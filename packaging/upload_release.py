"""Upload diretto sulla release, senza consumare spazio degli artefatti Actions."""
import os
from pathlib import Path
import subprocess

archives = [*Path('dist').glob('KMIP-Client-v*.zip'), *Path('dist').glob('KMIP-Client-v*.tar.gz')]
if len(archives) != 1:
    raise SystemExit('Atteso un solo pacchetto nativo, trovati: %d' % len(archives))
subprocess.run(['gh', 'release', 'upload', os.environ['GITHUB_REF_NAME'],
                '--repo', os.environ['GITHUB_REPOSITORY'], str(archives[0]), '--clobber'], check=True)
