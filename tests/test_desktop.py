import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='kmip-desktop-tests-')
        from desktop import create_application
        cls.app, cls.token, cls.root = create_application(cls.directory.name)
        cls.app.config['TESTING'] = True

    @classmethod
    def tearDownClass(cls):
        from logging.handlers import RotatingFileHandler
        for handler in list(cls.app.logger.handlers):
            if isinstance(handler, RotatingFileHandler):
                cls.app.logger.removeHandler(handler)
                handler.close()
        cls.directory.cleanup()

    def setUp(self):
        import webui
        self.webui = webui
        for path in (self.root / 'certs').iterdir():
            path.unlink()
        webui.PASSWORDS.clear()
        self.client = self.app.test_client()
        self.client.get('/?desktop_token=' + self.token)

    def test_access_is_local_and_authorized(self):
        stranger = self.app.test_client()
        self.assertEqual(stranger.get('/').status_code, 403)
        self.assertEqual(self.client.get('/readme').status_code, 200)
        self.assertEqual(self.client.post('/', data={'op': 'reset_certs'},
                        headers={'Origin': 'https://external.invalid'}).status_code, 403)

    def test_csr_without_external_openssl(self):
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization
        response = self.client.post('/', data={'op': 'generate_csr', 'csr_cn': 'test-client'})
        self.assertIn(b'BEGIN CERTIFICATE REQUEST', response.data)
        csr = x509.load_pem_x509_csr(next((self.root / 'certs').glob('*.csr')).read_bytes())
        key = serialization.load_pem_private_key((self.root / 'certs' / 'client.key').read_bytes(), None)
        self.assertTrue(csr.is_signature_valid)
        self.assertEqual(csr.public_key().public_numbers(), key.public_key().public_numbers())
        self.assertIn(str(self.root / 'certs').encode(), response.data)

    def test_invalid_key_preserves_existing_key(self):
        key_path = self.root / 'certs' / 'client.key'
        key_path.write_bytes(b'original-placeholder')
        response = self.client.post('/', data={'op': 'upload_client_key',
                    'client_key_file': (io.BytesIO(b'invalid'), 'wrong.key')})
        self.assertIn(b'class="err"', response.data)
        self.assertEqual(key_path.read_bytes(), b'original-placeholder')

    def test_password_reused_without_html_cookie_or_settings_leak(self):
        fields = {'op': 'ping', 'host': 'ctm.invalid', 'port': '5696', 'username': 'test-user'}
        with patch('webui.kmip_lib.connect', return_value=MagicMock()) as connect:
            response = self.client.post('/', data={**fields, 'password': 'not-a-real-password'})
            self.assertNotIn(b'not-a-real-password', response.data)
            self.assertNotIn('not-a-real-password', (self.root / 'settings.json').read_text())
            with self.client.session_transaction() as session:
                self.assertNotIn('not-a-real-password', str(dict(session)))
            self.client.post('/', data=fields)
            self.assertEqual(connect.call_args.kwargs['password'], 'not-a-real-password')
            self.client.post('/', data={**fields, 'host': 'other.invalid'})
            self.assertIsNone(connect.call_args.kwargs['password'])
            self.client.post('/', data={**fields, 'op': 'forget_password'})
            self.client.post('/', data=fields)
            self.assertIsNone(connect.call_args.kwargs['password'])

    def test_reset_removes_only_app_certificates(self):
        directory = self.root / 'certs'
        (directory / 'test.cer').write_text('certificate')
        (directory / 'test.cert').write_text('certificate')
        (directory / 'keep.txt').write_text('keep')
        (self.root / 'outside.key').write_text('keep')
        self.client.post('/', data={'op': 'reset_certs'})
        self.assertFalse((directory / 'test.cer').exists())
        self.assertFalse((directory / 'test.cert').exists())
        self.assertTrue((directory / 'keep.txt').exists())
        self.assertTrue((self.root / 'outside.key').exists())


class DiagnosticTests(unittest.TestCase):
    def test_ctm_authentication_error_without_batch_count(self):
        from kmip.core import enums
        from kmip.core.utils import BytearrayStream
        from kmip.services.kmip_protocol import KMIPProtocol
        from kmip_lib import DiagnosticProtocol, KmipServerError

        def field(tag, kind, value):
            return tag.to_bytes(3, 'big') + bytes([kind]) + len(value).to_bytes(4, 'big') + value + b'\0' * (-len(value) % 8)

        batch = field(enums.Tags.RESULT_STATUS.value, 5, (1).to_bytes(4, 'big'))
        batch += field(enums.Tags.RESULT_REASON.value, 5, (3).to_bytes(4, 'big'))
        batch += field(enums.Tags.RESULT_MESSAGE.value, 7, b'Certificate user must match username in Authentication request')
        response = field(enums.Tags.RESPONSE_HEADER.value, 1, b'')
        response += field(enums.Tags.BATCH_ITEM.value, 1, batch)
        response = BytearrayStream(field(enums.Tags.RESPONSE_MESSAGE.value, 1, response))
        with patch.object(KMIPProtocol, 'read', return_value=response):
            with self.assertRaisesRegex(KmipServerError, 'AUTHENTICATION_NOT_SUCCESSFUL.*Certificate user'):
                DiagnosticProtocol(None).read()


if __name__ == '__main__':
    unittest.main()
