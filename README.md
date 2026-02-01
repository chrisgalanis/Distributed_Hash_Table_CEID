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
- See **DISTRIBUTED_QUICKSTART.md** to get started

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
- Python 3.8 or higher
- pip package manager

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
- Simulated network (not real sockets/distributed deployment)
- Simplified node join/leave (rebuilds routing structures globally)
- No network failures or Byzantine nodes
- No replication or fault tolerance

## Extension Ideas

If you want to extend this project:

1. **Real Network**: Replace simulator with socket-based communication
2. **Docker/Kubernetes**: Deploy nodes as containers
3. **Replication**: Add data replication for fault tolerance
4. **Range Queries**: Extend B+ tree for range queries on popularity/rating
5. **Load Balancing**: Implement virtual nodes for better load distribution
6. **Failure Handling**: Add node failure detection and recovery
7. **More DHTs**: Implement Kademlia, CAN, or other DHT protocols

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

## Project Timeline

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
- ✅ Complete documentation

## Academic Integrity

This is an implementation guide for educational purposes. If you're submitting this for academic work:
- Understand every line of code
- Customize the implementation
- Add your own experiments and analysis
- Properly cite any external resources used
- Follow your institution's academic integrity policies

## License

This project is provided for educational purposes as part of the Decentralized Data Engineering and Technologies course.

## Contact

For questions about the implementation or experiments, refer to:
- Course instructors: S. Sioutas, A. Komninos, G. Vonitsanos
- Course materials and documentation

---

**Good luck with your experiments!**
# Distributed_Hash_Table_CEID
