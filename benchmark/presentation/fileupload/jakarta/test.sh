#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://localhost:9080}"
SCARFBENCH_TARGET="${SCARFBENCH_TARGET:-jakarta}"
# Upload a real file and verify the application wrote its exact bytes.
case "$SCARFBENCH_TARGET" in
  jakarta) path=/fileupload/upload ;;
  quarkus|spring) path=/upload ;;
  *) echo "Unknown target: $SCARFBENCH_TARGET" >&2; exit 1 ;;
esac

url="${BASE_URL%/}${path}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
destination="$work/destination"
mkdir -p "$destination"
filename=payload.txt
printf 'ScarfBench file upload %s\nSecond line\n' "$$" > "$work/$filename"

ready=0
for attempt in $(seq 1 90); do
  status="$(curl -sS --max-time 10 -o "$work/response" -w '%{http_code}' \
    -F "destination=$destination" -F "filename=$filename" \
    -F "file=@$work/$filename;filename=$filename;type=application/octet-stream" \
    "$url" 2>/dev/null)" || status=000
  if [[ "$status" == 200 ]] && grep -Fq "New file $filename created at $destination" "$work/response"; then
    ready=1
    break
  fi
  sleep 2
done
[[ "$ready" -eq 1 ]] || { echo "POST $path did not upload the file (HTTP $status)" >&2; exit 1; }
cmp "$work/$filename" "$destination/$filename" || { echo "Uploaded file contents differ" >&2; exit 1; }
echo 'PASS: multipart upload wrote the expected file bytes'
