import json

from _verification.verify import native_result


def test_make_failure_overrides_success_metadata(tmp_path):
    (tmp_path / 'metadata.json').write_text(json.dumps({
        'compile_ok': 'TRUE', 'deploy_ok': 'TRUE', 'tests_passed': 1, 'num_smoke_tests': 1}))
    (tmp_path / 'validation').mkdir()
    log = tmp_path / 'validation/run.log'
    log.write_text('===== 1 passed =====\nmake: *** [test] Error 1\n')
    assert not native_result(tmp_path)
    log.write_text('===== 1 passed =====\n')
    assert native_result(tmp_path)
