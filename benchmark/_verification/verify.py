"""Verify saved scarf conversions without an agent harness or new model calls."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _verification import copy_conversion, grade_contracts, prepare_profile


def native_result(run):
    metadata = json.loads((run / "metadata.json").read_text())
    log = run / "validation/run.log"
    make_failed = log.exists() and re.search(
        r"(?m)^make(?:\[\d+\])?: \*\*\*", log.read_text(errors="replace"))
    passed = metadata.get("tests_passed") or 0
    return bool(not make_failed and metadata.get("compile_ok") == "TRUE"
                and metadata.get("deploy_ok") == "TRUE" and passed > 0
                and passed >= (metadata.get("num_smoke_tests") or 0))


def verify(conversion, validations, artifacts, *, policy="target", scarf="scarf", timeout=60):
    """Copy a frozen input/output conversion and verify it in isolated workspaces."""
    conversion, validations, artifacts = map(Path, (conversion, validations, artifacts))
    metadata = json.loads((conversion / "metadata.json").read_text())
    layer, app = metadata["layer"], metadata["app"]
    source, target = metadata["source_framework"], metadata["target_framework"]
    instance = f"{layer}/{app}/{source}-to-{target}"
    agent = metadata["agent"]

    def run_path(work, instance_id):
        return work / "scarfbench-eval" / f"{agent}__{layer}__{app}__{source}__{target}" / "run_1"

    run = run_path(artifacts, instance)
    copy_conversion(conversion, run)

    def grade_native(instance_id, candidate, work, *, behavior_contract):
        private = work / "validations"
        shutil.copytree(validations / layer / app / target, private / layer / app / target,
                        ignore=shutil.ignore_patterns(
            ".git", "target", "node_modules", "__pycache__"))
        prepare_profile(private, candidate, metadata, work, behavior_contract=behavior_contract)
        profile = private / layer / app / target
        if (profile / "test.sh").is_file():
            shutil.copy2(profile / "test.sh", candidate / "output/test.sh")
        environment = {**os.environ, "TERM": "dumb"}
        environment.setdefault("DOCKER_BUILDKIT", "0")
        with (work / "scarfbench-validate.log").open("w") as log:
            subprocess.run([scarf, "validate", "--conversions-dir", str(work / "scarfbench-eval"),
                            "--validations-dir", str(private), "--timeout", str(timeout)],
                           env=environment, stdin=subprocess.DEVNULL, stdout=log,
                           stderr=subprocess.STDOUT, check=False)
        return native_result(candidate)

    return grade_contracts(instance, run, artifacts, policy=policy,
                           run_path=run_path, grade_native=grade_native)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conversion", type=Path, required=True)
    parser.add_argument("--validations-dir", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--policy", choices=("target", "source", "either"), default="target")
    parser.add_argument("--scarf", default="scarf")
    parser.add_argument("--timeout", type=int, default=60, help="Minutes per complete contract")
    args = parser.parse_args()
    resolved = verify(args.conversion, args.validations_dir, args.artifacts,
                      policy=args.policy, scarf=args.scarf, timeout=args.timeout)
    print((args.artifacts / "verification-contract.json").read_text())
    raise SystemExit(0 if resolved else 1)
