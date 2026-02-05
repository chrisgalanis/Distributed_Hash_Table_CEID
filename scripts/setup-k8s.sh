#!/bin/bash
# setup-k8s.sh - Set up Kubernetes for local development

set -e

echo "=== Kubernetes Setup for DHT Project ==="
echo ""

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"

echo "Detected: $OS $ARCH"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed."
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✓ Docker is installed"

# Offer choice between kind and minikube
echo ""
echo "Choose Kubernetes setup:"
echo "  1) kind (Kubernetes in Docker - RECOMMENDED, easiest)"
echo "  2) minikube (Traditional VM-based K8s)"
echo "  3) Skip (I already have kubectl configured)"
echo ""
read -p "Enter choice [1-3]: " CHOICE

case $CHOICE in
    1)
        echo ""
        echo "=== Installing kind ==="

        # Check if kind is already installed
        if command -v kind &> /dev/null; then
            echo "✓ kind is already installed"
        else
            echo "Installing kind..."

            if [[ "$OS" == "Linux" ]]; then
                # Install kind for Linux
                curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
                chmod +x ./kind
                sudo mv ./kind /usr/local/bin/kind
                echo "✓ kind installed"
            elif [[ "$OS" == "Darwin" ]]; then
                # Install kind for macOS
                if command -v brew &> /dev/null; then
                    brew install kind
                else
                    curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-darwin-amd64
                    chmod +x ./kind
                    sudo mv ./kind /usr/local/bin/kind
                fi
                echo "✓ kind installed"
            else
                echo "Unsupported OS. Please install kind manually:"
                echo "https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
                exit 1
            fi
        fi

        # Install kubectl if not present
        if ! command -v kubectl &> /dev/null; then
            echo "Installing kubectl..."

            if [[ "$OS" == "Linux" ]]; then
                curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
                chmod +x kubectl
                sudo mv kubectl /usr/local/bin/kubectl
            elif [[ "$OS" == "Darwin" ]]; then
                if command -v brew &> /dev/null; then
                    brew install kubectl
                else
                    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
                    chmod +x kubectl
                    sudo mv kubectl /usr/local/bin/kubectl
                fi
            fi
            echo "✓ kubectl installed"
        else
            echo "✓ kubectl is already installed"
        fi

        # Create kind cluster
        echo ""
        echo "Creating kind cluster 'dht-cluster'..."

        if kind get clusters | grep -q "dht-cluster"; then
            echo "✓ Cluster 'dht-cluster' already exists"
        else
            cat > /tmp/kind-config.yaml <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
- role: worker
- role: worker
EOF

            kind create cluster --name dht-cluster --config /tmp/kind-config.yaml
            echo "✓ kind cluster created with 3 worker nodes"
        fi

        # Set kubectl context
        kubectl config use-context kind-dht-cluster

        echo ""
        echo "✓ kind setup complete!"
        ;;

    2)
        echo ""
        echo "=== Installing minikube ==="

        # Check if minikube is already installed
        if command -v minikube &> /dev/null; then
            echo "✓ minikube is already installed"
        else
            echo "Installing minikube..."

            if [[ "$OS" == "Linux" ]]; then
                curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
                sudo install minikube-linux-amd64 /usr/local/bin/minikube
                rm minikube-linux-amd64
                echo "✓ minikube installed"
            elif [[ "$OS" == "Darwin" ]]; then
                if command -v brew &> /dev/null; then
                    brew install minikube
                else
                    curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-darwin-amd64
                    sudo install minikube-darwin-amd64 /usr/local/bin/minikube
                    rm minikube-darwin-amd64
                fi
                echo "✓ minikube installed"
            else
                echo "Unsupported OS. Please install minikube manually:"
                echo "https://minikube.sigs.k8s.io/docs/start/"
                exit 1
            fi
        fi

        # Install kubectl if not present
        if ! command -v kubectl &> /dev/null; then
            echo "Installing kubectl..."

            if [[ "$OS" == "Linux" ]]; then
                curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
                chmod +x kubectl
                sudo mv kubectl /usr/local/bin/kubectl
            elif [[ "$OS" == "Darwin" ]]; then
                if command -v brew &> /dev/null; then
                    brew install kubectl
                else
                    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
                    chmod +x kubectl
                    sudo mv kubectl /usr/local/bin/kubectl
                fi
            fi
            echo "✓ kubectl installed"
        else
            echo "✓ kubectl is already installed"
        fi

        # Start minikube
        echo ""
        echo "Starting minikube..."
        minikube start --driver=docker --nodes=3

        echo ""
        echo "✓ minikube setup complete!"
        ;;

    3)
        echo "Skipping Kubernetes installation"
        ;;

    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

# Verify kubectl works
echo ""
echo "=== Verifying Kubernetes Setup ==="
if kubectl cluster-info &> /dev/null; then
    echo "✓ kubectl can connect to cluster"
    kubectl cluster-info
    echo ""
    kubectl get nodes
else
    echo "❌ Cannot connect to Kubernetes cluster"
    exit 1
fi

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "  1. Build Docker image:"
echo "     ./scripts/build.sh"
echo ""
echo "  2. Load image into cluster:"
if [[ $CHOICE == "1" ]]; then
    echo "     kind load docker-image dht-node:latest --name dht-cluster"
elif [[ $CHOICE == "2" ]]; then
    echo "     eval \$(minikube docker-env)"
    echo "     ./scripts/build.sh"
fi
echo ""
echo "  3. Deploy to Kubernetes:"
echo "     ./scripts/deploy-k8s.sh chord 5"
echo ""
echo "Kubernetes cluster is ready for DHT deployment! 🚀"
