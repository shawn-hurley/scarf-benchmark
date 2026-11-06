import pytest
from _verification.profiles import _target_http_port, prepare_profile

@pytest.mark.parametrize(("base_url", "expected_port"), [
    ("http://localhost:8080/counter", 8080),
    ("http://127.0.0.1:9080/", 9080),
    ("http://localhost:8082/order", 8082),
    ("http://example.com:8080/counter", None),
    ("https://localhost:8080/counter", None),
    ("http://localhost:99999/counter", None),
])
def test_target_http_port_uses_only_literal_local_http_url(tmp_path, base_url, expected_port):
    script = tmp_path / "test.sh"
    script.write_text(f'BASE_URL="${{BASE_URL:-{base_url}}}"\n')
    assert _target_http_port(script) == expected_port

@pytest.mark.parametrize("arm", ["quarkus", "jakarta|quarkus", "quarkus|spring"])
def test_target_http_port_selects_framework_case_arm(tmp_path, arm):
    script = tmp_path / "test.sh"
    script.write_text('case "${INFRA_TARGET:-jakarta}" in\n'
                      '  other) base="${BASE_URL:-http://localhost:8082}" ;;\n'
                      f'  {arm}) url="${{BASE_URL:-http://localhost:9080}}/index.xhtml" ;;\n'
                      'esac\n')
    assert _target_http_port(script, framework="quarkus") == 9080
    assert _target_http_port(script, framework="other") == 8082
    assert _target_http_port(script, framework="unknown") is None
    assert _target_http_port(script) is None

def test_target_http_port_rejects_conflicting_framework_defaults(tmp_path):
    script = tmp_path / "test.sh"
    script.write_text('BASE_URL="${BASE_URL:-http://localhost:8080}"\n'
                      'case "${INFRA_TARGET:-jakarta}" in\n'
                      '  quarkus) base="${BASE_URL:-http://localhost:9080}" ;;\n'
                      'esac\n')
    assert _target_http_port(script, framework="quarkus") is None


@pytest.mark.parametrize('app', ['cart', 'realworld'])
def test_reference_setup_is_retained_while_module_layout_is_removed(tmp_path, app):
    import json
    layer = 'whole_applications' if app == 'realworld' else 'business_domain'
    profile = tmp_path / layer / app / 'quarkus'
    profile.mkdir(parents=True)
    recipe = ('FROM maven:fixture\nRUN apt-get install -y postgresql\nWORKDIR /app\n'
              'COPY old/pom.xml old/\nRUN mvn install -pl old -am -DskipTests\n'
              'CMD service postgresql start && exec mvn quarkus:run -pl old\n')
    (profile / 'Dockerfile').write_text(recipe)
    (profile / 'Makefile').write_text('test:\n\t@echo upstream\n')
    (profile / 'test.sh').write_text('case "${INFRA_TARGET:-jakarta}" in\n'
                                    '  quarkus) url="${BASE_URL:-http://localhost:9080}/index.xhtml" ;;\n'
                                    'esac\n')
    work = tmp_path / 'artifacts'
    prepare_profile(tmp_path, tmp_path / 'run', {
        'layer': layer, 'app': app, 'source_framework': 'jakarta', 'target_framework': 'quarkus'}, work)
    adapted = (profile / 'Dockerfile').read_text()
    assert 'COPY . .' in adapted and ' -pl ' not in adapted
    assert 'CMD service postgresql start && exec python3' in adapted
    assert 'ENV QUARKUS_HTTP_PORT=9080' in adapted
    assert (profile / 'Makefile').read_text() == 'test:\n\t@echo upstream\n'
    if app == 'realworld':
        assert 'ENV QUARKUS_DATASOURCE_USERNAME="realworld"' in adapted
        assert 'ENV QUARKUS_DATASOURCE_JDBC_URL="jdbc:postgresql://localhost:5432/realworld"' in adapted
    else:
        assert 'QUARKUS_DATASOURCE_' not in adapted
    evidence = json.loads((work / 'quarkus-verifier.json').read_text())
    assert evidence['reference_recipe_sha256'] != evidence['adapted_recipe_sha256']


def test_source_profile_keeps_target_build_and_source_listener(tmp_path):
    profile = tmp_path / 'benchmark/whole_applications/petclinic/quarkus'
    profile.mkdir(parents=True)
    (profile / 'Dockerfile').write_text('FROM fixture\nCOPY . .\nCMD ["mvn","quarkus:run"]\n')
    (profile / 'Makefile').write_text('test:\n\tdocker run -e QUARKUS_HTTP_PORT=8080 image\n')
    (profile / 'test.sh').write_text('exit 9\n')
    run = tmp_path / 'run'
    (run / 'input').mkdir(parents=True)
    source = '#!/bin/bash\nexport INFRA_TARGET="${INFRA_TARGET:-jakarta}"\necho source assertions\n'
    (run / 'input/test.sh').write_text(source)
    prepare_profile(tmp_path / 'benchmark', run, {
        'layer': 'whole_applications', 'app': 'petclinic',
        'source_framework': 'jakarta', 'target_framework': 'quarkus'}, tmp_path / 'artifacts',
        behavior_contract='source')
    assert 'ENV QUARKUS_HTTP_PORT=9080' in (profile / 'Dockerfile').read_text()
    assert 'QUARKUS_HTTP_PORT=9080' in (profile / 'Makefile').read_text()
    assert 'export INFRA_TARGET=jakarta' in (profile / 'test.sh').read_text()
    assert (run / 'output/.scarfbench-source-contract.sh').read_text() == source
