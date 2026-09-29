#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"

render() {
  local target="$1" base
  if [[ "$target" == jakarta ]]; then base=http://localhost:9080; else base=http://localhost:8080; fi
  cat <<HEADER
#!/usr/bin/env bash
set -euo pipefail
BASE_URL="\${BASE_URL:-$base}"
SCARFBENCH_TARGET="\${SCARFBENCH_TARGET:-$target}"
HEADER
  cat "$root/behavior_test.sh"
}

for target in jakarta quarkus spring; do
  script="$root/$target/test.sh"
  if [[ "${1:-}" == --check ]]; then
    diff -u "$script" <(render "$target")
  else
    render "$target" > "$script"
    chmod +x "$script"
  fi
done
