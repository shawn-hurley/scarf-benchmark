#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")" && pwd)"

render() {
  cat <<'SHELL_HEADER'
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/cargo-tracker}"
export BASE_URL

python3 - <<'SCARFBENCH_CARGOTRACKER_BEHAVIOR'
SHELL_HEADER
  cat "$root/behavior_test.py"
  printf '\nSCARFBENCH_CARGOTRACKER_BEHAVIOR\n'
}

for target in jakarta quarkus spring; do
  script="$root/$target/test.sh"
  if [[ "${1:-}" == "--check" ]]; then
    diff -u "$script" <(render)
  else
    render > "$script"
    chmod +x "$script"
  fi
done
