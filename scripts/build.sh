#!/bin/bash
# build.sh - Build Docker image for DHT nodes

set -e

echo "Building DHT node Docker image..."
docker build -f docker/Dockerfile -t dht-node:latest .

echo "✓ Built dht-node:latest successfully"
echo ""
echo "Next steps:"
echo "  For Docker: ./scripts/deploy-docker.sh chord"
echo "  For K8s:    ./scripts/deploy-k8s.sh chord"
