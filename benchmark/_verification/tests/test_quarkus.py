"""Grade equivalent layouts without accepting stale or ambiguous applications."""
import json
from pathlib import Path
import shlex
import sys
import subprocess
import zipfile

import pytest

from _verification import quarkus as verifier


def jar(path, main="io.quarkus.bootstrap.runner.QuarkusEntryPoint"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("META-INF/MANIFEST.MF", f"Manifest-Version: 1.0\nMain-Class: {main}\n")
    return path


@pytest.mark.parametrize("location", [
    "target/quarkus-app/quarkus-run.jar",
    "renamed-service/target/quarkus-app/quarkus-run.jar",
    "services/nested/target/application-runner.jar",
])
def test_module_independent_artifact_selection(tmp_path, location):
    application = jar(tmp_path / location)
    jar(tmp_path / "helper/target/helper.jar")
    jar(tmp_path / "target/quarkus-app/lib/main/dependency-runner.jar", "other.Main")
    jar(tmp_path / "target/quarkus-app/lib/main/quarkus-dependency-runner.jar")
    assert verifier.select_application(tmp_path) == application


def test_zero_and_multiple_applications_fail_with_diagnostics(tmp_path):
    with pytest.raises(ValueError, match="found 0: none"):
        verifier.select_application(tmp_path)
    jar(tmp_path / "first/target/quarkus-app/quarkus-run.jar")
    jar(tmp_path / "second/target/quarkus-app/quarkus-run.jar")
    with pytest.raises(ValueError, match="found 2: first/target/.*second/target/"):
        verifier.select_application(tmp_path)


def test_invalid_jars_and_external_symlinks_are_not_applications(tmp_path):
    root = tmp_path / "submission"
    root.mkdir()
    external = jar(tmp_path / "external/quarkus-run.jar")
    linked = root / "target/quarkus-app/quarkus-run.jar"
    linked.parent.mkdir(parents=True)
    linked.symlink_to(external)
    invalid = root / "target/broken-runner.jar"
    invalid.write_text("not a jar")
    assert verifier.application_artifacts(root) == []


def test_recipe_preserves_environment_profiles_and_service_setup():
    original = '''FROM maven:fixture
RUN apt-get install -y python3 postgresql
ENV EXAMPLE=value
WORKDIR /app
COPY pom.xml .
COPY old-module/pom.xml old-module/
RUN mvn install -pl old-module -am -DskipTests -Dquarkus.profile=dev
COPY . .
CMD service postgresql start && exec java -Dquarkus.profile=dev -jar old-module/target/quarkus-app/quarkus-run.jar
'''
    recipe = verifier.module_independent_recipe(original)
    assert "RUN apt-get install -y python3 postgresql" in recipe
    assert "ENV EXAMPLE=value" in recipe
    assert "old-module" not in recipe
    assert " -pl " not in recipe
    assert "build -DskipTests -Dquarkus.profile=dev" in recipe
    assert "CMD service postgresql start && exec python3" in recipe
    assert "run -Dquarkus.profile=dev" in recipe
    assert recipe.count("COPY ") == 1
    assert verifier.module_independent_recipe(recipe) == recipe


def test_json_maven_launch_selects_artifact_instead_of_root_plugin():
    recipe = verifier.module_independent_recipe('''FROM maven:fixture
RUN apt-get install -y python3
WORKDIR /app
COPY . .
RUN mvn clean package -Dpmd.skip=true
CMD ["mvn", "quarkus:run", "-pl", "obsolete", "-Dquarkus.profile=dev"]
''')
    command = json.loads(recipe.splitlines()[-1].removeprefix("CMD "))
    assert command == ["python3", verifier.HELPER, "run", "-Dquarkus.profile=dev"]
    assert "build -Dpmd.skip=true" in recipe
    assert "obsolete" not in recipe


def test_unknown_launch_is_rejected_instead_of_discarding_setup():
    with pytest.raises(ValueError, match="Unsupported.*launch"):
        verifier.module_independent_recipe("FROM maven:fixture\nCOPY . .\nCMD custom-launcher\n")


def test_image_declares_target_port_for_upstream_launch_commands():
    recipe = verifier.module_independent_recipe(
        'FROM maven:fixture\nCOPY . .\nCMD ["mvn", "quarkus:run"]\n', http_port=9080)
    assert "ENV QUARKUS_HTTP_PORT=9080\nCMD " in recipe
    for invalid in [0, 65536, True, "9080"]:
        with pytest.raises(ValueError, match="HTTP port"):
            verifier.module_independent_recipe("unused", http_port=invalid)


def test_embedded_helper_is_trusted_source_and_executable(tmp_path):
    recipe = verifier.module_independent_recipe(
        'FROM maven:fixture\nCOPY . .\nCMD ["mvn", "quarkus:run"]\n')
    install = next(line for line in recipe.splitlines() if line.startswith("RUN python3 -c "))
    script = shlex.split(install)[3]
    script = script.replace(repr(verifier.HELPER), repr(str(tmp_path / "helper.py")))
    exec(compile(script, "<install>", "exec"))
    assert (tmp_path / "helper.py").read_bytes() == Path(verifier.__file__).read_bytes()


def test_java_only_image_installs_python_before_using_helper(tmp_path):
    recipe = verifier.module_independent_recipe(
        'FROM maven:fixture\nRUN apt-get install -y curl\nCOPY . .\nCMD ["mvn", "quarkus:run"]\n')
    bootstrap = next(line for line in recipe.splitlines() if line.startswith("RUN command -v python3"))
    assert recipe.index(bootstrap) < recipe.index("RUN python3 -c ")
    # Exercise the actual bootstrap shell with no Python in PATH; apt installs
    # a stand-in, and the second invocation must leave the installation alone.
    engine = tmp_path / "bin"
    engine.mkdir()
    log = tmp_path / "apt.log"
    apt = engine / "apt-get"
    apt.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$APT_LOG"\n'
                   'if [ "$1" = install ]; then\n'
                   'printf "#!/bin/sh\\nexit 0\\n" > "$INSTALL_BIN/python3"\n'
                   '/bin/chmod +x "$INSTALL_BIN/python3"\nfi\n')
    apt.chmod(0o755)
    rm = engine / "rm"
    rm.write_text("#!/bin/sh\nexit 0\n")
    rm.chmod(0o755)
    env = {"PATH": str(engine), "APT_LOG": str(log), "INSTALL_BIN": str(engine)}
    command = ["/bin/sh", "-c", bootstrap.removeprefix("RUN ")]
    subprocess.run(command, env=env, check=True)
    assert log.read_text().splitlines() == ["update", "install -y --no-install-recommends python3"]
    before = log.read_text()
    subprocess.run(command, env=env, check=True)
    assert log.read_text() == before


