"""Crea una release provvisoria; non sostituisce release già pubblicate."""
import json
import os
import subprocess

repo = os.environ['GITHUB_REPOSITORY']
tag = os.environ['GITHUB_REF_NAME']
query = subprocess.run(['gh', 'release', 'view', tag, '--repo', repo, '--json', 'isDraft'], capture_output=True, text=True)
if query.returncode == 0:
    if not json.loads(query.stdout)['isDraft']:
        raise SystemExit('Versione già pubblicata: incrementare app_version.py e creare un nuovo tag.')
else:
    subprocess.run(['gh', 'release', 'create', tag, '--repo', repo, '--verify-tag', '--draft',
                    '--title', 'KMIP Client ' + tag, '--notes-file', 'RELEASE-NOTES.md'], check=True)
