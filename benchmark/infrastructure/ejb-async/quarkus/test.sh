#!/usr/bin/env bash
set -euo pipefail
case "${INFRA_TARGET:-jakarta}" in
  jakarta) url="${BASE_URL:-http://localhost:9080}/async-war/index.xhtml"; result=/async-war/response.xhtml ;;
  quarkus|spring) url="${BASE_URL:-http://localhost:9080}/index.xhtml"; result=/response.xhtml ;;
  *) echo 'Unknown INFRA_TARGET' >&2; exit 2 ;;
esac
export TEST_URL="$url" RESULT_PATH="$result"
for attempt in {1..60}; do
  if curl -fsS -o /dev/null "$url"; then break; fi
  if (( attempt == 60 )); then echo "Service unavailable: $url" >&2; exit 1; fi
  sleep 2
done
python - <<'PY'
import os, time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    response = page.goto(os.environ['TEST_URL'])
    assert response and response.status == 200, 'mail form URL missing'
    assert page.get_by_label('Send email to:').count() == 1, 'wrong mail form page'
    page.get_by_label('Send email to:').fill('benchmark@example.com')
    page.get_by_role('button', name='Send email').click()
    page.wait_for_url('**' + os.environ['RESULT_PATH'])
    assert 'Status:' in page.locator('body').inner_text(), 'mail status missing'
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        status = page.locator('body').inner_text()
        if 'Sent' in status or 'Encountered an error:' in status:
            break
        time.sleep(1)
        page.get_by_role('button', name='Refresh').click()
    else:
        raise AssertionError('asynchronous mail future did not complete')
    browser.close()
print('PASS: asynchronous mail request completed with a reported status')
PY
