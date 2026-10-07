#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
render() {
  cat <<'HEADER'
#!/usr/bin/env bash
set -euo pipefail
python3 - <<'DAYTRADER_BEHAVIOR'
HEADER
  cat "$root/behavior_test.py"
  printf '\nDAYTRADER_BEHAVIOR\n'
}
for target in jakarta quarkus spring; do
  script="$root/$target/test.sh"
  if [[ "${1:-}" == '--check' ]]; then
    diff -u "$script" <(render)
  else
    render > "$script"
    chmod +x "$script"
  fi
done
