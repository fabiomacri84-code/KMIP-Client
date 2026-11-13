#!/usr/bin/env bash
# Avvia la Web UI del client KMIP su http://127.0.0.1:8080.
#
# Usa --network=host: il container condivide la rete dell'host, quindi
# raggiunge la VM CTM in QEMU (NAT libvirt, bridge o port forwarding).
set -euo pipefail
cd "$(dirname "$0")"

IMAGE=localhost/kmip-test:latest

if ! podman image exists "$IMAGE"; then
    echo "Costruisco l'immagine $IMAGE ..."
    podman build -t "$IMAGE" .
fi

mkdir -p certs

exec podman run --rm -it \
    --network=host \
    -e KMIP_HOST="${KMIP_HOST:-}" \
    -e KMIP_PORT="${KMIP_PORT:-5696}" \
    -e KMIP_CA="${KMIP_CA:-/certs/ctm-ca.pem}" \
    -e KMIP_CERT="${KMIP_CERT:-/certs/client.crt}" \
    -e KMIP_KEY="${KMIP_KEY:-/certs/client.key}" \
    -e KMIP_USERNAME="${KMIP_USERNAME:-}" \
    -e KMIP_VERSION="${KMIP_VERSION:-1.4}" \
    -v "$PWD/certs:/certs:rw,Z" \
    --entrypoint python \
    "$IMAGE" /app/webui.py --host 127.0.0.1 --port "${WEBUI_PORT:-8080}"
