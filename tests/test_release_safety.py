from pathlib import Path
import importlib.util
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('kmip_build', Path(__file__).resolve().parents[1] / 'packaging' / 'build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class ReleaseSafetyTests(unittest.TestCase):
    def test_accepts_clean_package_with_public_ca_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'cacert.pem').write_text('public CA bundle')
            builder.check_release(directory)

    def test_rejects_local_identity_and_settings(self):
        for name in ('client.key', 'client.crt', 'ctm-ca.pem', 'settings.json', 'client.log', 'external.key', 'identity.p12'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                (Path(directory) / name).write_text('must not ship')
                with self.assertRaises(RuntimeError):
                    builder.check_release(directory)


if __name__ == '__main__':
    unittest.main()