def test_build_cleans_stale_modules_and_selects_new_artifact(tmp_path, monkeypatch):
    (tmp_path / "pom.xml").write_text("<project/>")
    stale = jar(tmp_path / "removed-module/target/quarkus-app/quarkus-run.jar")
    selection = tmp_path / "selected.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(verifier, "SELECTION", str(selection))
    monkeypatch.setattr(sys, "argv", ["helper", "build", "-Dquarkus.profile=dev"])
    def build(command, **kwargs):
        assert not stale.exists()
        assert command == ["mvn", "-B", "clean", "install", "-DskipTests", "-Dquarkus.profile=dev"]
        assert kwargs == {"check": True}
        jar(tmp_path / "new-module/target/quarkus-app/quarkus-run.jar")
    monkeypatch.setattr(verifier.subprocess, "run", build)
    verifier.main()
    assert json.loads(selection.read_text()) == str(tmp_path / "new-module/target/quarkus-app/quarkus-run.jar")


def test_runtime_exec_keeps_properties_and_uses_build_selection(tmp_path, monkeypatch):
    application = jar(tmp_path / "any-module/target/quarkus-app/quarkus-run.jar")
    selection = tmp_path / "selected.json"
    selection.write_text(json.dumps(str(application)))
    monkeypatch.setattr(verifier, "SELECTION", str(selection))
    monkeypatch.setattr(sys, "argv", ["helper", "run", "-Dquarkus.profile=dev"])
    calls = []
    monkeypatch.setattr(verifier.os, "execvp", lambda *args: calls.append(args))
    verifier.main()
    assert calls == [("java", ["java", "-Dquarkus.profile=dev", "-jar", str(application)])]
