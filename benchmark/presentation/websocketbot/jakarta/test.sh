#!/usr/bin/env bash
set -euo pipefail
case "${WEBSOCKETBOT_TARGET:-jakarta}" in
  jakarta) url="${BASE_URL:-http://localhost:9080}/websocketbot-10-SNAPSHOT/index.html" ;;
  quarkus|spring) url="${BASE_URL:-http://localhost:8080}/index.html" ;;
  *) echo 'Unknown WEBSOCKETBOT_TARGET' >&2; exit 2 ;;
esac
for attempt in {1..60}; do
  if curl -fs -o /dev/null "$url"; then break; fi
  if (( attempt == 60 )); then echo "Page unavailable: $url" >&2; exit 1; fi
  sleep 2
done
export TEST_URL="$url"
python - <<'PY'
import os, uuid
from playwright.sync_api import sync_playwright
name = 'bench' + uuid.uuid4().hex[:7]
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    response = page.goto(os.environ['TEST_URL'])
    assert response and response.status == 200, 'chat page missing'
    assert page.url == os.environ['TEST_URL'], 'chat page redirected from expected path'
    assert page.title() == 'WebsocketBot', 'wrong chat page'
    page.wait_for_function('window.wsocket && wsocket.readyState === WebSocket.OPEN', timeout=15000)
    page.locator('#name').fill(name)
    page.locator('#join').click()
    page.wait_for_function("name => document.querySelector('#textarea').value.includes(name + ' has joined the chat')", arg=name, timeout=15000)
    page.wait_for_function("name => document.querySelector('#userlist').value.includes(name)", arg=name, timeout=15000)
    page.locator('#input').fill('@Duke how are you?')
    page.locator('#input').press('Enter')
    page.wait_for_function("() => document.querySelector('#textarea').value.includes(\"I'm doing great, thank you!\")", timeout=15000)
    browser.close()
print('PASS: joined chat, received user list, and got Duke reply over WebSocket')
PY
