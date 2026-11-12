"""Loop course prototype. Local HTTP sessions authenticate actual PostgreSQL roles."""
import argparse
from datetime import date, datetime
from decimal import Decimal
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import secrets
import threading
import time
import unicodedata
from urllib.parse import urlsplit

import psycopg
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / '.local/connection.json').read_text())
SESSIONS = {}
SESSION_LOCK = threading.Lock()
DB_SLOTS = threading.BoundedSemaphore(8)
ACTIONS = {'profile', 'bootstrap', 'feed', 'comments', 'collections', 'publish',
           'hide', 'unhide', 'edit', 'tag', 'untag', 'like', 'unlike', 'follow',
           'unfollow', 'comment', 'create_collection', 'collect', 'remove_collection_item'}


def connect(username, password):
    return psycopg.connect(host=CONFIG['host'], port=CONFIG.get('port', 5432),
        dbname=CONFIG['dbname'], user=username, password=password,
        sslmode='verify-full', sslrootcert=str(ROOT / 'supabase-ca.crt'),
        connect_timeout=8, options='-c statement_timeout=10000 -c lock_timeout=5000')


def encode(value):
    if isinstance(value, (datetime, date, Decimal)):
        return str(value)
    raise TypeError(type(value).__name__)


class Handler(BaseHTTPRequestHandler):
    server_version = 'IS5413-Demo/1.0'

    def log_message(self, fmt, *args):
        # Never log request bodies, session tokens, passwords or database errors.
        return

    def headers_common(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; media-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        self.send_header('Cache-Control', 'no-store')

    def respond(self, data, status=200, cookie=None):
        body = json.dumps(data, default=encode, ensure_ascii=False).encode()
        self.send_response(status)
        self.headers_common()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(body)

    def session(self):
        cookies = SimpleCookie()
        try:
            cookies.load(self.headers.get('Cookie', ''))
            token = cookies['loop_session'].value
        except Exception:
            return None, None
        with SESSION_LOCK:
            s = SESSIONS.get(token)
            if s and s['expires'] > time.time():
                return token, s
            SESSIONS.pop(token, None)
        return None, None

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/session':
            _, s = self.session()
            self.respond({'profile': s['profile'], 'csrf': s['csrf']} if s else {'profile': None})
            return
        if path.startswith('/api/'):
            self.respond({'error': 'Not found'}, 404)
            return
        target = (ROOT / 'static' / ('index.html' if path == '/' else path.lstrip('/'))).resolve()
        if not target.is_relative_to((ROOT / 'static').resolve()) or not target.is_file():
            self.respond({'error': 'Not found'}, 404)
            return
        data = target.read_bytes()
        self.send_response(200)
        self.headers_common()
        self.send_header('Content-Type', mimetypes.guess_type(str(target))[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        origin = f'http://127.0.0.1:{self.server.server_port}'
        if self.headers.get('Origin') != origin or self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
            self.respond({'error': 'Local same-origin requests only'}, 403)
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 20000:
                raise ValueError('Invalid request size')
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError('Expected an object')
            path = urlsplit(self.path).path
            if path == '/api/login':
                username, password = body.get('username', ''), body.get('password', '')
                if username not in {f'douyin_demo_u{i}' for i in range(1, 6)} or not isinstance(password, str):
                    self.respond({'error': 'Invalid demo credentials'}, 401)
                    return
                try:
                    with DB_SLOTS, connect(username, password) as conn:
                        profile = conn.execute("SELECT douyin.app('profile')").fetchone()[0]
                except psycopg.Error:
                    self.respond({'error': 'Login failed. Check the database credentials and network.'}, 401)
                    return
                token = secrets.token_urlsafe(32)
                s = dict(username=username, password=password, profile=profile,
                         csrf=secrets.token_urlsafe(24), expires=time.time() + 3600)
                with SESSION_LOCK:
                    # Expired credentials are removed from memory on subsequent logins.
                    for key in [k for k, v in SESSIONS.items() if v['expires'] <= time.time()]:
                        SESSIONS.pop(key, None)
                    SESSIONS[token] = s
                self.respond({'profile': profile, 'csrf': s['csrf']}, cookie=f'loop_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600')
                return
            token, s = self.session()
            if not s:
                self.respond({'error': 'Please sign in'}, 401)
                return
            if not secrets.compare_digest(self.headers.get('X-CSRF-Token', ''), s['csrf']):
                self.respond({'error': 'Invalid CSRF token'}, 403)
                return
            if path == '/api/logout':
                with SESSION_LOCK:
                    SESSIONS.pop(token, None)
                self.respond({'ok': True}, cookie='loop_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
                return
            if path != '/api/action':
                self.respond({'error': 'Not found'}, 404)
                return
            action, payload = body.get('action'), body.get('payload', {})
            if not isinstance(payload, dict):
                raise ValueError('Expected payload object')
            for key in ('caption', 'name', 'body_text', 'search'):
                if key in payload and isinstance(payload[key], str):
                    payload[key] = unicodedata.normalize('NFC', payload[key]).strip()
            with DB_SLOTS, connect(s['username'], s['password']) as conn:
                if action == 'report':
                    result = conn.execute('SELECT douyin.report(%s)', (payload.get('id'),)).fetchone()[0]
                elif action in ACTIONS:
                    result = conn.execute('SELECT douyin.app(%s, %s)', (action, Jsonb(payload))).fetchone()[0]
                else:
                    raise ValueError('Unknown action')
            self.respond({'data': result})
        except psycopg.Error as exc:
            code = exc.sqlstate or 'database_error'
            public_message = exc.diag.message_primary if code in {'42501', '23514', '23503', '23505', '23502', '22023'} else 'Database operation failed'
            self.respond({'error': public_message, 'code': code}, 403 if code == '42501' else 409)
        except (ValueError, TypeError, KeyError):
            self.respond({'error': 'Invalid request'}, 400)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5413)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Loop prototype: http://127.0.0.1:{args.port}', flush=True)
    print('Demo credentials remain in prototype/.local/connection.json; do not submit that file.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
