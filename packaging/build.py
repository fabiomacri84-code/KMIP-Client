#!/usr/bin/env python3
"""Build nativa: eseguire con Python 3.12 sul sistema di destinazione."""
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def check_release(directory):
    """Blocca la distribuzione di dati locali o identità del laboratorio."""
    forbidden_names = {'client.key', 'client.crt', 'ctm-ca.pem', 'settings.json', 'client.log'}
    private_suffixes = {'.key', '.csr', '.p12', '.pfx'}
    for path in Path(directory).rglob('*'):
        if path.is_file() and (path.name.lower() in forbidden_names or path.suffix.lower() in private_suffixes):
            raise RuntimeError('Pacchetto non distribuibile: contiene dati locali: ' + str(path))


def main():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    from app_version import __version__
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    str(root / 'packaging' / 'kmip-client.spec')], cwd=root, check=True)
    binary = root / 'dist' / 'KMIP-Test-Client' / ('kmip-test-client.exe' if sys.platform == 'win32' else 'kmip-test-client')
    subprocess.run([str(binary), '--self-test'], check=True)
    shutil.copy2(root / 'APP-DESKTOP.md', binary.parent / 'LEGGIMI.md')
    (binary.parent / 'VERSION.txt').write_text(__version__ + '\n', encoding='ascii')
    check_release(binary.parent)
    platform_name = {'Darwin': 'macOS'}.get(platform.system(), platform.system())
    archive_name = root / 'dist' / ('KMIP-Client-v' + __version__ + '-' + platform_name + '-' + platform.machine())
    if sys.platform == 'darwin':
        check_release(root / 'dist' / 'KMIP Test Client.app')
        subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent',
                        str(root / 'dist' / 'KMIP Test Client.app'), str(archive_name) + '.zip'], check=True)
    else:
        shutil.make_archive(str(archive_name), 'zip' if sys.platform == 'win32' else 'gztar',
                            root_dir=root / 'dist', base_dir='KMIP-Test-Client')
    print('Pacchetto creato:', archive_name)


if __name__ == '__main__':
    main()
