#!/usr/bin/env python3
"""Generate the three standalone scripts from one behavior contract."""
from pathlib import Path

root = Path(__file__).resolve().parent
template = (root / "behavior-test.sh.in").read_text()
for target in ("jakarta", "quarkus", "spring"):
    output = root / target / "test.sh"
    output.write_text(template.replace("__TARGET__", target))
    output.chmod(0o755)
