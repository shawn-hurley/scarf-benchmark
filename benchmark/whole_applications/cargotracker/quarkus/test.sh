#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/cargo-tracker}"
export BASE_URL

python3 - <<'SCARFBENCH_CARGOTRACKER_BEHAVIOR'
#!/usr/bin/env python3
"""Shared HTTP contract for CargoTracker's route candidate service."""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080/cargo-tracker").rstrip("/")
ROUTE_URL = BASE_URL + "/rest/graph-traversal/shortest-path"
LOCATIONS = {
    "CNHKG", "AUMEL", "SESTO", "FIHEL", "USCHI", "JNTKO", "DEHAM",
    "CNSHA", "NLRTM", "SEGOT", "CNHGH", "USNYC", "USDAL",
}
VOYAGES = {"0100S", "0200T", "0300A", "0301S", "0400S"}


def candidates(origin, destination):
    query = urllib.parse.urlencode({"origin": origin, "destination": destination})
    request = urllib.request.Request(ROUTE_URL + "?" + query, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        assert response.status == 200, f"route lookup returned {response.status}"
        result = json.load(response)
    # Quarkus wraps the collection to give its REST JSON provider a concrete type.
    if isinstance(result, dict):
        result = result.get("transitPaths")
    assert isinstance(result, list), f"expected route candidates, got {result!r}"
    assert 3 <= len(result) <= 5, f"expected 3-5 candidates, got {len(result)}"
    for path in result:
        edges = path.get("transitEdges")
        assert isinstance(edges, list) and 1 <= len(edges) <= 6, f"invalid route: {path!r}"
        visited = {origin}
        current = origin
        for index, edge in enumerate(edges):
            assert edge["fromUnLocode"] == current, f"disconnected leg: {edge!r}"
            target = edge["toUnLocode"]
            assert target in LOCATIONS, f"unknown destination: {target!r}"
            assert target not in visited, f"route repeats a location: {target!r}"
            assert edge["voyageNumber"] in VOYAGES, f"unknown voyage: {edge!r}"
            assert edge.get("fromDate") and edge.get("toDate"), f"missing leg dates: {edge!r}"
            if index < len(edges) - 1:
                assert target != destination, "route reaches destination before final leg"
            visited.add(target)
            current = target
        assert current == destination, f"route ends at {current}, expected {destination}"


deadline = time.monotonic() + 180
while True:
    try:
        candidates("CNHKG", "USNYC")
        break
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        if time.monotonic() >= deadline:
            raise
        time.sleep(2)

candidates("AUMEL", "DEHAM")
print("PASS: two route lookups returned valid, connected cargo itineraries")

SCARFBENCH_CARGOTRACKER_BEHAVIOR
