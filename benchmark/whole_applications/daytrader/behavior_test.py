"""Shared DayTrader stock quote behavior, embedded into each standalone test.sh."""
import json
import math
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request(base, path, data=None):
    body = urlencode(data).encode() if data is not None else None
    req = Request(base + path, data=body)
    try:
        with urlopen(req, timeout=180 if path.startswith('/config') else 10) as response:
            return response.status, response.read().decode('utf-8')
    except HTTPError as error:
        return error.code, error.read().decode('utf-8')


def quotes(base, symbols, post=False):
    path = '/rest/quotes' if post else '/rest/quotes/' + symbols
    status, body = request(base, path, {'symbols': symbols} if post else None)
    if status != 200:
        raise AssertionError(f'{path}: HTTP {status}: {body[:300]}')
    value = json.loads(body)
    if not isinstance(value, list):
        raise AssertionError(f'{path}: expected a JSON array, got {body[:300]}')
    return value


def validate(items, expected):
    actual = [item.get('symbol') for item in items if isinstance(item, dict)]
    if actual != expected or len(items) != len(expected):
        raise AssertionError(f'quote symbols: expected {expected}, got {items}')
    for item in items:
        if not isinstance(item.get('companyName'), str) or not item['companyName'].strip():
            raise AssertionError(f'quote missing company name: {item}')
        if not math.isfinite(float(item['price'])) or float(item['price']) <= 0:
            raise AssertionError(f'quote has invalid price: {item}')


def main():
    candidates = [os.environ['BASE_URL'].rstrip('/')] if os.getenv('BASE_URL') else [
        'http://localhost:8080', 'http://localhost:9080/daytrader'
    ]
    base = None
    deadline = time.monotonic() + int(os.getenv('STARTUP_TIMEOUT', '180'))
    while time.monotonic() < deadline and base is None:
        for candidate in candidates:
            try:
                status, _ = request(candidate, '/')
                if status == 200:
                    base = candidate
                    break
            except (OSError, URLError):
                pass
        if base is None:
            time.sleep(2)
    if base is None:
        raise AssertionError(f'DayTrader did not start at {candidates}')
    print(f'DayTrader at {base}', flush=True)

    try:
        initial = quotes(base, 's:0')
    except (AssertionError, ValueError) as error:
        initial = []
        print(f'Quote lookup before setup: {error}', flush=True)
    if not initial:
        if base.endswith(':8080'):
            raise AssertionError('Quarkus did not populate its database on startup')
        status, body = request(base, '/config?action=updateConfig&MaxUsers=2&MaxQuotes=3')
        if status != 200:
            raise AssertionError(f'Could not set seed size: HTTP {status}: {body[:300]}')
        status, body = request(base, '/config?action=buildDB')
        if status != 200:
            raise AssertionError(f'Could not populate database: HTTP {status}: {body[-600:]}')
        # Liberty starts with an empty H2 database and buildDB silently skips
        # inserts until its tables have been created. Spring creates its schema
        # on startup, so only perform this second step if quotes are still absent.
        if not quotes(base, 's:0'):
            status, body = request(base, '/config?action=buildDBTables')
            if status != 200 or 'DayTrader tables successfully created!' not in body:
                raise AssertionError(f'Could not create database tables: HTTP {status}: {body[-600:]}')
            status, body = request(base, '/config?action=buildDB')
            if status != 200:
                raise AssertionError(f'Could not populate new tables: HTTP {status}: {body[-600:]}')

    validate(quotes(base, 's:0'), ['s:0'])
    validate(quotes(base, 's:0,s:1'), ['s:0', 's:1'])
    validate(quotes(base, 's:1,s:0', post=True), ['s:1', 's:0'])
    print('PASS: GET and POST returned persisted quotes in requested order with valid prices')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'FAIL: {error}', file=sys.stderr)
        sys.exit(1)
