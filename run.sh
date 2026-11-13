#!/usr/bin/env bash
# Esegue il client KMIP in un container Podman.
#
# I certificati devono stare in ./certs e sono montati in /certs (sola lettura).
# La rete è "host" così il container raggiunge il CTM anche se la VM usa NAT
# o un port forwarding sul localhost dell'host.
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
    -v "$PWD/certs:/certs:ro,Z" \
    "$IMAGE" "$@"
