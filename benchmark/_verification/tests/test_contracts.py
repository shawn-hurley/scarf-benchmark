import json
import os
from pathlib import Path
import subprocess

import pytest

from _verification.contracts import prepare_source_contract, validation_policy, grade_contracts


class ScarfBench:
    def __init__(self, config):
        self.config = config

    def _run_dir_for_instance(self, artifacts, instance):
        return artifacts / "conversions" / instance.replace("/", "__") / "run_1"

    def _grade_native(self, *args, **kwargs):
        raise NotImplementedError

    def grade_run(self, instance, run, artifacts):
        return grade_contracts(instance, run, artifacts, policy=self.config["validation_contract"],
                               run_path=self._run_dir_for_instance, grade_native=self._grade_native)


def conversion(tmp_path, policy):
    benchmark = ScarfBench({"validation_contract": policy})
    identity = "whole_applications/petclinic/jakarta-to-quarkus"
    run = benchmark._run_dir_for_instance(tmp_path, identity)
    (run / "input").mkdir(parents=True)
    (run / "input/test.sh").write_text("echo source assertions\n")
    source = run / "output/src/validation/constraint/Source.java"
    source.parent.mkdir(parents=True)
    source.write_text("unchanged source")
    (run / "metadata.json").write_text(json.dumps({
        "source_framework": "jakarta", "target_framework": "quarkus",
        "compile_ok": "FALSE", "failure_reason": "old result",
    }))
    return benchmark, identity, run, source


@pytest.mark.parametrize("target,source,matched", [
    (True, False, "target"), (False, True, "source"), (False, False, None),
])
def test_either_requires_one_complete_contract(tmp_path, monkeypatch, target, source, matched):
    benchmark, identity, run, original_source = conversion(tmp_path, "either")
    calls = []
    def grade(instance_id, attempt, artifacts, *, behavior_contract):
        calls.append(behavior_contract)
        metadata = json.loads((attempt / "metadata.json").read_text())
        assert "failure_reason" not in metadata
        assert (attempt / "output/src/validation/constraint/Source.java").read_text() == "unchanged source"
        resolved = target if behavior_contract == "target" else source
        (attempt / "metadata.json").write_text(json.dumps({"compile_ok": "TRUE", "tests_passed": int(resolved)}))
        (attempt / "validation").mkdir()
        (attempt / "validation/run.log").write_text(behavior_contract)
        return resolved
    monkeypatch.setattr(benchmark, "_grade_native", grade)
    assert benchmark.grade_run(identity, run, tmp_path) == (matched is not None)
    assert calls == (["target"] if target else ["target", "source"])
    evidence = json.loads((tmp_path / "verification-contract.json").read_text())
    assert evidence["policy"] == "either"
    assert evidence["matched_contract"] == matched
    assert original_source.read_text() == "unchanged source"
    assert (run / "validation/run.log").read_text() == calls[-1]


def test_either_does_not_rescue_non_quarkus_build(tmp_path, monkeypatch):
    benchmark, identity, run, _ = conversion(tmp_path, "either")
    calls = []
    def grade(instance_id, attempt, artifacts, *, behavior_contract):
        calls.append(behavior_contract)
        (attempt / "metadata.json").write_text('{"compile_ok":"FALSE"}')
        return False
    monkeypatch.setattr(benchmark, "_grade_native", grade)
    assert not benchmark.grade_run(identity, run, tmp_path)
    assert calls == ["target"]


def test_source_only_uses_source_assertions(tmp_path, monkeypatch):
    benchmark, identity, run, _ = conversion(tmp_path, "source")
    def grade(instance_id, attempt, artifacts, *, behavior_contract):
        assert behavior_contract == "source"
        (attempt / "metadata.json").write_text('{"compile_ok":"TRUE"}')
        return True
    monkeypatch.setattr(benchmark, "_grade_native", grade)
    assert benchmark.grade_run(identity, run, tmp_path)
    assert json.loads((tmp_path / "verification-contract.json").read_text())["matched_contract"] == "source"


def test_source_wrapper_keeps_assertions_and_overrides_target_selector(tmp_path):
    profile = tmp_path / "benchmark/whole_applications/petclinic/quarkus"
    profile.mkdir(parents=True)
    run = tmp_path / "conversion"
    (run / "input").mkdir(parents=True)
    script = ('#!/bin/bash\nset -eu\nBASE_URL="${BASE_URL:-http://localhost:8080}"\n'
              'test "$PETCLINIC_TARGET" = jakarta\n'
              'test "$BASE_URL" = http://localhost:8080\necho "source assertions passed"\n')
    (run / "input/test.sh").write_text(script)
    port = prepare_source_contract(tmp_path / "benchmark", run, {
        "layer": "whole_applications", "app": "petclinic",
        "source_framework": "jakarta", "target_framework": "quarkus"})
    assert port == 8080
    assert (run / "output/.scarfbench-source-contract.sh").read_text() == script
    wrapper = (profile / "test.sh").read_text().replace("/app/", str(run / "output") + "/")
    result = subprocess.run(["bash", "-c", wrapper], env={**os.environ,
                            "PETCLINIC_TARGET": "quarkus", "BASE_URL": "http://wrong:1234"},
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "source assertions passed" in result.stdout


@pytest.mark.parametrize("policy", ["unknown", None, True])
def test_invalid_policy_fails_closed(policy):
    with pytest.raises(ValueError, match="validation_contract"):
        validation_policy({"validation_contract": policy})


def test_missing_frozen_source_is_not_replaced_by_candidate_test(tmp_path):
    benchmark, identity, run, _ = conversion(tmp_path, "either")
    (run / "input/test.sh").unlink()
    (run / "output/test.sh").write_text("exit 0\n")
    with pytest.raises(FileNotFoundError, match="frozen input"):
        benchmark.grade_run(identity, run, tmp_path)
