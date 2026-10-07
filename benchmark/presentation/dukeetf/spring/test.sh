#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://localhost:8080}"
SCARFBENCH_TARGET="${SCARFBENCH_TARGET:-spring}"
# One HTTP request waits for the next generated price/volume tick.
case "$SCARFBENCH_TARGET" in
  jakarta) path=/dukeetf-10-SNAPSHOT/dukeetf ;;
  quarkus|spring) path=/dukeetf ;;
  *) echo "Unknown target: $SCARFBENCH_TARGET" >&2; exit 1 ;;
esac

url="${BASE_URL%/}${path}"
sample() {
  local body
  body="$(curl -fsS --max-time 10 "$url" 2>/dev/null)" || return 1
  [[ "$body" =~ ^[0-9]+\.[0-9][0-9]\ /\ [0-9]+$ ]] || return 1
  local price="${body%% *}" volume="${body##* }"
  awk -v p="$price" -v v="$volume" 'BEGIN { exit !(p > 0 && p < 10000 && v >= 0) }'
}

ready=0
for attempt in $(seq 1 90); do
  if sample; then ready=1; break; fi
  sleep 2
done
[[ "$ready" -eq 1 ]] || { echo "No valid ETF update from $path" >&2; exit 1; }
sample || { echo "Second ETF update was invalid" >&2; exit 1; }
echo 'PASS: two ETF updates carried valid price and volume values'
