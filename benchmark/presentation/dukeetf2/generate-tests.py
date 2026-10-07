#!/usr/bin/env python3
"""Embed the shared behavior check in each self-contained target test.sh."""
from pathlib import Path

root = Path(__file__).resolve().parent
behavior = (root / 'behavior_test.sh').read_text()
for target, port in [('jakarta', 9080), ('quarkus', 8080), ('spring', 8080)]:
    script = (f'#!/usr/bin/env bash\nset -euo pipefail\n'
              f'BASE_URL="${{BASE_URL:-http://localhost:{port}}}"\n'
              f'SCARFBENCH_TARGET="${{SCARFBENCH_TARGET:-{target}}}"\n'
              'export BASE_URL SCARFBENCH_TARGET\n' + behavior)
    path = root / target / 'test.sh'
    path.write_text(script)
    path.chmod(0o755)
