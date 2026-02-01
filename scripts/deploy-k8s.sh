#!/bin/bash
# Deploy DHT nodes to Kubernetes

set -e

PROTOCOL=${1:-chord}

echo "Deploying $PROTOCOL nodes to Kubernetes..."

# Create namespace
echo "Creating namespace..."
kubectl apply -f k8s/namespace.yaml

# Deploy based on protocol
if [ "$PROTOCOL" = "chord" ]; then
    echo "Deploying Chord StatefulSet..."
    kubectl apply -f k8s/chord-statefulset.yaml

    echo "Waiting for Chord pods to be ready..."
    kubectl wait --for=condition=ready pod -l app=dht-chord -n dht-system --timeout=300s || true

elif [ "$PROTOCOL" = "pastry" ]; then
    echo "Deploying Pastry StatefulSet..."
    kubectl apply -f k8s/pastry-statefulset.yaml

    echo "Waiting for Pastry pods to be ready..."
    kubectl wait --for=condition=ready pod -l app=dht-pastry -n dht-system --timeout=300s || true
else
    echo "Unknown protocol: $PROTOCOL (use 'chord' or 'pastry')"
    exit 1
fi

echo ""
echo "✓ $PROTOCOL nodes deployed to Kubernetes!"
echo ""
echo "Check status:"
echo "  kubectl get pods -n dht-system"
echo ""
echo "View logs:"
echo "  kubectl logs -n dht-system ${PROTOCOL}-node-0"
echo ""
echo "Access node:"
echo "  kubectl port-forward -n dht-system ${PROTOCOL}-node-0 8000:8000"
echo "  Then: curl http://localhost:8000/health"
echo ""
echo "Run experiment:"
echo "  python distributed/orchestrator.py --protocol $PROTOCOL --deployment k8s --num-nodes 5 --num-items 500"
echo ""
echo "Cleanup:"
echo "  kubectl delete -f k8s/${PROTOCOL}-statefulset.yaml"
