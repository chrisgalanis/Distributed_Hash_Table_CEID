# Distributed Hash Tables: Chord vs Pastry Implementation

This project implements and experimentally evaluates two fundamental DHT (Distributed Hash Table) protocols: **Chord** and **Pastry**. It was developed for the Decentralized Data Engineering and Technologies course.

## 🚀 Two Deployment Modes

This implementation supports **both simulated and real distributed environments**:

### Simulated Mode (Default)
- Fast in-process simulation
- Perfect for development and experiments
- `python main.py --test`

### Distributed Mode (NEW!)
- Real distributed deployment with Docker & Kubernetes
- HTTP/REST communication between nodes
- Production-like environment
- See sections below for Docker and Kubernetes setup

### Deployment Comparison

| Feature | Simulated | Docker | Kubernetes |
|---------|-----------|--------|------------|
| **Network** | In-process | Real HTTP | Real HTTP |
| **Setup** | Quick | Easy | Moderate |
| **Latency** | ~0ms | 1-10ms | 1-50ms |
| **Isolation** | None | Container | Container + Orchestration |
| **Scaling** | Limited by RAM | Manual | Automatic |
| **Use Case** | Development | Testing | Production-like |
| **Command** | `python main.py --test` | `./scripts/deploy-docker.sh chord` | `./scripts/deploy-k8s.sh chord` |

## Project Overview

The implementation supports:
- **DHT Operations**: Build, Insert, Delete, Update, Lookup, Node Join, Node Leave
- **Performance Metrics**: Hop count comparison between Chord and Pastry
- **Concurrent Queries**: K parallel movie popularity lookups
- **Local Indexing**: B+ tree for efficient local storage at each peer
- **Visualization**: Comprehensive plotting of performance comparisons
- **Distributed Deployment**: Docker, Docker Compose, and Kubernetes support

## Features

### Chord DHT
- Consistent hashing with m-bit identifier space
- Finger table routing (O(log N) hops)
- Ring-based topology
- Dynamic join/leave with key redistribution

### Pastry DHT
- Prefix-based routing table
- Leaf set for proximity routing
- Base-2^b digit representation (default b=4, hexadecimal)
- O(log N) expected hops

### Local Storage
- B+ tree indexing for efficient key lookup
- Support for multiple values per key (movie titles can have multiple records)
- Fast exact-match queries

### Network Simulator
- Thread-based simulation with message passing
- Accurate hop counting for fair performance comparison
- Deterministic routing for reproducible experiments

## Project Structure

```
decentralised-data/
├── dht/
│   ├── __init__.py
│   ├── common.py          # Common interfaces and utilities
│   ├── network.py         # Network simulator with hop counting
│   ├── local_index.py     # B+ tree implementation
│   ├── chord.py           # Chord DHT implementation
│   ├── pastry.py          # Pastry DHT implementation
│   └── data_loader.py     # Movie dataset loading utilities
├── experiments/
│   ├── __init__.py
│   ├── workload.py        # Workload generation
│   ├── runner.py          # Experiment execution
│   └── plots.py           # Visualization utilities
├── data/                  # Place movies_dataset.csv here
├── results/               # Experiment results and plots
├── main.py                # Main entry point
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Installation

### Prerequisites

**For Simulated Mode:**
- Python 3.8 or higher
- pip package manager

**For Distributed Mode (Docker):**
- Docker and Docker Compose
- Python 3.8+ (for orchestrator)

**For Distributed Mode (Kubernetes):**
- Kubernetes (minikube for local development)
- kubectl CLI tool
- Docker

### Setup

1. Clone or extract the project:
```bash
cd decentralised-data
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Download the movies dataset:
   - Download from: https://www.kaggle.com/datasets/mustafasayed1181/movies-metadata-cleaned-dataset-19002025
   - Place `movies_dataset.csv` in the `data/` directory

### What are Docker and Kubernetes?

**Docker** is a platform that packages your application and its dependencies into containers - lightweight, portable units that run consistently across different environments. Think of it as shipping your entire development environment in a box.

