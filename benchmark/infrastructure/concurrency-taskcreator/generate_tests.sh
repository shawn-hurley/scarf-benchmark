#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
for target in quarkus spring; do
  if [[ "${1:-}" == --check ]]; then
    cmp "$root/jakarta/test.sh" "$root/$target/test.sh"
  else
    cp "$root/jakarta/test.sh" "$root/$target/test.sh"
    chmod +x "$root/$target/test.sh"
  fi
done
