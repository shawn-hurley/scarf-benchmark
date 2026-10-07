#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
export BASE_URL
export PETCLINIC_TARGET="${PETCLINIC_TARGET:-quarkus}"

python3 - <<'SCARFBENCH_PETCLINIC_BEHAVIOR'
"""PetClinic's shared veterinarian and owner/pet behavior contract."""

import json
import os
import time
import urllib.error
import urllib.request


BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080").rstrip("/")
TARGET = os.environ["PETCLINIC_TARGET"]
PATHS = {
    "jakarta": ("/petclinic/rest/vet/list", "/petclinic/rest/owner/2"),
    "quarkus": ("/vets", "/owners/1001"),
    "spring": ("/vets", "/owners?lastName=Franklin"),
}


def get(path):
    url = BASE_URL + path
    last_error = None
    for _ in range(60):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                body = response.read().decode("utf-8")
                if response.status != 200:
                    raise AssertionError(f"{path}: HTTP {response.status}")
                return body
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
            time.sleep(2)
    raise AssertionError(f"{path}: application did not become ready: {last_error}")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def verify_vets():
    path, _ = PATHS[TARGET]
    data = json.loads(get(path))
    vets = data if TARGET == "jakarta" else data["vetList"]
    require(isinstance(vets, list) and len(vets) >= 2, "vet list must contain records")
    ids = set()
    with_specialty = 0
    for vet in vets:
        require(vet.get("firstName") and vet.get("lastName"), "vet needs a full name")
        require(vet.get("id") not in ids, "vet IDs must be unique")
        ids.add(vet.get("id"))
        specialties = vet.get("specialtyList", {}).get("specialty", []) if TARGET == "jakarta" else vet.get("specialties", [])
        if specialties:
            with_specialty += 1
            require(all(item.get("name") for item in specialties), "specialty needs a name")
    require(with_specialty > 0, "vet specialties must be joined to vets")


def verify_owner_and_pet():
    _, path = PATHS[TARGET]
    body = get(path)
    if TARGET == "jakarta":
        owner = json.loads(body)
        require(owner.get("firstName") == "Justus" and owner.get("lastName") == "Jonas", "owner lookup returned the wrong owner")
        pets = owner.get("petList", {}).get("pet", [])
        require({pet.get("name") for pet in pets} >= {"Roger", "Jerry", "Tom"}, "owner lookup lost pet relationships")
    else:
        require("George" in body and "Franklin" in body, "owner lookup returned the wrong owner")
        require("Leo" in body, "owner page lost the owner's pet")
        if TARGET == "spring":
            require("/owners/" in body, "owner search did not resolve to an owner page")


verify_vets()
verify_owner_and_pet()
print("PASS: PetClinic shared behavior contract")

SCARFBENCH_PETCLINIC_BEHAVIOR