**Kubernetes (k8s)** is a container orchestration platform that manages Docker containers at scale. It automatically handles deployment, scaling, load balancing, and self-healing of containerized applications across multiple machines.

**Why use them for this project?**
- **Docker**: Run each DHT node in its own isolated container with real network communication (instead of simulated)
- **Kubernetes**: Deploy and manage many DHT nodes easily, with automatic scaling and monitoring
- **Real distributed testing**: Experience how distributed systems work in production environments

## Usage

### 1. Basic Functionality Test

Verify that Chord and Pastry implementations work correctly:

```bash
python main.py --test
```

This runs a quick test with a small dataset to ensure all operations work.

### 2. Scalability Experiment

Compare Chord and Pastry performance with varying numbers of nodes:

```bash
# Default: test with 50, 100, 200, 500 nodes
python main.py --experiment scalability

# Custom node counts
python main.py --experiment scalability --nodes 100 200 500 1000

# Use more items and operations
python main.py --experiment scalability --items 5000 --operations 1000

# Use real movie dataset (if available)
python main.py --experiment scalability --use-real-data --data-file data/movies_dataset.csv
```

**Output:**
- Results saved to `results/experiment_results.csv`
- Plots saved to `results/` directory
- Console summary showing average hops for each operation

### 3. Concurrent Popularity Lookup

Look up the popularity of K movies concurrently:

```bash
# Lookup top 10 popular movies with 100 nodes
python main.py --experiment popularity --k-movies 10 --num-nodes 100

# With more movies and nodes
python main.py --experiment popularity --k-movies 50 --num-nodes 500 --items 10000

# Use real data
python main.py --experiment popularity --k-movies 20 --use-real-data --data-file data/movies_dataset.csv
```

**Output:**
- Popularity values for each movie
- Total and average hops for Chord and Pastry
- Performance comparison

### 4. Generate Plots Only

If you already have results and want to regenerate plots:

```bash
python main.py --plot-only results/experiment_results.csv
```

## Docker Deployment

Docker allows you to run your DHT nodes in isolated containers with real HTTP communication between nodes.

### Quick Start with Docker

**1. Install Docker:**

