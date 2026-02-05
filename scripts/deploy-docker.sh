#!/bin/bash
# deploy-docker.sh - Deploy DHT nodes with Docker

set -e

PROTOCOL=${1:-chord}
NUM_NODES=${2:-5}

if [[ "$PROTOCOL" != "chord" && "$PROTOCOL" != "pastry" ]]; then
    echo "Usage: $0 <chord|pastry> [num_nodes]"
    echo "Example: $0 chord 5"
    exit 1
fi

echo "Deploying $NUM_NODES $PROTOCOL nodes with Docker..."
echo ""

# Set base port
if [[ "$PROTOCOL" == "chord" ]]; then
    BASE_PORT=8000
else
    BASE_PORT=9000
fi

# Create network if it doesn't exist
if ! docker network inspect dht-network > /dev/null 2>&1; then
    echo "Creating Docker network 'dht-network'..."
    docker network create dht-network
fi

# Stop and remove existing containers with the same protocol prefix
echo "Cleaning up existing containers..."
docker ps -a --filter "name=${PROTOCOL}-node-" -q | xargs -r docker rm -f > /dev/null 2>&1 || true

# Start nodes
echo "Starting $NUM_NODES nodes..."
for i in $(seq 0 $((NUM_NODES - 1))); do
    NODE_ID=$((i * 50))
    PORT=$((BASE_PORT + i))
    CONTAINER_NAME="${PROTOCOL}-node-$i"

    docker run -d \
        --name "$CONTAINER_NAME" \
        --network dht-network \
        --hostname "$CONTAINER_NAME" \
        -p "${PORT}:8000" \
        dht-node:latest \
        --node-id "$NODE_ID" \
        --protocol "$PROTOCOL" \
        --port 8000 \
        > /dev/null

    echo "  Started ${CONTAINER_NAME} (node_id=${NODE_ID}, port=${PORT})"
done

# Wait for nodes to be ready
echo ""
echo "Waiting for nodes to start..."
sleep 8

# Check health of each node with retries
echo ""
echo "Checking node health..."
SUCCESS=0
FAILED=0

for i in $(seq 0 $((NUM_NODES - 1))); do
    PORT=$((BASE_PORT + i))

    # Try up to 3 times with 2 second timeout each
    RETRY=0
    MAX_RETRIES=3
    HEALTHY=false

    while [ $RETRY -lt $MAX_RETRIES ]; do
        if curl -s --max-time 2 http://localhost:$PORT/health > /dev/null 2>&1; then
            HEALTHY=true
            break
        fi
        RETRY=$((RETRY + 1))
        if [ $RETRY -lt $MAX_RETRIES ]; then
            sleep 1
        fi
    done

    if [ "$HEALTHY" = "true" ]; then
        echo "✓ Node $i (port $PORT) - OK"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "✗ Node $i (port $PORT) - FAILED"
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo "Summary: $SUCCESS/$NUM_NODES nodes ready"

if [[ $FAILED -gt 0 ]]; then
    echo ""
    echo "Some nodes failed to start. Check logs with:"
    echo "  docker logs ${PROTOCOL}-node-0"
    exit 1
fi

echo ""
echo "✓ $PROTOCOL nodes ready!"
echo ""
echo "Next steps:"
echo "  1. Run experiment:"
echo "     python distributed/orchestrator.py --protocol $PROTOCOL --deployment docker --num-nodes $NUM_NODES --num-items 500"
echo ""
echo "  2. View logs:"
echo "     docker logs -f ${PROTOCOL}-node-0"
echo ""
echo "  3. Stop nodes:"
echo "     docker ps --filter 'name=${PROTOCOL}-node-' -q | xargs docker rm -f"
