#!/bin/bash
# deploy-k8s.sh - Deploy DHT nodes to Kubernetes

set -e

PROTOCOL=${1:-chord}
REPLICAS=${2:-5}

if [[ "$PROTOCOL" != "chord" && "$PROTOCOL" != "pastry" ]]; then
    echo "Usage: $0 <chord|pastry> [replicas]"
    echo "Example: $0 chord 5"
    exit 1
fi

echo "Deploying $PROTOCOL to Kubernetes with $REPLICAS replicas..."
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    echo "Please install kubectl: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    echo "Error: Cannot connect to Kubernetes cluster"
    echo ""
    echo "To set up Kubernetes, run:"
    echo "  ./scripts/setup-k8s.sh"
    echo ""
    echo "Or manually:"
    echo "  kind create cluster --name dht-cluster  (recommended)"
    echo "  minikube start                          (alternative)"
    exit 1
fi

# Check if image exists in cluster
echo "Checking if dht-node:latest image is available..."
CURRENT_CONTEXT=$(kubectl config current-context)

if [[ "$CURRENT_CONTEXT" == *"kind"* ]]; then
    # Using kind - need to load image
    echo "Detected kind cluster. Checking if image is loaded..."
    if ! docker exec kind-control-plane crictl images | grep -q "dht-node"; then
        echo ""
        echo "⚠️  Image not found in kind cluster. Loading it now..."
        kind load docker-image dht-node:latest --name dht-cluster || {
            echo ""
            echo "Failed to load image. Make sure you've built it first:"
            echo "  ./scripts/build.sh"
            echo "  kind load docker-image dht-node:latest --name dht-cluster"
            exit 1
        }
        echo "✓ Image loaded into kind cluster"
    fi
elif [[ "$CURRENT_CONTEXT" == *"minikube"* ]]; then
    # Using minikube - remind to build in minikube env
    echo "Detected minikube cluster."
    echo "Make sure you built the image in minikube's Docker environment:"
    echo "  eval \$(minikube docker-env)"
    echo "  ./scripts/build.sh"
    echo ""
fi

# Create namespace if it doesn't exist
echo "Creating namespace..."
kubectl apply -f k8s/namespace.yaml

# Deploy the StatefulSet
echo "Deploying $PROTOCOL StatefulSet..."
kubectl apply -f k8s/${PROTOCOL}-statefulset.yaml

# Scale to desired replicas if different from default
echo "Scaling to $REPLICAS replicas..."
kubectl scale statefulset ${PROTOCOL}-node -n dht-system --replicas=$REPLICAS

# Wait for pods to be ready
echo ""
echo "Waiting for pods to be ready (this may take a few minutes)..."
kubectl wait --for=condition=ready pod -l app=dht-${PROTOCOL} -n dht-system --timeout=300s

# Get pod status
echo ""
echo "Pod Status:"
kubectl get pods -n dht-system -l app=dht-${PROTOCOL}

# Show service info
echo ""
echo "Service Info:"
kubectl get svc -n dht-system -l app=dht-${PROTOCOL}

echo ""
echo "✓ $PROTOCOL nodes deployed successfully!"
echo ""
echo "Next steps:"
echo "  1. Check pod status:"
echo "     kubectl get pods -n dht-system"
echo ""
echo "  2. View logs:"
echo "     kubectl logs -n dht-system ${PROTOCOL}-node-0 -f"
echo ""
echo "  3. Access a node:"
echo "     kubectl port-forward -n dht-system ${PROTOCOL}-node-0 8000:8000"
echo "     Then: curl http://localhost:8000/health"
echo ""
echo "  4. Scale nodes:"
echo "     kubectl scale statefulset ${PROTOCOL}-node -n dht-system --replicas=10"
echo ""
echo "  5. Cleanup:"
echo "     kubectl delete -f k8s/${PROTOCOL}-statefulset.yaml"
echo "     kubectl delete namespace dht-system"
