#!/bin/bash
set -e

CDPATH= cd "$(dirname "$0")/../.."

echo "🐳 Launching Ubuntu 22.04 LTS build container..."
chmod +x packaging/linux/docker_entrypoint.sh

docker run --rm \
    -v "$(pwd)":/workspace \
    -w /workspace \
    -e HOST_UID="$(id -u)" \
    -e HOST_GID="$(id -g)" \
    ubuntu:22.04 \
    bash packaging/linux/docker_entrypoint.sh
