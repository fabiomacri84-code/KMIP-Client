"""Impedisce una release con tag e versione applicativa discordanti."""
import os
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app_version import __version__

if not re.fullmatch(r'\d+\.\d+\.\d+', __version__):
    raise SystemExit('Versione non valida: ' + __version__)
if os.environ.get('GITHUB_REF_TYPE') == 'tag' and os.environ.get('GITHUB_REF_NAME') != 'v' + __version__:
    raise SystemExit('Il tag deve essere v' + __version__)
print('Versione applicativa: ' + __version__)
