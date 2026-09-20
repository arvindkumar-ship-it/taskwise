#!/bin/bash
# Minimal example deploy: build, push to a registry, pull + restart on a remote host.
# Edit REGISTRY and HOST for your setup, or use this as a reference for your
# platform's (Render/Railway/Fly) own build-from-Dockerfile flow instead.
set -euo pipefail

REGISTRY="your-registry.example.com/taskwise-agent"
HOST="user@your-server.example.com"

echo "Building image..."
docker build -t "$REGISTRY:latest" .

echo "Pushing image..."
docker push "$REGISTRY:latest"

echo "Deploying on $HOST..."
ssh "$HOST" "docker pull $REGISTRY:latest && docker compose up -d --force-recreate"

echo "Done."
