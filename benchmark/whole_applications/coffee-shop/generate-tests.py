#!/usr/bin/env python3
"""Generate the three standalone scripts from one behavior contract."""
import argparse
from pathlib import Path
import sys


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--check", action="store_true", help="fail if generated scripts differ; do not write files")
args = parser.parse_args()

root = Path(__file__).resolve().parent
template = (root / "behavior-test.sh.in").read_text()
stale = []
for target in ("jakarta", "quarkus", "spring"):
    output = root / target / "test.sh"
    expected = template.replace("__TARGET__", target)
    if args.check:
        if not output.is_file() or output.read_text() != expected:
            stale.append(output.relative_to(root))
    else:
        output.write_text(expected)
        output.chmod(0o755)

if stale:
    for path in stale:
        print(f"out of date: {path}", file=sys.stderr)
    print("Run python3 generate-tests.py to regenerate the scripts.", file=sys.stderr)
    sys.exit(1)
