# DHT Comparison: Chord vs Pastry

Experimental comparison of Chord and Pastry distributed hash table protocols.

## Quick Start

### Prerequisites

```bash
pip install -r requirements.txt
```

### Run Comparison

**Simulated mode (RECOMMENDED - generates full comparison with plots):**
```bash
./compare.sh simulated 10000
```
- Tests all operations: insert, delete, lookup, update, join, leave
- Measures hop counts for Chord vs Pastry
- Generates 9 comparison plots automatically
- Tests across 50, 100, 200, 500 nodes
- **Use this for your assignment/experiments**

**Docker mode (deployment testing only):**
```bash
./compare.sh docker 5 500
```
- Tests distributed deployment with real containers
- No comprehensive plots (basic testing only)

**Kubernetes mode (deployment testing only):**
```bash
./compare.sh k8s 5 500
```
- Tests Kubernetes orchestration
- No comprehensive plots (basic testing only)

## Results

After running, check:
- `comparison_results/results.csv` - Performance metrics
- `results/*.png` - 9 comparison plots

## What Gets Tested

- **Operations**: insert, delete, lookup, update, node join, node leave
- **Metric**: Number of hops per operation
- **Comparison**: Chord vs Pastry across different network sizes (50, 100, 200, 500 nodes)

## Dataset

If `data/movies_dataset.csv` exists, it will be used automatically. Otherwise, synthetic data is generated.

## Docker Setup (Optional)

```bash
# Install Docker
sudo apt-get install docker.io docker-compose  # Linux
# OR download Docker Desktop for Mac/Windows

# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

## Kubernetes Setup (Optional)

```bash
# Install minikube and kubectl
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl

# Start cluster
minikube start
```

## Usage Examples

```bash
# Quick test with simulated mode
./compare.sh simulated 1000

# Docker with 10 nodes
./compare.sh docker 10 5000

# K8s with 5 nodes
./compare.sh k8s 5 500
```

## Performance Summary

Based on experiments with 50-500 nodes:
- **Pastry**: ~48-53% better than Chord for most operations
- **Chord**: O(log N) hops, uses finger table routing
- **Pastry**: O(log N) hops, uses prefix routing + leaf sets

## Project Structure

```
├── compare.sh              # Main comparison script
├── dht/                    # DHT implementations
│   ├── chord.py           # Chord protocol
│   ├── pastry.py          # Pastry protocol
│   └── data_loader.py     # Dataset utilities
├── experiments/            # Experiment runner and workload generator
├── distributed/            # Docker/K8s deployment
├── results/               # Generated plots
└── comparison_results/    # Metrics CSV
```

## Requirements

- Python 3.8+
- Required packages: see `requirements.txt`
- Docker (optional, for distributed mode)
- Kubernetes/minikube (optional, for K8s mode)
