#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://localhost:8080}"
SCARFBENCH_TARGET="${SCARFBENCH_TARGET:-spring}"
export BASE_URL SCARFBENCH_TARGET
python3 - <<'PY'
import base64
import os
import re
import socket
import time
from urllib.parse import urlsplit
from urllib.request import urlopen
from urllib.error import URLError

target = os.environ['SCARFBENCH_TARGET']
base = os.environ['BASE_URL'].rstrip('/')
path = '/dukeetf2-10-SNAPSHOT/dukeetf' if target == 'jakarta' else '/dukeetf'
if target not in ('jakarta', 'quarkus', 'spring'):
    raise SystemExit(f'Unknown target: {target}')

page_path = '/dukeetf2-10-SNAPSHOT/' if target == 'jakarta' else ('/index.html' if target == 'quarkus' else '/')
deadline = time.monotonic() + 90
while True:
    try:
        with urlopen(base + page_path, timeout=10) as response:
            html = response.read().decode()
        break
    except (OSError, URLError) as error:
        if time.monotonic() >= deadline:
            raise SystemExit(f'ETF page failed: {error}')
        time.sleep(2)
assert ("Duke's WebSocket ETF" in html and 'id="price"' in html
        and 'id="volume"' in html and 'new WebSocket' in html
        and 'location.host' in html and path in html)

url = urlsplit(base)
host = url.hostname
port = url.port or 80
deadline = time.monotonic() + 90
while True:
    try:
        with socket.create_connection((host, port), timeout=10) as connection:
            connection.settimeout(10)
            key = base64.b64encode(os.urandom(16)).decode()
            request = (f'GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n'
                       f'Upgrade: websocket\r\nConnection: Upgrade\r\n'
                       f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n')
            connection.sendall(request.encode())
            stream = connection.makefile('rb')
            status = stream.readline().decode().strip()
            if len(status.split()) < 2 or status.split()[1] != '101':
                raise AssertionError(f'WebSocket upgrade failed: {status}')
            while stream.readline().strip():
                pass
            updates = []
            while len(updates) < 2:
                header = stream.read(2)
                if len(header) != 2:
                    raise AssertionError('WebSocket closed before two updates')
                opcode = header[0] & 15
                length = header[1] & 127
                if length == 126:
                    length = int.from_bytes(stream.read(2), 'big')
                elif length == 127:
                    length = int.from_bytes(stream.read(8), 'big')
                payload = stream.read(length).decode()
                if opcode != 1:
                    raise AssertionError(f'Expected text frame, got opcode {opcode}')
                if not re.fullmatch(r'\d+\.\d{2} / \d+', payload):
                    raise AssertionError(f'Invalid price/volume update: {payload!r}')
                price, volume = payload.split(' / ')
                if not (0 < float(price) < 10000 and int(volume) >= 0):
                    raise AssertionError(f'Out-of-range ETF update: {payload!r}')
                updates.append(payload)
            print(f'PASS: received two valid WebSocket ETF updates at {path}')
            break
    except (OSError, AssertionError) as error:
        if time.monotonic() >= deadline:
            raise SystemExit(f'ETF WebSocket failed: {error}')
        time.sleep(2)
PY
