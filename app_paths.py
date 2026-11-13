"""Percorsi scrivibili dell'app, separati dall'eseguibile e dai file distribuiti."""
import os
from pathlib import Path
import sys


def data_directory():
    if os.environ.get('KMIP_DATA_DIR'):
        return Path(os.environ['KMIP_DATA_DIR']).expanduser().resolve()
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'KMIP Test Client'
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'KMIP Test Client'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'kmip-test-client'


def certificates_directory():
    if os.environ.get('KMIP_CERTS_DIR'):
        return Path(os.environ['KMIP_CERTS_DIR']).expanduser().resolve()
    if not getattr(sys, 'frozen', False) and Path('/certs').is_dir():
        return Path('/certs')
    return data_directory() / 'certs'


def write_private_file(path, content):
    """Crea un file privato senza dipendere da fchmod, assente su Windows."""
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        if os.name != 'nt':
            os.fchmod(stream.fileno(), 0o600)
        stream.write(content)
