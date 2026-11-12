"""Serverless session regression tests; no database writes."""
import base64
import importlib
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.session = dict(username='douyin_demo_u1', profile={'user_id': 1, 'nickname': 'Demo_Ada'},
                            csrf='test-csrf', expires=time.time() + 600)

    def test_valid_identity_is_restored(self):
        restored = app.open_session(app.seal_session(self.session))
        self.assertEqual(restored['profile']['user_id'], 1)
        self.assertEqual(restored['csrf'], 'test-csrf')

    def test_cookie_has_no_password(self):
        token = app.seal_session(self.session)
        data = token.split('.')[0]
        decoded = base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))
        self.assertNotIn(b'"password"', decoded)
        for user in app.CONFIG['users'].values():
            self.assertNotIn(user['password'].encode(), decoded)

    def test_signed_body_tampering_is_rejected(self):
        token = app.seal_session(self.session)
        self.assertIsNone(app.open_session(('A' if token[0] != 'A' else 'B') + token[1:]))

    def test_signature_tampering_is_rejected(self):
        token = app.seal_session(self.session)
        body, signature = token.split('.')
        signature = ('A' if signature[0] != 'A' else 'B') + signature[1:]
        self.assertIsNone(app.open_session(body + '.' + signature))

    def test_expired_session_is_rejected(self):
        self.session['expires'] = time.time() - 1
        self.assertIsNone(app.open_session(app.seal_session(self.session)))

    def test_malformed_cookie_is_rejected(self):
        for token in ['', 'x', 'x.y.z', 'x.y', 'a' * 5000]:
            self.assertIsNone(app.open_session(token))

    def test_password_rotation_invalidates_cookie(self):
        token = app.seal_session(self.session)
        with patch.dict(app.CONFIG['users']['1'], password='changed-for-test-only'):
            self.assertIsNone(app.open_session(token))

    def test_another_function_instance_accepts_same_cookie(self):
        token = app.seal_session(self.session)
        # Reload erases module state; the stable local/env signing key survives.
        reloaded = importlib.reload(app)
        self.assertEqual(reloaded.open_session(token)['profile']['user_id'], 1)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SessionTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'tests': result.testsRun, 'passed': result.wasSuccessful()}))
    sys.exit(not result.wasSuccessful())
