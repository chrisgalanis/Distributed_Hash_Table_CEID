#!/bin/bash
# Build Docker image for DHT nodes

set -e

echo "Building DHT node Docker image..."
docker build -f docker/Dockerfile -t dht-node:latest .

echo ""
echo "✓ Built dht-node:latest"
echo ""
echo "Next steps:"
echo "  - Deploy with Docker: ./scripts/deploy-docker.sh"
echo "  - Deploy to K8s:     ./scripts/deploy-k8s.sh"
