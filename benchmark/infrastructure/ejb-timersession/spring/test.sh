#!/usr/bin/env bash
set -euo pipefail
case "${INFRA_TARGET:-jakarta}" in
  jakarta) url="${BASE_URL:-http://localhost:9080}/timersession/timer-client.xhtml" ;;
  quarkus) url="${BASE_URL:-http://localhost:9080}/timersession/timer-client.xhtml" ;;
  spring) url="${BASE_URL:-http://localhost:9080}/" ;;
  *) echo 'Unknown INFRA_TARGET' >&2; exit 2 ;;
esac
export TEST_URL="$url"
for attempt in {1..60}; do
  if curl -fsS -o /dev/null "$url"; then break; fi
  if (( attempt == 60 )); then echo "Service unavailable: $url" >&2; exit 1; fi
  sleep 2
done
python - <<'PY'
import os, re, time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    response = page.goto(os.environ['TEST_URL'])
    assert response and response.status == 200, 'timer URL missing'
    assert 'Set a programmatic timer here.' in page.locator('body').inner_text(), 'wrong timer page'
    before = page.locator('body').inner_text()
    page.get_by_role('button', name='Set Timer').click()
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        text = page.locator('body').inner_text()
        match = re.search(r'The last programmatic timeout was: (.+?)\.', text)
        if match and match.group(1).strip() not in ('never', 'null', '') and match.group(1) not in before:
            break
        time.sleep(1)
        page.get_by_role('button', name='Refresh').click()
    else:
        raise AssertionError('programmatic timer did not fire')
    browser.close()
print('PASS: programmatic timer fired')
PY
