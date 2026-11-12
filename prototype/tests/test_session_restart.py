"""HTTP -> real PostgreSQL, then a full server restart with the same cookie."""
import http.cookiejar
import json
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
config = json.loads((ROOT / '.local/connection.json').read_text())
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
base = f'http://127.0.0.1:{port}'
jar = http.cookiejar.CookieJar()
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def start():
    process = subprocess.Popen([sys.executable, str(ROOT / 'app.py'), '--port', str(port)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(base + '/api/session', timeout=1).close()
            return process
        except (urllib.error.URLError, OSError):
            time.sleep(.1)
    process.terminate()
    raise RuntimeError('Test server did not start')


def stop(process):
    process.send_signal(signal.SIGINT)
    process.wait(timeout=5)


def request(path, body=None, csrf='', origin=None):
    headers = {'Origin': origin or base, 'X-CSRF-Token': csrf, 'Content-Type': 'application/json'}
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers=headers)
    with client.open(req, timeout=15) as response:
        return json.loads(response.read())


process = start()
checks = []
try:
    login = request('/api/login', {'username': config['users']['1']['user'],
                                   'password': config['users']['1']['password']})
    assert login['profile']['user_id'] == 1
    checks.append('Real database login accepted')
    stop(process)
    process = start()
    session = request('/api/session')
    assert session['profile']['user_id'] == 1 and session['csrf'] == login['csrf']
    checks.append('Login survives complete HTTP process restart')
    result = request('/api/action', {'action': 'profile', 'payload': {}}, session['csrf'])
    assert result['data']['user_id'] == 1
    checks.append('Restored session can query PostgreSQL')
    for csrf, origin in [('wrong', base), (session['csrf'], 'https://attacker.invalid')]:
        try:
            request('/api/action', {'action': 'profile', 'payload': {}}, csrf, origin)
            raise AssertionError('Untrusted request accepted')
        except urllib.error.HTTPError as error:
            assert error.code == 403
    checks.append('CSRF and cross-origin requests rejected')
    request('/api/logout', {}, session['csrf'])
    assert request('/api/session')['profile'] is None
    checks.append('Logout clears the browser cookie')
    print(json.dumps({'passed': True, 'checks': checks}))
finally:
    if process.poll() is None:
        stop(process)
