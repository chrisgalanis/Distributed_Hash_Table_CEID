#!/bin/bash
# Start DHT nodes locally (separate processes)

PROTOCOL=${1:-chord}
NUM_NODES=${2:-5}

if [ "$PROTOCOL" = "chord" ]; then
    BASE_PORT=8000
elif [ "$PROTOCOL" = "pastry" ]; then
    BASE_PORT=9000
else
    echo "Unknown protocol: $PROTOCOL (use 'chord' or 'pastry')"
    exit 1
fi

echo "Starting $NUM_NODES $PROTOCOL nodes locally..."
echo "Press Ctrl+C to stop all nodes"
echo ""

# Array to store PIDs
PIDS=()

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping all nodes..."
    for pid in "${PIDS[@]}"; do
        kill $pid 2>/dev/null || true
    done
    exit 0
}

# Set trap for cleanup
trap cleanup INT TERM

# Start nodes
for i in $(seq 0 $((NUM_NODES - 1))); do
    NODE_ID=$((i * 50))
    PORT=$((BASE_PORT + i))

    echo "Starting node $NODE_ID on port $PORT..."
    python -m distributed.node_server \
        --node-id $NODE_ID \
        --protocol $PROTOCOL \
        --port $PORT \
        --m 16 > "node_${NODE_ID}.log" 2>&1 &

    PIDS+=($!)
    sleep 0.5
done

echo ""
echo "✓ All nodes started!"
echo ""
echo "Log files:"
for i in $(seq 0 $((NUM_NODES - 1))); do
    NODE_ID=$((i * 50))
    echo "  node_${NODE_ID}.log"
done
echo ""
echo "Check health:"
for i in $(seq 0 $((NUM_NODES - 1))); do
    PORT=$((BASE_PORT + i))
    echo "  curl http://localhost:$PORT/health"
done
echo ""
echo "Run experiment in another terminal:"
echo "  python distributed/orchestrator.py --protocol $PROTOCOL --deployment local --num-nodes $NUM_NODES --num-items 500"
echo ""

# Wait for all background jobs
wait
