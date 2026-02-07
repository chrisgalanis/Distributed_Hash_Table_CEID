#!/bin/bash
# compare.sh - Compare Chord vs Pastry DHT implementations

# Show help
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    cat << EOF
DHT Comparison Tool - Compare Chord vs Pastry protocols

USAGE:
  ./compare.sh simulated [NUM_ITEMS]
  ./compare.sh docker [NUM_NODES] [NUM_ITEMS]
  ./compare.sh k8s [NUM_NODES] [NUM_ITEMS]

MODES:
  simulated    Fast in-process simulation (default)
               Tests with 50, 100, 200, 500 nodes automatically
  docker       Docker containers with real network
  k8s          Kubernetes deployment

ARGUMENTS:
  For simulated mode:
    NUM_ITEMS    Number of items to store (default: 1000)

  For docker/k8s modes:
    NUM_NODES    Number of nodes to deploy (default: 5)
    NUM_ITEMS    Number of items to store (default: 1000)

EXAMPLES:
  ./compare.sh simulated 10000         # Simulated with 10k items
  ./compare.sh docker 5 500            # Docker with 5 nodes, 500 items
  ./compare.sh k8s 10 5000             # K8s with 10 nodes, 5k items

RESULTS:
  - comparison_results/results.csv     # Performance metrics
  - results/*.png                      # Comparison plots

DATASET:
  If data/movies_dataset.csv exists, it will be used automatically.
  Otherwise, synthetic data is generated.

EOF
    exit 0
fi

set -e

MODE=${1:-simulated}

# Arguments depend on mode
if [[ "$MODE" == "simulated" ]]; then
    # Simulated: arg2 is num_items (nodes are fixed at 50,100,200,500)
    NUM_ITEMS=${2:-1000}
    NUM_NODES=""  # Not used
else
    # Docker/K8s: arg2 is num_nodes, arg3 is num_items
    NUM_NODES=${2:-5}
    NUM_ITEMS=${3:-1000}
fi

# Validate node count
if [[ "$MODE" != "simulated" ]] && [[ $NUM_NODES -gt 20 ]]; then
    echo "Warning: $NUM_NODES nodes is a lot for distributed mode."
    echo "Recommended: 5-10 nodes for testing"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

RESULTS_DIR="comparison_results"
mkdir -p "$RESULTS_DIR"

# Set PYTHONPATH to project root
export PYTHONPATH="$(pwd):$PYTHONPATH"

echo "======================================"
echo "  DHT Comparison: Chord vs Pastry"
echo "======================================"
echo "Mode: $MODE"
if [[ "$MODE" == "simulated" ]]; then
    echo "Nodes: 50, 100, 200, 500 (fixed test matrix)"
    echo "Items: $NUM_ITEMS"
else
    echo "Nodes: $NUM_NODES"
    echo "Items: $NUM_ITEMS"
fi
echo "Results: $RESULTS_DIR"
echo ""

case $MODE in
    simulated)
        echo "Running simulated comparison..."

        # Check if real dataset exists
        REAL_DATA_ARGS=""
        if [[ -f "data/movies_dataset.csv" ]]; then
            echo "Found real dataset: data/movies_dataset.csv"
            REAL_DATA_ARGS="--use-real-data --data-file data/movies_dataset.csv"
        else
            echo "Using synthetic dataset"
        fi

        python main.py --experiment scalability \
            --nodes 50 100 200 500 \
            --items $NUM_ITEMS \
            --operations 500 \
            --output "$RESULTS_DIR/results.csv" \
            $REAL_DATA_ARGS

        echo ""
        echo "✓ Results saved to $RESULTS_DIR/results.csv"
        echo "✓ Plots saved to results/"
        ;;

    docker)
        echo "Building Docker image..."
        ./scripts/build.sh

        # Test with multiple node counts for proper plots
        if [ $NUM_NODES -le 10 ]; then
            NODE_COUNTS="3 5 $NUM_NODES"
        else
            NODE_COUNTS="5 10 $NUM_NODES"
        fi

        # Remove duplicates and sort
        NODE_COUNTS=$(echo $NODE_COUNTS | tr ' ' '\n' | sort -nu | tr '\n' ' ')

        echo ""
        echo "Testing Chord with node counts: $NODE_COUNTS"

        # Clear previous results
        > "$RESULTS_DIR/chord_results.csv"
        echo "protocol,operation,num_nodes,num_items,avg_hops,max_hops,min_hops,total_ops" > "$RESULTS_DIR/chord_results.csv"

        for nodes in $NODE_COUNTS; do
            echo "  Testing with $nodes nodes..."
            ./scripts/deploy-docker.sh chord $nodes > /dev/null 2>&1
            sleep 2

            python distributed/orchestrator.py \
                --protocol chord \
                --deployment docker \
                --num-nodes $nodes \
                --num-items $NUM_ITEMS \
                --num-operations 200 \
                --output "$RESULTS_DIR/chord_temp.csv" 2>&1 | grep -E "Progress:|RESULTS|avg=" | tee -a "$RESULTS_DIR/chord.txt"

            # Append results (skip header)
            tail -n +2 "$RESULTS_DIR/chord_temp.csv" >> "$RESULTS_DIR/chord_results.csv" 2>/dev/null

            docker ps --filter 'name=chord-node-' -q | xargs -r docker rm -f > /dev/null 2>&1
            sleep 1
        done

        echo ""
        echo "Testing Pastry with node counts: $NODE_COUNTS"

        # Clear previous results
        > "$RESULTS_DIR/pastry_results.csv"
        echo "protocol,operation,num_nodes,num_items,avg_hops,max_hops,min_hops,total_ops" > "$RESULTS_DIR/pastry_results.csv"

        for nodes in $NODE_COUNTS; do
            echo "  Testing with $nodes nodes..."
            ./scripts/deploy-docker.sh pastry $nodes > /dev/null 2>&1
            sleep 2

            python distributed/orchestrator.py \
                --protocol pastry \
                --deployment docker \
                --num-nodes $nodes \
                --num-items $NUM_ITEMS \
                --num-operations 200 \
                --output "$RESULTS_DIR/pastry_temp.csv" 2>&1 | grep -E "Progress:|RESULTS|avg=" | tee -a "$RESULTS_DIR/pastry.txt"

            # Append results (skip header)
            tail -n +2 "$RESULTS_DIR/pastry_temp.csv" >> "$RESULTS_DIR/pastry_results.csv" 2>/dev/null

            docker ps --filter 'name=pastry-node-' -q | xargs -r docker rm -f > /dev/null 2>&1
            sleep 1
        done

        # Merge results and generate plots
        echo ""
        echo "Generating comparison plots..."
        cat "$RESULTS_DIR/chord_results.csv" "$RESULTS_DIR/pastry_results.csv" | \
            awk 'NR==1 || !/^protocol/' > "$RESULTS_DIR/results.csv"

        python -c "
import sys
sys.path.insert(0, '.')
from experiments.plots import generate_all_plots
generate_all_plots('$RESULTS_DIR/results.csv', 'results')
print('✓ Plots saved to results/')
"

        # Cleanup temp files
        rm -f "$RESULTS_DIR/chord_temp.csv" "$RESULTS_DIR/pastry_temp.csv"

        echo ""
        echo "✓ Results saved to $RESULTS_DIR/results.csv"
        echo "✓ Plots saved to results/"
        ;;

    k8s)
        echo "Building Docker image..."
        ./scripts/build.sh

        # Load image into cluster
        if kubectl config current-context | grep -q kind; then
            echo "Loading image into kind cluster..."
            kind load docker-image dht-node:latest --name dht-cluster
        fi

        # Test with multiple node counts for proper plots
        if [ $NUM_NODES -le 10 ]; then
            NODE_COUNTS="3 5 $NUM_NODES"
        else
            NODE_COUNTS="5 10 $NUM_NODES"
        fi

        # Remove duplicates and sort
        NODE_COUNTS=$(echo $NODE_COUNTS | tr ' ' '\n' | sort -nu | tr '\n' ' ')

        echo ""
        echo "Testing Chord with node counts: $NODE_COUNTS"

        # Clear previous results
        > "$RESULTS_DIR/chord_results.csv"
        echo "protocol,operation,num_nodes,num_items,avg_hops,max_hops,min_hops,total_ops" > "$RESULTS_DIR/chord_results.csv"

        for nodes in $NODE_COUNTS; do
            echo "  Testing with $nodes nodes..."
            ./scripts/deploy-k8s.sh chord $nodes > /dev/null 2>&1
            sleep 3

            # Set up port forwarding
            ./scripts/k8s-portforward.sh chord $nodes start > /dev/null 2>&1
            sleep 2

            python distributed/orchestrator.py \
                --protocol chord \
                --deployment k8s \
                --num-nodes $nodes \
                --num-items $NUM_ITEMS \
                --num-operations 200 \
                --output "$RESULTS_DIR/chord_temp.csv" 2>&1 | grep -E "Progress:|RESULTS|avg=" | tee -a "$RESULTS_DIR/chord.txt"

            # Append results (skip header)
            tail -n +2 "$RESULTS_DIR/chord_temp.csv" >> "$RESULTS_DIR/chord_results.csv" 2>/dev/null

            # Stop port forwarding
            ./scripts/k8s-portforward.sh chord $nodes stop > /dev/null 2>&1

            kubectl delete -f k8s/chord-statefulset.yaml > /dev/null 2>&1
            sleep 2
        done

        echo ""
        echo "Testing Pastry with node counts: $NODE_COUNTS"

        # Clear previous results
        > "$RESULTS_DIR/pastry_results.csv"
        echo "protocol,operation,num_nodes,num_items,avg_hops,max_hops,min_hops,total_ops" > "$RESULTS_DIR/pastry_results.csv"

        for nodes in $NODE_COUNTS; do
            echo "  Testing with $nodes nodes..."
            ./scripts/deploy-k8s.sh pastry $nodes > /dev/null 2>&1
            sleep 3

            # Set up port forwarding
            ./scripts/k8s-portforward.sh pastry $nodes start > /dev/null 2>&1
            sleep 2

            python distributed/orchestrator.py \
                --protocol pastry \
                --deployment k8s \
                --num-nodes $nodes \
                --num-items $NUM_ITEMS \
                --num-operations 200 \
                --output "$RESULTS_DIR/pastry_temp.csv" 2>&1 | grep -E "Progress:|RESULTS|avg=" | tee -a "$RESULTS_DIR/pastry.txt"

            # Append results (skip header)
            tail -n +2 "$RESULTS_DIR/pastry_temp.csv" >> "$RESULTS_DIR/pastry_results.csv" 2>/dev/null

            # Stop port forwarding
            ./scripts/k8s-portforward.sh pastry $nodes stop > /dev/null 2>&1

            kubectl delete -f k8s/pastry-statefulset.yaml > /dev/null 2>&1
            sleep 2
        done

        # Merge results and generate plots
        echo ""
        echo "Generating comparison plots..."
        cat "$RESULTS_DIR/chord_results.csv" "$RESULTS_DIR/pastry_results.csv" | \
            awk 'NR==1 || !/^protocol/' > "$RESULTS_DIR/results.csv"

        python -c "
import sys
sys.path.insert(0, '.')
from experiments.plots import generate_all_plots
generate_all_plots('$RESULTS_DIR/results.csv', 'results')
print('✓ Plots saved to results/')
"

        # Cleanup temp files
        rm -f "$RESULTS_DIR/chord_temp.csv" "$RESULTS_DIR/pastry_temp.csv"

        echo ""
        echo "✓ Results saved to $RESULTS_DIR/results.csv"
        echo "✓ Plots saved to results/"
        ;;

    *)
        echo "Invalid mode. Use: simulated, docker, or k8s"
        exit 1
        ;;
esac

echo ""
echo "======================================"
echo "  Comparison Complete"
echo "======================================"
echo "Check $RESULTS_DIR/ for results and plots"
echo ""
echo "Usage:"
echo "  ./compare.sh simulated [num_items]"
echo "  ./compare.sh docker [num_nodes] [num_items]"
echo "  ./compare.sh k8s [num_nodes] [num_items]"
