#!/usr/bin/env bash
set -euo pipefail
export PRESENTATION_TARGET="${PRESENTATION_TARGET:-jakarta}"
python3 - <<'PY'

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

base = "/jaxrs-customer-10-SNAPSHOT/webapi/Customer" if target == "jakarta" else "/webapi/Customer"
initial = json.loads(ready(base + "/all", "application/json"))
assert isinstance(initial, list), initial
unique = "scarfbench-" + str(time.time_ns()) + "@example.test"
customer = {
    "firstname": "Scarf", "lastname": "Bench", "email": unique,
    "phone": "5550100",
    "address": {"number": 14, "street": "Test Street", "city": "Boston",
                "province": "MA", "zip": "02110", "country": "USA"}
}
status, body, headers = request("POST", base, customer, accept="application/json")
expect(201, status, body)
location = headers.get("Location", headers.get("location", ""))
assert urlparse(location).path.rsplit("/", 1)[-1].isdigit(), location
status, body, _ = request("GET", base + "/all", accept="application/json")
expect(200, status, body)
matches = [item for item in json.loads(body) if item.get("email") == unique]
assert len(matches) == 1, body[:500]
found = matches[0]
assert found["firstname"] == "Scarf" and found["lastname"] == "Bench", found
assert found["address"]["city"] == "Boston", found
print("PASS customer creation and persisted listing")
PY
