"""Loop course prototype. Local HTTP sessions authenticate actual PostgreSQL roles."""
import argparse
import base64
import hashlib
import hmac
from datetime import date, datetime
from decimal import Decimal
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import secrets
import sys
import threading
import time
import unicodedata
from urllib.parse import urlsplit

import psycopg
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parent
_config_file = ROOT / '.local/connection.json'
CONFIG = json.loads(os.environ['LOOP_CONNECTION_JSON']) if os.environ.get('LOOP_CONNECTION_JSON') else (json.loads(_config_file.read_text()) if _config_file.exists() else {})
CLOUD = os.environ.get('VERCEL') == '1'
SESSION_TTL = 3600


def signing_key():
    configured = os.environ.get('LOOP_SESSION_KEY')
    if configured:
        if len(configured) < 32:
            raise RuntimeError('Session key must contain at least 32 characters')
        return configured.encode()
    if CLOUD:
        raise RuntimeError('Cloud session key is not configured')
    path = ROOT / '.local/session.key'
    path.parent.mkdir(exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as target:
            target.write(secrets.token_urlsafe(32))
    except FileExistsError:
        pass
    return path.read_bytes()


def seal_session(session):
    # The browser receives a signed identity, never a database password.
    key = signing_key()
    user = CONFIG['users'][str(session['profile']['user_id'])]
    value = dict(username=session['username'], profile=session['profile'],
                 csrf=session['csrf'], expires=session['expires'],
                 credential_version=hmac.new(key, user['password'].encode(), hashlib.sha256).hexdigest())
    data = base64.urlsafe_b64encode(json.dumps(value, separators=(',', ':')).encode()).rstrip(b'=')
    signature = base64.urlsafe_b64encode(hmac.new(key, data, hashlib.sha256).digest()).rstrip(b'=')
    return (data + b'.' + signature).decode()


def open_session(token):
    try:
        if not isinstance(token, str) or len(token) > 4096:
            return None
        data, signature = token.encode().split(b'.')
        key = signing_key()
        expected = base64.urlsafe_b64encode(hmac.new(key, data, hashlib.sha256).digest()).rstrip(b'=')
        if not hmac.compare_digest(signature, expected):
            return None
        value = json.loads(base64.urlsafe_b64decode(data + b'=' * (-len(data) % 4)))
        if not isinstance(value.get('expires'), (int, float)) or value['expires'] <= time.time():
            return None
        uid = value['profile']['user_id']
        user = CONFIG['users'][str(uid)]
        if value['username'] != user['user'] or not isinstance(value['csrf'], str):
            return None
        version = hmac.new(key, user['password'].encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(value.get('credential_version', ''), version):
            return None
        value['password'] = user['password']
        return value
    except (ValueError, KeyError, TypeError, RuntimeError):
        return None
DB_SLOTS = threading.BoundedSemaphore(8)
ACTIONS = {'profile', 'bootstrap', 'feed', 'comments', 'collections', 'publish',
           'hide', 'unhide', 'edit', 'tag', 'untag', 'like', 'unlike', 'follow',
           'unfollow', 'comment', 'create_collection', 'collect', 'remove_collection_item'}


def connect(username, password):
    return psycopg.connect(host=CONFIG['host'], port=CONFIG.get('port', 5432),
        dbname=CONFIG['dbname'], user=username + CONFIG.get('username_suffix', ''), password=password,
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
        session = open_session(token)
        return (token, session) if session else (None, None)

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
        # No forwarded host/proto is trusted. Vercel routes the real Host to this project.
        host = self.headers.get('Host', '')
        expected_host = host if CLOUD else f'127.0.0.1:{self.server.server_port}'
        origin = ('https://' if CLOUD else 'http://') + expected_host
        if not host or host != expected_host or self.headers.get('Origin') != origin:
            self.respond({'error': 'Same-origin requests only'}, 403)
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
                if not CONFIG.get('host') or not CONFIG.get('users'):
                    self.respond({'error': 'The service is not configured yet'}, 503)
                    return
                username, password = body.get('username', ''), body.get('password', '')
                if username not in {f'douyin_demo_u{i}' for i in range(1, 6)} or not isinstance(password, str):
                    self.respond({'error': 'Invalid demo credentials'}, 401)
                    return
                provisioned = next((u for u in CONFIG['users'].values() if u['user'] == username), None)
                if not provisioned or not secrets.compare_digest(password, provisioned['password']):
                    self.respond({'error': 'Invalid demo credentials'}, 401)
                    return
                try:
                    with DB_SLOTS, connect(username, password) as conn:
                        profile = conn.execute("SELECT douyin.app('profile')").fetchone()[0]
                except psycopg.OperationalError:
                    print('loop: database login connection unavailable', file=sys.stderr, flush=True)
                    self.respond({'error': 'Database temporarily unavailable. Please try again shortly.'}, 503)
                    return
                except psycopg.Error:
                    self.respond({'error': 'Login failed. Check the database credentials and network.'}, 401)
                    return
                s = dict(username=username, password=password, profile=profile,
                         csrf=secrets.token_urlsafe(24), expires=time.time() + SESSION_TTL)
                token = seal_session(s)
                secure = '; Secure' if CLOUD else ''
                self.respond({'profile': profile, 'csrf': s['csrf']}, cookie=f'loop_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}{secure}')
                return
            token, s = self.session()
            if not s:
                self.respond({'error': 'Please sign in'}, 401)
                return
            if not secrets.compare_digest(self.headers.get('X-CSRF-Token', ''), s['csrf']):
                self.respond({'error': 'Invalid CSRF token'}, 403)
                return
            if path == '/api/logout':
                secure = '; Secure' if CLOUD else ''
                self.respond({'ok': True}, cookie='loop_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0' + secure)
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
            if code == 'database_error':
                print('loop: database action connection unavailable', file=sys.stderr, flush=True)
            public_message = exc.diag.message_primary if code in {'42501', '23514', '23503', '23505', '23502', '22023'} else 'Database operation failed'
            self.respond({'error': public_message, 'code': code}, 403 if code == '42501' else 409)
        except (ValueError, TypeError, KeyError):
            self.respond({'error': 'Invalid request'}, 400)
        except RuntimeError:
            self.respond({'error': 'The service is not configured yet'}, 503)


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
