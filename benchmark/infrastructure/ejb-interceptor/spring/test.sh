#!/usr/bin/env bash
set -euo pipefail
case "${INFRA_TARGET:-jakarta}" in
  spring) base="${BASE_URL:-http://localhost:8080}"; path=/; result=/response ;;
  jakarta|quarkus) base="${BASE_URL:-http://localhost:9080}"; path=/index.xhtml; result=/response.xhtml ;;
  *) echo 'Unknown INFRA_TARGET' >&2; exit 2 ;;
esac
export TEST_URL="${base}${path}" RESULT_PATH="$result"
for attempt in {1..60}; do
  if curl -fsS -o /dev/null "${base}${path}"; then break; fi
  if (( attempt == 60 )); then echo "Service unavailable: ${base}${path}" >&2; exit 1; fi
  sleep 2
done
python - <<'PY'
import os
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    response = page.goto(os.environ['TEST_URL'])
    assert response and response.status == 200, 'form URL missing'
    assert page.title() == 'Interceptor Example', 'wrong form page'
    page.get_by_label('Enter your name:').fill('MiXeD NaMe')
    page.get_by_role('button', name='Submit').click()
    page.wait_for_url('**' + os.environ['RESULT_PATH'])
    assert 'Hello, mixed name.' in page.locator('body').inner_text(), 'interceptor did not lowercase name'
    browser.close()
print('PASS: name is lowercased by interceptor')
PY
