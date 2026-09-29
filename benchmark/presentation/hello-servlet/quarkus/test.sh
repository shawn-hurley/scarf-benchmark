#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://localhost:8080}"
SCARFBENCH_TARGET="${SCARFBENCH_TARGET:-quarkus}"
# The greeting must use the requested name and reject a missing name.
case "$SCARFBENCH_TARGET" in
  jakarta) path=/hello-servlet/greeting ;;
  quarkus|spring) path=/greeting ;;
  *) echo "Unknown target: $SCARFBENCH_TARGET" >&2; exit 1 ;;
esac

url="${BASE_URL%/}${path}"
ready=0
for attempt in $(seq 1 90); do
  if curl -fsS --max-time 5 "$url?name=ScarfBench" 2>/dev/null | grep -Fxq 'Hello, ScarfBench!'; then
    ready=1
    break
  fi
  sleep 2
done
[[ "$ready" -eq 1 ]] || { echo "Greeting at $path did not become ready" >&2; exit 1; }

response="$(curl -fsS --max-time 5 "$url?name=Another%20Person")"
[[ "$response" == 'Hello, Another Person!' ]] || { echo "Greeting ignored the requested name: $response" >&2; exit 1; }

status="$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' "$url")"
[[ "$status" == 400 ]] || { echo "Missing name returned HTTP $status, expected 400" >&2; exit 1; }
echo 'PASS: greeting uses the name and rejects a missing parameter'
