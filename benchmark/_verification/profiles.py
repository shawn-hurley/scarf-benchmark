"""Trusted deployment preparation for migrated Quarkus applications."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from .quarkus import module_independent_recipe

_DEPLOYMENTS_FILE = Path(__file__).with_name("deployments.json")

def _target_http_port(test_script: Path, *, framework: str | None = None) -> int | None:
    """Read the local HTTP port required by a target framework's smoke test.

    Support literal BASE_URL defaults and simple framework TARGET case arms.
    Never execute shell code to infer settings. Unknown or conflicting forms
    retain their original behavior instead of risking a guessed port.
    """
    script = test_script.read_text(errors="replace")
    match = re.search(
        r'^BASE_URL="\$\{BASE_URL:-(http://[^}\s]+)\}"[ \t]*$',
        script,
        re.MULTILINE,
    )
    urls = [match.group(1)] if match else []
    if framework:
        for case in re.finditer(
            r'^\s*case\s+"\$\{[A-Z_]+_TARGET(?::-[a-z_]+)?\}"\s+in\s*\n(.*?)^\s*esac\b',
            script, re.MULTILINE | re.DOTALL,
        ):
            for arm in re.finditer(
                r'^\s*([a-z_]+(?:\|[a-z_]+)*)\)\s*(.*?)\s*;;[ \t]*$',
                case.group(1), re.MULTILINE,
            ):
                if framework in arm.group(1).split("|"):
                    urls.extend(re.findall(r'\$\{BASE_URL:-(http://[^}\s]+)\}', arm.group(2)))
    if not urls:
        return None
    ports = set()
    for value in urls:
        try:
            url = urlsplit(value)
            port = url.port
            if (url.hostname not in {"localhost", "127.0.0.1", "::1"}
                    or url.username or url.password or port is None or not 1 <= port <= 65535):
                return None
        except ValueError:
            return None
        ports.add(port)
    return ports.pop() if len(ports) == 1 else None

def _validation_deployment_environment(*, layer: str, app: str, framework: str) -> dict[str, str]:
    """Trusted benchmark deployment settings, independent of candidate defaults."""
    document = json.loads(_DEPLOYMENTS_FILE.read_text())
    if document.get("schema_version") != 1:
        raise ValueError("Unsupported ScarfBench deployment settings version")
    key = f"{layer}/{app}/{framework}"
    environment = document.get("deployments", {}).get(key, {}).get("environment", {})
    if not isinstance(environment, dict) or any(
        not isinstance(name, str) or not re.fullmatch(r"[A-Z_][A-Z0-9_]*", name)
        or not isinstance(value, str) or any(char in value for char in "\n\r\0$")
        for name, value in environment.items()
    ):
        raise ValueError(f"Invalid literal deployment environment: {key}")
    return dict(environment)


def prepare_profile(benchmark_dir, run, metadata, artifacts, *, behavior_contract="target"):
    """Adapt a private reference tree without changing application source or assertions."""
    from .contracts import prepare_source_contract
    profile = benchmark_dir / metadata["layer"] / metadata["app"] / metadata["target_framework"]
    source_port = None
    if behavior_contract == "source":
        source_port = prepare_source_contract(benchmark_dir, run, metadata)
        makefile = profile / "Makefile"
        if makefile.exists():
            makefile.write_text(re.sub(r"QUARKUS_HTTP_PORT=\d+",
                                      f"QUARKUS_HTTP_PORT={source_port}", makefile.read_text()))
    recipe_path = profile / "Dockerfile"
    if metadata["target_framework"] != "quarkus" or not recipe_path.is_file():
        return
    original = recipe_path.read_text()
    script = profile / "test.sh"
    port = (source_port if source_port is not None else
            _target_http_port(script, framework="quarkus") if script.exists() else None)
    recipe = module_independent_recipe(original, http_port=port)
    environment = _validation_deployment_environment(
        layer=metadata["layer"], app=metadata["app"], framework="quarkus")
    for name, value in sorted(environment.items()):
        recipe += f"ENV {name}={json.dumps(value)}\n"
    recipe_path.write_text(recipe)
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "quarkus-verifier.json").write_text(json.dumps({
        "version": 1,
        "reference_recipe_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "adapted_recipe_sha256": hashlib.sha256(recipe.encode()).hexdigest(),
        "http_port": port,
        "deployment_environment_keys": sorted(environment),
        "contract": "root Maven reactor; exactly one runnable Quarkus JVM artifact",
    }, indent=2) + "\n")
