#!/usr/bin/env bash
set -euo pipefail
case "${INFRA_TARGET:-jakarta}" in
  jakarta) origin="${BASE_URL:-http://localhost:9080}"; prefix=/jobs ;;
  quarkus) origin="${BASE_URL:-http://localhost:8080}"; prefix=/jobs ;;
  spring) origin="${BASE_URL:-http://localhost:9080}"; prefix='' ;;
  *) echo 'Unknown INFRA_TARGET' >&2; exit 2 ;;
esac
api="${origin}${prefix}/webapi/JobService"
# The token and process paths are part of the example's public contract.
token=$(curl --retry 30 --retry-connrefused --retry-delay 2 --fail --silent --show-error "$api/token")
[[ "$token" =~ ^123X5-[0-9a-fA-F-]{36}$ ]] || { echo "Bad token: $token" >&2; exit 1; }
job_id=2147
for mode in low high; do
  args=()
  if [[ "$mode" == high ]]; then args=(-H "X-REST-API-Key: $token"); fi
  response=$(curl --fail --silent --show-error -X POST "${args[@]}" "$api/process?jobID=$job_id")
  [[ "$response" == "Job $job_id successfully submitted." ]] || { echo "Bad $mode response: $response" >&2; exit 1; }
done
echo 'PASS: token issued and both priority paths accept job submissions'
