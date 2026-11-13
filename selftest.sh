#!/usr/bin/env bash
# Test offline: avvia un server KMIP PyKMIP locale e verifica il client.
# Serve solo a dimostrare che container, TLS e operazioni KMIP funzionano,
# senza CipherTrust Manager.
set -euo pipefail
cd "$(dirname "$0")"

IMAGE=localhost/kmip-test:latest
DIR=selftest-certs
PORT=5697
NAME=kmip-selftest

if ! podman image exists "$IMAGE"; then
    podman build -t "$IMAGE" .
fi

rm -rf "$DIR"
mkdir -p "$DIR"

openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$DIR/ca.key" -out "$DIR/ca.crt" -days 30 \
    -subj "/CN=KMIP Selftest CA" 2>/dev/null
openssl req -newkey rsa:2048 -nodes \
    -keyout "$DIR/server.key" -out "$DIR/server.csr" \
    -subj "/CN=localhost" 2>/dev/null
printf "subjectAltName=DNS:localhost,IP:127.0.0.1\nextendedKeyUsage=serverAuth\n" \
    > "$DIR/server.ext"
openssl x509 -req -in "$DIR/server.csr" -CA "$DIR/ca.crt" \
    -CAkey "$DIR/ca.key" -CAcreateserial -out "$DIR/server.crt" \
    -days 30 -extfile "$DIR/server.ext" 2>/dev/null
openssl req -newkey rsa:2048 -nodes \
    -keyout "$DIR/client.key" -out "$DIR/client.csr" \
    -subj "/CN=kmipclient" 2>/dev/null
printf "extendedKeyUsage=clientAuth\n" > "$DIR/client.ext"
openssl x509 -req -in "$DIR/client.csr" -CA "$DIR/ca.crt" \
    -CAkey "$DIR/ca.key" -CAcreateserial -out "$DIR/client.crt" \
    -days 30 -extfile "$DIR/client.ext" 2>/dev/null

cat > "$DIR/server.conf" <<EOF
[server]
hostname=127.0.0.1
port=$PORT
certificate_path=/certs/server.crt
key_path=/certs/server.key
ca_path=/certs/ca.crt
auth_suite=TLS1.2
database_path=/tmp/kmip-selftest.db
enable_tls_client_auth=True
EOF

podman rm -f "$NAME" >/dev/null 2>&1 || true
podman run -d --rm --name "$NAME" --network=host \
    -v "$PWD/$DIR:/certs:ro,Z" --entrypoint pykmip-server \
    "$IMAGE" -f /certs/server.conf -l /tmp/kmip-selftest.log >/dev/null

trap 'podman rm -f "$NAME" >/dev/null 2>&1 || true' EXIT

sleep 2

podman run --rm --network=host -v "$PWD/$DIR:/certs:ro,Z" "$IMAGE" \
    --host 127.0.0.1 --port "$PORT" \
    --ca /certs/ca.crt --cert /certs/client.crt --key /certs/client.key \
    demo --destroy