Linux (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo usermod -aG docker $USER  # Add yourself to docker group
newgrp docker  # Refresh group membership
```

macOS/Windows: Download Docker Desktop from https://www.docker.com/products/docker-desktop

**2. Build the Docker image:**

```bash
./scripts/build.sh
```

Or manually:
```bash
docker build -t dht-node:latest -f docker/Dockerfile .
```

**3. Deploy DHT nodes using Docker Compose:**

Start 5 Chord nodes (ports 8000-8004):
```bash
./scripts/deploy-docker.sh chord
```

Start 5 Pastry nodes (ports 9000-9004):
```bash
./scripts/deploy-docker.sh pastry
```

Or manually with docker-compose:
```bash
# Start Chord nodes
docker compose -f docker/docker-compose.yml up -d chord-node-0 chord-node-1 chord-node-2 chord-node-3 chord-node-4

# Start Pastry nodes
docker compose -f docker/docker-compose.yml up -d pastry-node-0 pastry-node-1 pastry-node-2 pastry-node-3 pastry-node-4
```

**4. Verify nodes are running:**

```bash
# Check running containers
docker ps

# Test health endpoints
curl http://localhost:8000/health
curl http://localhost:8001/health
```

**5. Run an experiment:**

```bash
python distributed/orchestrator.py \
    --protocol chord \
    --deployment docker \
    --num-nodes 5 \
    --num-items 500
```

**6. View logs:**

```bash
# View all logs
docker compose -f docker/docker-compose.yml logs -f

# View specific node
docker compose -f docker/docker-compose.yml logs -f chord-node-0
```

**7. Stop the deployment:**

```bash
docker compose -f docker/docker-compose.yml down
```

### Docker Commands Reference

```bash
# List running containers
docker ps

# Stop all containers
docker compose -f docker/docker-compose.yml down

# Rebuild and restart
docker compose -f docker/docker-compose.yml up -d --build

# Remove all stopped containers
docker container prune

# View resource usage
docker stats
```

## Kubernetes Deployment

Kubernetes provides production-grade orchestration for running many DHT nodes with automatic scaling and self-healing.

### Quick Start with Kubernetes

**1. Install Minikube and kubectl:**

Linux:
```bash
# Install Minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

macOS:
```bash
brew install minikube kubectl
```

Windows: Download from https://minikube.sigs.k8s.io/docs/start/

**2. Start Minikube:**

```bash
minikube start
```

**3. Build image in Minikube's Docker:**

```bash
# Point to Minikube's Docker
eval $(minikube docker-env)

# Build the image
./scripts/build.sh
```

**4. Deploy to Kubernetes:**

Deploy Chord:
```bash
./scripts/deploy-k8s.sh chord
```

Deploy Pastry:
```bash
./scripts/deploy-k8s.sh pastry
```

Or manually:
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/chord-statefulset.yaml
```

**5. Check pod status:**

```bash
kubectl get pods -n dht-system
```

**6. Access a node (port forwarding):**

```bash
# Forward chord-node-0 to localhost:8000
kubectl port-forward -n dht-system chord-node-0 8000:8000

# In another terminal, test it
curl http://localhost:8000/health
```

**7. View logs:**

```bash
# Logs from specific pod
kubectl logs -n dht-system chord-node-0 -f

# Logs from all pods
kubectl logs -n dht-system -l app=chord-node
```

**8. Scale deployment:**

```bash
# Scale to 10 nodes
kubectl scale statefulset chord-node -n dht-system --replicas=10
```

**9. Cleanup:**

```bash
# Delete deployment
kubectl delete -f k8s/chord-statefulset.yaml

# Or delete entire namespace
kubectl delete namespace dht-system

# Stop Minikube
minikube stop
```

### Kubernetes Commands Reference

```bash
# List all pods
kubectl get pods -n dht-system

# Describe pod (see errors)
kubectl describe pod chord-node-0 -n dht-system

# View logs
kubectl logs -n dht-system chord-node-0 -f

# Execute command in pod
kubectl exec -it chord-node-0 -n dht-system -- bash

# Scale statefulset
kubectl scale statefulset chord-node -n dht-system --replicas=10

# List services
kubectl get services -n dht-system

# Port forward
kubectl port-forward -n dht-system chord-node-0 8000:8000
```

## Command-Line Options

```
--test                  Run basic functionality test
--experiment TYPE       Run experiment (scalability or popularity)
--nodes N1 N2 ...      List of node counts to test
--num-nodes N          Number of nodes (for popularity experiment)
--items N              Number of items/movies to use (default: 1000)
--operations N         Number of operations per experiment (default: 500)
--k-movies K           Number of movies for concurrent lookup (default: 10)
--m M                  Bits in DHT identifier space (default: 16)
--seed N               Random seed for reproducibility (default: 42)
--use-real-data        Use real movie dataset
--data-file PATH       Path to movies CSV file
--output PATH          Output file for results
--no-plots             Skip generating plots
--plot-only CSV        Generate plots from existing results
```

## Understanding the Results

### Experiment Results CSV

The CSV file contains:
- `protocol`: Chord or Pastry
- `operation`: lookup, insert, delete, update, join, leave
- `num_nodes`: Number of nodes in the DHT
- `num_items`: Number of items stored
- `avg_hops`: Average hops per operation
- `max_hops`: Maximum hops observed
- `min_hops`: Minimum hops observed
- `total_ops`: Number of operations executed

### Generated Plots

1. **hops_vs_nodes_[operation].png**: Individual plots for each operation showing how hops scale with node count

2. **all_operations_comparison.png**: Multi-subplot figure comparing all operations

3. **performance_ratio.png**: Chord/Pastry hop ratio
   - Ratio > 1: Pastry is more efficient
   - Ratio < 1: Chord is more efficient

4. **hops_distribution.png**: Box plots showing hop distributions

## Implementation Details

### Key Design Decisions

1. **Identifier Space**: Configurable m-bit space (default m=16, supporting up to 65,536 nodes)

2. **Key Normalization**: Movie titles are normalized (lowercase, stripped whitespace) for consistent hashing

3. **Multiple Values per Key**: Since movie titles can repeat across years, each key stores a list of movie records

4. **Routing Table Initialization**: Both protocols build routing structures statically during the build phase, then maintain them during join/leave operations

5. **Hop Counting**: Network simulator accurately counts message hops, excluding the final data retrieval

6. **Thread Safety**: Network simulator uses locks to ensure thread-safe operation during concurrent lookups

### Theoretical Performance

- **Chord**: O(log N) hops for lookup/insert/delete
- **Pastry**: O(log N) expected hops with better constant factors

### Limitations

This is an educational implementation with some simplifications:
- **Simulated mode**: Uses in-process communication (but see Docker/Kubernetes deployment for real distributed networking)
- Simplified node join/leave (rebuilds routing structures globally)
- No network failures or Byzantine nodes
- No replication or fault tolerance

**Note**: The Docker and Kubernetes deployment modes address the first limitation by providing real HTTP-based network communication between nodes running in separate containers.

## Dataset Information

The movie dataset contains:
- **946,000+ movies** from 1900-2025
- **14 attributes**: id, title, adult, original_language, origin_country, release_date, genre_names, production_company_names, budget, revenue, runtime, popularity, vote_average, vote_count

**Dataset Citation**: Movies Metadata Cleaned Dataset (1900-2025) from Kaggle by Mustafa Sayed

## Performance Tips

For large-scale experiments:
- Use m=20 or higher for better hash distribution with many nodes
- Limit items to 10,000-50,000 for reasonable runtime
- Reduce operations count for quick tests
- Use synthetic data for faster loading

## Troubleshooting

**Import Errors:**
```bash
# Make sure you're in the project root directory
cd /path/to/decentralised-data
python main.py --test
```

**Memory Issues with Large Datasets:**
```bash
# Reduce items and operations
python main.py --experiment scalability --items 1000 --operations 200
```

**No Plots Generated:**
```bash
# Install matplotlib
pip install matplotlib

# Or skip plots
python main.py --experiment scalability --no-plots
```

### Docker Troubleshooting

**"Cannot connect to Docker daemon":**
```bash
# Check if Docker is running
sudo systemctl status docker

# Start Docker
sudo systemctl start docker
```

**"Port already in use":**
```bash
# Find what's using the port
lsof -i :8000

# Kill the process or change ports in docker-compose.yml
```

**"Permission denied" (Linux):**
```bash
# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

**Container keeps restarting:**
```bash
# Check logs for errors
docker compose -f docker/docker-compose.yml logs chord-node-0
```

### Kubernetes Troubleshooting

**Pods stuck in "Pending":**
```bash
# Check what's wrong
kubectl describe pod chord-node-0 -n dht-system
```

**"ImagePullBackOff" error:**
```bash
# Build image in Minikube's Docker
eval $(minikube docker-env)
./scripts/build.sh

# Make sure imagePullPolicy is set to Never in YAML
```

**Can't access pods:**
```bash
# Use port forwarding
kubectl port-forward -n dht-system chord-node-0 8000:8000
```

**Minikube not starting:**
```bash
# Delete and restart
minikube delete
minikube start
```

## Project Features

This implementation includes:
- ✅ Chord DHT with finger table routing
- ✅ Pastry DHT with prefix routing and leaf sets
- ✅ B+ tree local indexing
- ✅ Network simulator with hop counting
- ✅ Comprehensive experiment framework
- ✅ Data loading for movies dataset
- ✅ Concurrent popularity lookup
- ✅ Visualization and plotting
- ✅ Configurable workload generation
- ✅ **Docker deployment** with Docker Compose
- ✅ **Kubernetes deployment** with StatefulSets
- ✅ Complete documentation

# Distributed_Hash_Table_CEID
