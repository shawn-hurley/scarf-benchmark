#!/usr/bin/env python3
"""Generate standalone target test.sh files; --check verifies committed output."""
from pathlib import Path
import argparse
import sys

TEST_PY = r"""
import http.client
import json
import os
import re
import time
from urllib.parse import urlparse

target = os.environ["PRESENTATION_TARGET"]
assert target in ("jakarta", "quarkus", "spring"), target
port = 9080 if target == "jakarta" else 8080
cookie = None

def request(method, path, body=None, content_type=None, accept=None):
    global cookie
    conn = http.client.HTTPConnection("localhost", port, timeout=10)
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    if accept:
        headers["Accept"] = accept
    if cookie:
        headers["Cookie"] = cookie
    if isinstance(body, dict):
        body = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    try:
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        if response.getheader("Set-Cookie"):
            cookie = response.getheader("Set-Cookie").split(";", 1)[0]
        return response.status, response.read(), dict(response.getheaders())
    finally:
        conn.close()

def ready(path, accept=None):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            status, body, headers = request("GET", path, accept=accept)
            if status == 200:
                return body
        except (OSError, TimeoutError):
            pass
        time.sleep(2)
    raise AssertionError(f"{path} did not become ready")

def expect(status, actual, body):
    assert actual == status, f"expected HTTP {status}, got {actual}: {body[:400]!r}"

path = "/mood-10-SNAPSHOT/report" if target == "jakarta" else "/report"
allowed = {"awake", "sleepy", "alert", "hungry", "in need of coffee", "thoughtful", "lethargic", "neutral"}

def check_report(body):
    html = body.decode("utf-8")
    assert "Servlet MoodServlet" in html, html[:400]
    found = re.search(r"Duke's mood is:\s*([^<]+)", html)
    assert found and found.group(1).strip() in allowed, html[:400]
    image = re.search(r'<img\s+src="([^"]+\.gif)"', html)
    assert image, html[:400]
    return found.group(1).strip(), image.group(1)

first = ready(path)
mood, image = check_report(first)
status, body, _ = request("POST", path, b"name=ScarfBench", "application/x-www-form-urlencoded")
expect(200, status, body)
second_mood, _ = check_report(body)
assert second_mood in allowed, second_mood
image_path = image if image.startswith("/") else path.rsplit("/", 1)[0] + "/" + image
status, image_bytes, _ = request("GET", image_path)
expect(200, status, image_bytes)
assert image_bytes.startswith((b"GIF87a", b"GIF89a")), image_bytes[:20]
print("PASS mood report, POST rendering and GIF asset")
"""

def render(target):
    return ('#!/usr/bin/env bash\nset -euo pipefail\n'
            + 'export PRESENTATION_TARGET="${PRESENTATION_TARGET:-' + target + '}"\n'
            + "python3 - <<'PY'\n" + TEST_PY + "PY\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    failed = False
    for target in ('jakarta', 'quarkus', 'spring'):
        path = base / target / 'test.sh'
        content = render(target)
        if args.check:
            if path.read_text() != content:
                print(f'outdated: {path}', file=sys.stderr)
                failed = True
        else:
            path.write_text(content)
            path.chmod(0o755)
    return int(failed)

if __name__ == '__main__':
    raise SystemExit(main())
