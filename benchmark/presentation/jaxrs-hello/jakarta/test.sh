#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://localhost:9080}"
SCARFBENCH_TARGET="${SCARFBENCH_TARGET:-jakarta}"
# Shared JAX-RS Hello behavior: the route and representation must survive migration.
case "$SCARFBENCH_TARGET" in
  jakarta) path=/jaxrs-hello-10-SNAPSHOT/helloworld ;;
  quarkus|spring) path=/helloworld ;;
  *) echo "Unknown target: $SCARFBENCH_TARGET" >&2; exit 1 ;;
esac

url="${BASE_URL%/}${path}"
body_file="$(mktemp)"
headers_file="$(mktemp)"
trap 'rm -f "$body_file" "$headers_file"' EXIT

ready=0
for attempt in $(seq 1 90); do
  if curl -fsS --max-time 5 -D "$headers_file" -o "$body_file" "$url" 2>/dev/null; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" -ne 1 ]]; then
  echo "GET $path never became ready" >&2
  exit 1
fi

expected='<html lang="en"><body><h1>Hello, World!!</h1></body></html>'
[[ "$(cat "$body_file")" == "$expected" ]] || { echo "GET $path returned the wrong greeting" >&2; exit 1; }
grep -qi '^content-type: text/html' "$headers_file" || { echo "GET $path did not return HTML" >&2; exit 1; }

status="$(curl -sS --max-time 5 -o "$body_file" -w '%{http_code}' -X PUT -H 'Content-Type: text/html' --data '<p>replacement</p>' "$url")"
[[ "$status" == 204 || "$status" == 200 ]] || { echo "PUT $path returned HTTP $status" >&2; exit 1; }

curl -fsS --max-time 5 -o "$body_file" "$url"
[[ "$(cat "$body_file")" == "$expected" ]] || { echo "PUT changed the greeting" >&2; exit 1; }
echo 'PASS: Hello endpoint returns the expected HTML and accepts PUT without changing it'
