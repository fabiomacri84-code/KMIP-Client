#!/usr/bin/env python3
"""Avvio desktop per KMIP Test Client, senza Podman né server da avviare a mano."""
import argparse
import hmac
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import secrets
import sys
import tempfile
import threading
from urllib.request import HTTPCookieProcessor, build_opener
from http.cookiejar import CookieJar

from app_version import __version__

SETTINGS_FIELDS = ('host', 'port', 'ca', 'cert', 'key', 'username', 'kmip_version')


def create_application(data_dir=None):
    if data_dir:
        os.environ['KMIP_DATA_DIR'] = str(Path(data_dir).expanduser().resolve())
        os.environ['KMIP_CERTS_DIR'] = str(Path(data_dir).expanduser().resolve() / 'certs')
    from app_paths import data_directory, write_private_file
    root = data_directory()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.environ.setdefault('KMIP_CERTS_DIR', str(root / 'certs'))
    settings_path = root / 'settings.json'
    import webui
    try:
        settings = json.loads(settings_path.read_text(encoding='utf-8'))
        if not isinstance(settings, dict):
            raise ValueError('Configurazione non valida')
        for field in SETTINGS_FIELDS:
            env_name = 'KMIP_VERSION' if field == 'kmip_version' else 'KMIP_' + field.upper()
            if isinstance(settings.get(field), str) and env_name not in os.environ:
                webui.DEFAULTS[field] = settings[field]
    except (OSError, ValueError, TypeError):
        pass

    def save_settings(ctx):
        values = {field: str(ctx[field]) for field in SETTINGS_FIELDS}
        write_private_file(settings_path, json.dumps(values, ensure_ascii=False, indent=2).encode('utf-8'))
        webui.DEFAULTS.update(values)

    app = webui.app
    app.config['SAVE_SETTINGS'] = save_settings
    app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024
    token = secrets.token_urlsafe(32)
    from flask import abort, redirect, request, session

    @app.before_request
    def protect_local_app():
        # Il server ascolta solo su loopback. Il token iniziale resta nella
        # finestra dell'app, le richieste successive usano la sessione firmata.
        if request.remote_addr != '127.0.0.1':
            abort(403)
        provided = request.args.get('desktop_token', '')
        if provided and hmac.compare_digest(provided, token):
            session['desktop_authorized'] = True
            return redirect('/')
        if not session.get('desktop_authorized'):
            abort(403)
        if request.method == 'POST':
            origin = request.headers.get('Origin')
            if origin and origin != request.host_url.rstrip('/'):
                abort(403)

    handler = RotatingFileHandler(root / 'client.log', maxBytes=2_000_000,
                                  backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Avvio KMIP Client v%s', __version__)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    return app, token, root


def self_test():
    """Verifica il pacchetto senza display, senza CTM e senza toccare certificati reali."""
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    from werkzeug.serving import make_server
    with tempfile.TemporaryDirectory(prefix='kmip-app-test-') as directory:
        app, token, root = create_application(directory)
        assert not list((root / 'certs').iterdir()), 'Una nuova installazione deve partire senza certificati o chiavi'
        client = app.test_client()
        assert client.get('/').status_code == 403
        assert client.get('/?desktop_token=' + token).status_code == 302
        assert client.get('/').status_code == 200
        assert client.get('/readme').status_code == 200
        response = client.post('/', data={'op': 'generate_csr', 'csr_cn': 'desktop-self-test'})
        assert response.status_code == 200 and b'BEGIN CERTIFICATE REQUEST' in response.data
        csr_path = next((root / 'certs').glob('*.csr'))
        csr = x509.load_pem_x509_csr(csr_path.read_bytes())
        key = serialization.load_pem_private_key((root / 'certs' / 'client.key').read_bytes(), None)
        assert csr.is_signature_valid and csr.public_key().public_numbers() == key.public_key().public_numbers()
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            opener = build_opener(HTTPCookieProcessor(CookieJar()))
            with opener.open('http://127.0.0.1:%d/?desktop_token=%s' % (server.server_port, token)) as page:
                assert page.status == 200
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        for handler in list(app.logger.handlers):
            if isinstance(handler, RotatingFileHandler):
                app.logger.removeHandler(handler)
                handler.close()
        print(json.dumps({'esito': 'OK', 'versione': __version__, 'pagina': 'OK', 'guida': 'OK', 'CSR_e_chiave': 'OK',
                          'server_locale': 'OK', 'accesso_protetto': 'OK'}))
    return 0


def main():
    parser = argparse.ArgumentParser(description='KMIP Test Client — applicazione desktop')
    parser.add_argument('--version', action='version', version='KMIP Client ' + __version__)
    parser.add_argument('--data-dir', help='Cartella dei dati e dei certificati')
    parser.add_argument('--smoke-test', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--self-test', action='store_true', help='Verifica il pacchetto senza connettersi a CTM')
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    app, token, root = create_application(args.data_dir)
    from werkzeug.serving import make_server
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        if sys.platform.startswith('linux'):
            # Questa interfaccia non richiede accelerazione video; il rendering
            # software evita dipendenze dai driver della macchina di build.
            os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-gpu --disable-features=VaapiVideoDecoder')
            os.environ.setdefault('QT_QUICK_BACKEND', 'software')
            os.environ.setdefault('QT_OPENGL', 'software')
        import webview
        window = webview.create_window('KMIP Test Client — CipherTrust Manager — v' + __version__,
                              'http://127.0.0.1:%d/?desktop_token=%s' % (server.server_port, token),
                              width=1150, height=900, min_size=(760, 600), text_select=True)
        failures = []
        def verify_window():
            try:
                if not window.events.loaded.wait(timeout=45):
                    raise RuntimeError('La finestra non ha caricato la pagina')
                if not window.evaluate_js("Boolean(document.getElementById('kmip-form'))"):
                    raise RuntimeError('Pagina principale non caricata nella finestra')
                print('Finestra desktop e pagina KMIP: OK', flush=True)
            except Exception as exc:
                failures.append(exc)
            finally:
                window.destroy()
        webview.start(verify_window if args.smoke_test else None, gui='qt', private_mode=True,
                      icon=str(Path(__file__).resolve().parent / 'assets' / 'icon.png'))
        if failures:
            raise failures[0]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        import webui
        webui.PASSWORDS.clear()
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        if '--self-test' in sys.argv or '--smoke-test' in sys.argv:
            raise
        logging.exception('Avvio di KMIP Test Client fallito')
        # Anche un eseguibile Windows senza console deve mostrare l'errore.
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            qt_app = QApplication.instance() or QApplication([])
            QMessageBox.critical(None, 'KMIP Test Client',
                'Impossibile avviare l’app. Controlla client.log nella cartella dati.')
        except Exception:
            pass
        raise
