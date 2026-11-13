#!/usr/bin/env bash
# Genera una PKI di test (CA + certificato client) in ./certs.
#
# Serve solo se vuoi registrare su CipherTrust Manager un client con
# certificato emesso da una CA esterna. Se usi la procedura guidata di CTM
# ("New Certificate"), CTM genera già certificato e chiave: mettili in ./certs
# e ignora questo script.
#
# Per il percorso manuale nei sottodomini, segui la guida dell’app:
# scarica certificato e chiave da CTM senza generare una CSR qui.
#
# Uso: ./make-certs.sh [common-name] [directory]
set -euo pipefail
cd "$(dirname "$0")"

CN="${1:-kmipclient}"
OUT="${2:-certs}"
mkdir -p "$OUT"

if [ -e "$OUT/ca.key" ] || [ -e "$OUT/client.key" ]; then
    echo "ERRORE: $OUT contiene già una PKI. Sposta o cancella i file prima di rigenerarla." >&2
    exit 1
fi

openssl req -x509 -newkey rsa:3072 -nodes \
    -keyout "$OUT/ca.key" -out "$OUT/ca.crt" -days 3650 \
    -subj "/CN=KMIP Test CA"

openssl req -newkey rsa:3072 -nodes \
    -keyout "$OUT/client.key" -out "$OUT/client.csr" \
    -subj "/CN=$CN"

openssl x509 -req -in "$OUT/client.csr" \
    -CA "$OUT/ca.crt" -CAkey "$OUT/ca.key" -CAcreateserial \
    -out "$OUT/client.crt" -days 825 \
    -extfile <(printf "extendedKeyUsage=clientAuth\n")

rm -f "$OUT/client.csr"
chmod 600 "$OUT"/*.key

echo
echo "Generati in $OUT:"
echo "  ca.crt      CA (da caricare su CTM se richiesto)"
echo "  client.crt  certificato client (CN=$CN)"
echo "  client.key  chiave privata client"
echo
echo "Sul CTM crea prima un utente '$CN' e registra il client con questo"
echo "certificato (KMIP > Registered Clients > Add Client)."
