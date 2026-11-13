#!/usr/bin/env bash
# Alternativa senza container: crea un virtualenv locale con PyKMIP.
# Il metodo consigliato resta ./run.sh (Podman), che non tocca l'host.
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo
echo "Fatto. Esempio d'uso:"
echo "  .venv/bin/python kmip_test.py --help"
