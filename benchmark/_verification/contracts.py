"""Select complete ScarfBench behavior contracts without rewriting assertions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil


def validation_policy(config: dict) -> str:
    policy = config.get("validation_contract", "target")
    if policy not in ("target", "source", "either"):
        raise ValueError("scarfbench.validation_contract must be target, source, or either")
    return policy


def validate_source_pair(source: str, target: str) -> None:
    if (source, target) != ("jakarta", "quarkus"):
        raise ValueError("source/either behavior validation currently supports Jakarta-to-Quarkus")


def copy_conversion(original: Path, destination: Path) -> None:
    # A source package can legitimately be named validation. Only the native
    # grader's top-level output directory is excluded from this isolated copy.
    shutil.copytree(original, destination, ignore=lambda directory, names:
                    {"validation"} if Path(directory) == original else set())
    path = destination / "metadata.json"
    if path.is_file():
        metadata = json.loads(path.read_text())
        for key in ("compile_ok", "deploy_ok", "tests_passed", "failure_reason",
                    "failure_category", "inconclusive"):
            metadata.pop(key, None)
        path.write_text(json.dumps(metadata, indent=2) + "\n")


def prepare_source_contract(benchmark_dir: Path, run: Path, metadata: dict) -> int:
    """Run the trusted source assertions against the migrated Quarkus runtime."""
    from .profiles import _target_http_port
    source, target = metadata["source_framework"], metadata["target_framework"]
    validate_source_pair(source, target)
    script = run / "input/test.sh"
    if not script.is_file():
        raise FileNotFoundError("Source behavior validation requires the frozen input/test.sh")
    text = script.read_text()
    selectors = sorted(set(re.findall(r"\b[A-Z][A-Z0-9_]*_TARGET\b", text)))
    output = run / "output"
    output.mkdir(exist_ok=True)
    shutil.copy2(script, output / ".scarfbench-source-contract.sh")
    # Explicit selectors take precedence over target-specific Makefile flags.
    # The assertion script itself is copied byte for byte from the frozen input.
    wrapper = ("#!/usr/bin/env bash\nset -euo pipefail\nunset BASE_URL APP_ORIGIN\n"
               + "".join(f"export {name}={source}\n" for name in selectors)
               + "exec bash /app/.scarfbench-source-contract.sh\n")
    profile = benchmark_dir / metadata["layer"] / metadata["app"] / target
    (profile / "test.sh").write_text(wrapper)
    # The supported Jakarta suite uses 9080 unless its assertion script declares
    # a literal local BASE_URL (Petclinic, RealWorld and CargoTracker use 8080).
    port = _target_http_port(script, framework=source) or 9080
    (profile / ".scarfbench-source-contract.json").write_text(json.dumps({
        "framework_runtime": target, "behavior_contract": source,
        "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
        "selectors": selectors, "http_port": port,
    }, indent=2) + "\n")
    return port


def grade_contracts(instance_id: str, run: Path, artifacts: Path, *, policy: str, run_path, grade_native) -> bool:
    """Accept a complete contract, never a mixture of passing individual checks."""
    policy = validation_policy({"validation_contract": policy})
    if run != run_path(artifacts, instance_id):
        raise ValueError("ScarfBench conversion is outside the native grading layout")
    source, target = instance_id.rsplit("/", 1)[-1].split("-to-")
    if policy != "target":
        validate_source_pair(source, target)
        if not (run / "input/test.sh").is_file():
            raise FileNotFoundError("Source behavior validation requires the frozen input/test.sh")
    evidence = {"version": 1, "policy": policy, "runtime_framework": target,
                "matched_contract": None, "attempts": []}
    selected = None
    contracts = ["target", "source"] if policy == "either" else [policy]
    for contract in contracts:
        if policy == "target":
            work, conversion = artifacts, run
        else:
            work = artifacts / "contract-validation" / contract
            conversion = run_path(work, instance_id)
            copy_conversion(run, conversion)
        resolved = grade_native(instance_id, conversion, work, behavior_contract=contract)
        metadata_file = conversion / "metadata.json"
        metadata = json.loads(metadata_file.read_text()) if metadata_file.exists() else {}
        evidence["attempts"].append({"contract": contract, "resolved": resolved,
                                    "compile_ok": metadata.get("compile_ok"),
                                    "failure_reason": metadata.get("failure_reason"),
                                    "artifacts": str(work.relative_to(artifacts))})
        selected = (conversion, work)
        if resolved:
            evidence["matched_contract"] = contract
            break
        # A source behavior test cannot rescue an application that does not
        # build as the target framework. Avoid rebuilding it for another test.
        if metadata.get("compile_ok") != "TRUE":
            break
    if policy != "target" and selected:
        conversion, work = selected
        shutil.copy2(conversion / "metadata.json", run / "metadata.json")
        if (conversion / "validation").is_dir():
            shutil.copytree(conversion / "validation", run / "validation", dirs_exist_ok=True)
        # Adopt trusted grader scaffolding only; application source stays intact.
        for name in ("Dockerfile", "Makefile", "test.sh", ".scarfbench-source-contract.sh"):
            path = conversion / "output" / name
            if path.is_file():
                shutil.copy2(path, run / "output" / name)
        if (work / "quarkus-verifier.json").is_file():
            shutil.copy2(work / "quarkus-verifier.json", artifacts / "quarkus-verifier.json")
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "verification-contract.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence["matched_contract"] is not None
