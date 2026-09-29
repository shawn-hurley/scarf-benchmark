#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")" && pwd)"

render() {
  local target="$1"
  cat <<SHELL_HEADER
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="\${BASE_URL:-http://localhost:8080}"
export BASE_URL
export PETCLINIC_TARGET="$target"

python3 - <<'SCARFBENCH_PETCLINIC_BEHAVIOR'
SHELL_HEADER
  cat "$root/behavior_test.py"
  printf '\nSCARFBENCH_PETCLINIC_BEHAVIOR\n'
}

for target in jakarta quarkus spring; do
  script="$root/$target/test.sh"
  if [[ "${1:-}" == "--check" ]]; then
    diff -u "$script" <(render "$target")
  else
    render "$target" > "$script"
    chmod +x "$script"
  fi
done
