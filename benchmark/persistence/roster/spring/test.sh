#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PYTEST'
import json, os, time, urllib.error, urllib.request
from urllib.parse import urlsplit
profile=os.environ.get("SCARF_TARGET","quarkus")
assert profile in ("spring","jakarta","quarkus"),profile
port=9080 if profile=="jakarta" else 8080
base=os.environ.get("BASE_URL",f"http://localhost:{port}/roster").rstrip("/")
assert urlsplit(base).path=="/roster", f"Expected exact /roster path, got {urlsplit(base).path!r}"
league_id="SCARF"+str(int(time.time()*1000)%100000000)
url=base+"/league/"+league_id

def request(method, target, payload=None):
    data=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(target,data=data,method=method,headers={"Content-Type":"application/json","Accept":"application/json"})
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl): return None
    opener=urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req,timeout=12) as response:
            return response.status,response.read().decode()
    except urllib.error.HTTPError as e:
        return e.code,e.read().decode()

deadline=time.monotonic()+300
while True:
    try:
        status,_=request("GET",base+"/players")
        if status==200: break
    except Exception: pass
    if time.monotonic()>deadline: raise AssertionError("Roster exact path did not become ready")
    time.sleep(2)
status,_=request("POST",base+"/league",{"id":league_id,"name":"Scarf League","sport":"soccer"})
assert status in (200,201,204),f"Create league status {status}"
status,body=request("GET",url)
assert status==200,f"Read league status {status}: {body[:300]}"
league=json.loads(body)
assert league["id"]==league_id and league["name"]=="Scarf League" and league["sport"].lower()=="soccer",league
status,_=request("DELETE",url)
assert status in (200,204),f"Delete league status {status}"
status,_=request("GET",url)
assert status!=200,f"Deleted league still accessible: {status}"
print(f"PASS roster ({profile}): exact path and league CRUD")
PYTEST
