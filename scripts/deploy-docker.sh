#!/bin/bash
# Deploy DHT nodes using Docker Compose

set -e

# Detect docker-compose command (old vs new)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "Error: Neither 'docker-compose' nor 'docker compose' is available"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

PROTOCOL=${1:-chord}
NUM_NODES=${2:-5}

echo "Deploying $NUM_NODES $PROTOCOL nodes with Docker Compose..."
echo "Using: $DOCKER_COMPOSE"

if [ "$PROTOCOL" = "chord" ]; then
    $DOCKER_COMPOSE -f docker/docker-compose.yml up -d \
        chord-node-0 chord-node-1 chord-node-2 chord-node-3 chord-node-4
    BASE_PORT=8000
elif [ "$PROTOCOL" = "pastry" ]; then
    $DOCKER_COMPOSE -f docker/docker-compose.yml up -d \
        pastry-node-0 pastry-node-1 pastry-node-2 pastry-node-3 pastry-node-4
    BASE_PORT=9000
else
    echo "Unknown protocol: $PROTOCOL (use 'chord' or 'pastry')"
    exit 1
fi

echo "Waiting for nodes to start..."
sleep 5

echo ""
echo "Checking node health..."
for i in {0..4}; do
    PORT=$((BASE_PORT + i))
    STATUS=$(curl -s http://localhost:$PORT/health | grep -o '"status":"ok"' || echo "FAILED")
    if [ "$STATUS" = '"status":"ok"' ]; then
        echo "  ✓ Node $i at localhost:$PORT - OK"
    else
        echo "  ✗ Node $i at localhost:$PORT - FAILED"
    fi
done

echo ""
echo "✓ $PROTOCOL nodes deployed!"
echo ""
echo "Run experiment:"
echo "  python distributed/orchestrator.py --protocol $PROTOCOL --deployment docker --num-nodes $NUM_NODES --num-items 500"
echo ""
echo "View logs:"
echo "  $DOCKER_COMPOSE -f docker/docker-compose.yml logs -f"
echo ""
echo "Stop nodes:"
echo "  $DOCKER_COMPOSE -f docker/docker-compose.yml down"
