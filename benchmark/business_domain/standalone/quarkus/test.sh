#!/usr/bin/env bash
set -euo pipefail
export BUSINESS_DOMAIN_TARGET="${BUSINESS_DOMAIN_TARGET:-quarkus}"
python3 - <<'PY'

import http.client
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

target = os.environ["BUSINESS_DOMAIN_TARGET"]
assert target in ("jakarta", "quarkus", "spring"), target
port = 9080 if target == "jakarta" else 8080
cookie = None

def request(method, path, body=None, content_type=None):
    global cookie
    conn = http.client.HTTPConnection("localhost", port, timeout=10)
    headers = {"Content-Type": content_type} if content_type else {}
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
        return response.status, response.read().decode("utf-8")
    finally:
        conn.close()

def ready(path):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            status, body = request("GET", path)
            if status == 200:
                return body
        except (OSError, TimeoutError):
            pass
        time.sleep(2)
    raise AssertionError(f"{path} did not become ready")

def expect(status, actual, body):
    assert actual == status, f"expected HTTP {status}, got {actual}: {body[:400]}"

path = "/standalone/greet"
body = ready(path)
assert json.loads(body) == {"message": "Greetings!"}, body
print("PASS standalone greeting")
PY
