#!/usr/bin/env bash
# Genera chiave privata + CSR per il client KMIP.
#
# È il equivalente di ciò che fa vCenter nella guida vSphere: il CSR viene
# poi firmato dalla CA locale di CipherTrust Manager e il certificato firmato
# viene scaricato in ./certs/client.crt.
#
# Per il percorso manuale nei sottodomini, segui la guida dell’app:
# scarica certificato e chiave da CTM senza generare una CSR qui.
#
# Uso: ./make-csr.sh [common-name] [directory]
set -euo pipefail
cd "$(dirname "$0")"

CN="${1:-kmipclient}"
OUT="${2:-certs}"
mkdir -p "$OUT"

if [ -e "$OUT/client.key" ] || [ -e "$OUT/client.csr" ]; then
    echo "ERRORE: $OUT contiene già client.key/client.csr. Spostali o cancellali." >&2
    exit 1
fi

openssl req -newkey rsa:3072 -nodes \
    -keyout "$OUT/client.key" -out "$OUT/client.csr" \
    -subj "/CN=$CN"

chmod 600 "$OUT/client.key"

echo
echo "Generati:"
echo "  $OUT/client.key  chiave privata (non caricarla su CTM)"
echo "  $OUT/client.csr  richiesta da firmare"
echo
echo "Passi successivi su CipherTrust Manager:"
echo "  1. Seleziona il dominio root per questo percorso con CSR"
echo "  2. CA > Local > (la tua CA) > Upload CSR"
echo "  3. Incolla il contenuto di $OUT/client.csr e rilascia il certificato"
echo "  4. Scarica il certificato come $OUT/client.crt"
echo "  5. Crea l'utente '$CN' (Access Management > Users) e aggiungilo"
echo "     al gruppo Key Users"
echo
echo "Se l'interfaccia KMIP richiede anche la password, userai:"
echo "  --username '$CN' --password '...'"
