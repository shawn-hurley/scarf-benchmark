#!/usr/bin/env bash
set -euo pipefail
case "${INFRA_TARGET:-jakarta}" in
  jakarta|quarkus) base="${BASE_URL:-http://localhost:9080}"; url="$base/index.xhtml"; api="$base/taskinfo" ;;
  spring) base="${BASE_URL:-http://localhost:9080}"; url=''; api="$base/taskcreator/taskinfo" ;;
  *) echo 'Unknown INFRA_TARGET' >&2; exit 2 ;;
esac
export TEST_URL="$url" TEST_API="$api"
ready="$api"
if [[ -n "$url" ]]; then ready="$url"; fi
for attempt in {1..60}; do
  if curl -sS -o /dev/null "$ready"; then break; fi
  if (( attempt == 60 )); then echo "Service unavailable: $ready" >&2; exit 1; fi
  sleep 2
done
python - <<'PY'
import os, time, uuid
from urllib.request import Request, urlopen
from playwright.sync_api import sync_playwright
name = 'bench' + uuid.uuid4().hex[:8]
api = os.environ['TEST_API']
if os.environ['TEST_URL']:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        response = page.goto(os.environ['TEST_URL'])
        assert response and response.status == 200, 'task creator URL missing'
        assert 'The Task Creator Concurrency Example' in page.locator('body').inner_text()
        page.locator('input[id$="taskname"]').fill(name)
        page.get_by_role('button', name='Submit').click()
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if name in page.locator('textarea[id$="infolog"]').input_value():
                break
            time.sleep(0.5)
        else:
            raise AssertionError('submitted task did not appear in execution log')
        browser.close()
else:
    # The Spring reference exposes only the task update service and no form.
    marker = 'benchmark-' + name
    request = Request(api, data=marker.encode(), headers={'Content-Type':'text/plain'}, method='POST')
    with urlopen(request, timeout=10) as response:
        assert response.status in (200, 204), 'task update rejected'
print('PASS: task creator operation completed')
PY
