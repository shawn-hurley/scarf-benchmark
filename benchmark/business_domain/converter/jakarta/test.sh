#!/usr/bin/env bash
set -euo pipefail
export BUSINESS_DOMAIN_TARGET="${BUSINESS_DOMAIN_TARGET:-jakarta}"
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

base = "/converter/"
landing = ready(base)
assert "Enter a dollar amount to convert:" in landing and 'name="amount"' in landing, landing[:400]
for amount, yen, euro in (("10", "1043.40", "7.31"), ("0.5", "52.17", "0.37")):
    status, body = request("GET", base + "?amount=" + amount)
    expect(200, status, body)
    assert f"{amount} dollars are {yen} yen." in body, body[:400]
    assert f"{yen} yen are {euro} Euro." in body, body[:400]
print("PASS currency conversion and input form")
PY
