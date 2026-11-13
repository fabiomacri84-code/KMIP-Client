"""Controlla che una release contenga esattamente le tre build richieste."""
import hashlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app_version import __version__

folder = Path(sys.argv[1])
archives = sorted([*folder.glob('*.zip'), *folder.glob('*.tar.gz')])
if len(archives) != 3:
    raise SystemExit('Servono le build Windows, Linux e macOS: trovati %d archivi' % len(archives))
for platform in ('Windows', 'Linux', 'macOS'):
    if sum(('-' + platform + '-') in archive.name for archive in archives) != 1:
        raise SystemExit('Build mancante o duplicata: ' + platform)
lines = []
for archive in archives:
    if not archive.name.startswith('KMIP-Client-v' + __version__ + '-'):
        raise SystemExit('Archivio con versione errata: ' + archive.name)
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    lines.append(digest + '  ' + archive.name)
(folder / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n', encoding='ascii')
print('Tre build verificate per la versione ' + __version__)
