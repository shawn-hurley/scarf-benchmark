"""Module-independent JVM Quarkus validation, also executed inside grader images.

Keep this module standard-library-only: its source is embedded in the trusted
validation Dockerfile, rather than taken from the submitted application.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import zipfile

MARKER = "# ScarfBench module-independent Quarkus verifier v1"
HELPER = "/opt/scarfbench-quarkus-verifier.py"
SELECTION = "/opt/scarfbench-quarkus-entrypoint.json"


def _instructions(recipe: str) -> list[str]:
    instructions, pending = [], ""
    for line in recipe.splitlines():
        if not pending and (not line.strip() or line.lstrip().startswith("#")):
            continue
        pending += line + "\n"
        if line.rstrip().endswith("\\"):
            continue
        instructions.append(pending.rstrip())
        pending = ""
    if pending:
        raise ValueError("Unterminated Dockerfile instruction")
    return instructions


def module_independent_recipe(recipe: str, *, http_port: int | None = None) -> str:
    """Retain the reference runtime environment, replacing its application layout.

    Unknown command forms fail explicitly. In particular, service setup before
    the final application command must survive; guessing by application name
    or trying several applications until the tests pass would change grading.
    """
    if http_port is not None and (type(http_port) is not int or not 1 <= http_port <= 65535):
        raise ValueError("Quarkus validation HTTP port must be between 1 and 65535")
    if MARKER in recipe:
        return recipe
    instructions = _instructions(recipe)
    prefix = []
    for instruction in instructions:
        if instruction.split(None, 1)[0].upper() in {"COPY", "ADD"}:
            break
        prefix.append(instruction)
    else:
        raise ValueError("Quarkus validator has no application COPY instruction")
    if any(i.split(None, 1)[0].upper() == "ENTRYPOINT" for i in instructions):
        raise ValueError("Unsupported Quarkus validator ENTRYPOINT")
    commands = [i.split(None, 1)[1] for i in instructions
                if i.split(None, 1)[0].upper() == "CMD"]
    if len(commands) != 1:
        raise ValueError("Quarkus validator must have one CMD")
    command = commands[0]
    service_prefix = ""
    if command.startswith("["):
        launch = json.loads(command)
    else:
        # Preserve the complete shell prefix (database/broker initialization).
        flat = command.replace("\\\n", " ")
        matches = list(re.finditer(r"(?:^|&&\s*)(?:exec\s+)?(java|mvn)\s+", flat))
        if not matches:
            raise ValueError("Unsupported Quarkus validator launch command")
        match = matches[-1]
        start = match.start(1)
        service_prefix = flat[:start]
        service_prefix = re.sub(r"exec\s+$", "", service_prefix)
        launch = shlex.split(flat[start:])
    if launch[0] not in {"java", "mvn"} or any(x in launch for x in ["&&", ";", "||", "|"]):
        raise ValueError("Unsupported Quarkus validator application command")
    runtime_options = [x for x in launch[1:] if x.startswith("-D")]
    # Preserve reference build properties (e.g. profiles and optional linters),
    # but never module selectors or the reference's package/install repetition.
    build_options = []
    for instruction in instructions:
        if instruction.startswith("RUN ") and re.search(r"\bmvn\s", instruction):
            for token in shlex.split(instruction.replace("\\\n", " ")):
                if token.startswith("-D") and token not in build_options:
                    build_options.append(token)
    payload = base64.b64encode(Path(__file__).read_bytes()).decode("ascii")
    install = ("import base64; from pathlib import Path; "
               f"Path({HELPER!r}).write_bytes(base64.b64decode({payload!r}))")
    build = shlex.join(["python3", HELPER, "build", *build_options])
    run = ["python3", HELPER, "run", *runtime_options]
    cmd = ("CMD " + service_prefix + "exec " + shlex.join(run)
           if service_prefix else "CMD " + json.dumps(run))
    # Some reference images contain only Java and curl. The verifier owns this
    # dependency; submitted application code must not need to install it.
    python = ("RUN command -v python3 >/dev/null 2>&1 || "
              "(apt-get update && apt-get install -y --no-install-recommends python3 "
              "&& rm -rf /var/lib/apt/lists/*)")
    # Set the runtime default in the image, so upstream Makefiles that do not
    # pass a port still launch on the unchanged behavior test's listener.
    runtime_env = [f"ENV QUARKUS_HTTP_PORT={http_port}"] if http_port is not None else []
    return "\n".join([MARKER, *prefix, python, "WORKDIR /app", "COPY . .",
                      "RUN python3 -c " + shlex.quote(install), "RUN " + build,
                      *runtime_env, cmd, ""])


def _main_class(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as jar:
            manifest = jar.read("META-INF/MANIFEST.MF").decode("utf-8")
        manifest = manifest.replace("\r\n", "\n").replace("\n ", "")
        return next((line.partition(":")[2].strip() for line in manifest.splitlines()
                     if line.startswith("Main-Class:")), "")
    except (OSError, KeyError, UnicodeError, zipfile.BadZipFile):
        return ""


def application_artifacts(root: Path) -> list[Path]:
    """Find runnable fast, uber, or legacy JVM jars in any module's target dir."""
    root = root.resolve()
    artifacts = []
    for path in root.rglob("*.jar"):
        relative = path.relative_to(root)
        if "target" not in relative.parts or not path.resolve().is_relative_to(root):
            continue
        # Dependency jars can have Main-Class too; they are not app entrypoints.
        fast = path.name == "quarkus-run.jar" and path.parent.name == "quarkus-app"
        runner = path.name.endswith("-runner.jar") and path.parent.name == "target"
        if (fast or runner) and _main_class(path).startswith("io.quarkus."):
            artifacts.append(path)
    return sorted(artifacts)


def select_application(root: Path) -> Path:
    artifacts = application_artifacts(root)
    if len(artifacts) != 1:
        listing = ", ".join(str(p.relative_to(root.resolve())) for p in artifacts) or "none"
        raise ValueError(f"Expected exactly one runnable Quarkus application; "
                         f"found {len(artifacts)}: {listing}")
    return artifacts[0]


def main() -> None:
    action, *options = sys.argv[1:]
    if action == "build":
        if not Path("pom.xml").is_file():
            raise ValueError("Submitted project must contain a root Maven pom.xml")
        # Prevent copied build outputs from an inactive/removed module becoming
        # candidates. This operates only on the disposable grader image.
        for target in sorted(Path.cwd().rglob("target"), reverse=True):
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
        subprocess.run(["mvn", "-B", "clean", "install", "-DskipTests", *options], check=True)
        entrypoint = select_application(Path.cwd())
        Path(SELECTION).write_text(json.dumps(str(entrypoint)))
        print(f"ScarfBench Quarkus application: {entrypoint}", flush=True)
    elif action == "run":
        entrypoint = Path(json.loads(Path(SELECTION).read_text()))
        if not entrypoint.is_file():
            raise ValueError(f"Built Quarkus application is missing: {entrypoint}")
        os.execvp("java", ["java", *options, "-jar", str(entrypoint)])
    else:
        raise ValueError(f"Unknown Quarkus verifier action: {action}")


if __name__ == "__main__":
    main()
