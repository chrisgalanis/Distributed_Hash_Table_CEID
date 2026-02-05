#!/bin/bash
# Helper script to guide through commits
# Run with: ./scripts/commit-helper.sh [commit-number]

COMMIT_NUM=${1:-1}

case $COMMIT_NUM in
  1)
    echo "Commit 1: Initial project structure and requirements"
    echo "Files: requirements.txt"
    echo ""
    echo "Run:"
    echo "  git add requirements.txt"
    echo "  git commit -m 'feat: initial project structure and dependencies'"
    ;;
  2)
    echo "Commit 2: Common DHT interfaces"
    echo "Files: dht/__init__.py dht/common.py"
    echo ""
    echo "Run:"
    echo "  git add dht/__init__.py dht/common.py"
    echo "  git commit -m 'feat: add common DHT interfaces and hash utilities'"
    ;;
  3)
    echo "Commit 3: Network simulator"
    echo "Files: dht/network.py"
    echo ""
    echo "Run:"
    echo "  git add dht/network.py"
    echo "  git commit -m 'feat: implement network simulator with hop counting'"
    ;;
  4)
    echo "Commit 4: B+ tree local indexing"
    echo "Files: dht/local_index.py"
    echo ""
    echo "Run:"
    echo "  git add dht/local_index.py"
    echo "  git commit -m 'feat: implement B+ tree for local node storage'"
    ;;
  5)
    echo "Commit 5: Chord DHT"
    echo "Files: dht/chord.py"
    echo ""
    echo "Run:"
    echo "  git add dht/chord.py"
    echo "  git commit -m 'feat: implement Chord DHT with finger table routing'"
    ;;
  6)
    echo "Commit 6: Pastry DHT"
    echo "Files: dht/pastry.py"
    echo ""
    echo "Run:"
    echo "  git add dht/pastry.py"
    echo "  git commit -m 'feat: implement Pastry DHT with prefix routing'"
    ;;
  7)
    echo "Commit 7: Data loader"
    echo "Files: dht/data_loader.py"
    echo ""
    echo "Run:"
    echo "  git add dht/data_loader.py"
    echo "  git commit -m 'feat: add movie dataset loader and utilities'"
    ;;
  8)
    echo "Commit 8: Workload generator"
    echo "Files: experiments/__init__.py experiments/workload.py"
    echo ""
    echo "Run:"
    echo "  git add experiments/__init__.py experiments/workload.py"
    echo "  git commit -m 'feat: add workload generator for DHT experiments'"
    ;;
  9)
    echo "Commit 9: Experiment runner"
    echo "Files: experiments/runner.py"
    echo ""
    echo "Run:"
    echo "  git add experiments/runner.py"
    echo "  git commit -m 'feat: add experiment runner for performance evaluation'"
    ;;
  10)
    echo "Commit 10: Plotting utilities"
    echo "Files: experiments/plots.py"
    echo ""
    echo "Run:"
    echo "  git add experiments/plots.py"
    echo "  git commit -m 'feat: add visualization and plotting utilities'"
    ;;
  11)
    echo "Commit 11: Main script"
    echo "Files: main.py"
    echo ""
    echo "Run:"
    echo "  git add main.py"
    echo "  git commit -m 'feat: add main script with CLI interface'"
    ;;
  12)
    echo "Commit 12: Example script"
    echo "Files: example_usage.py"
    echo ""
    echo "Run:"
    echo "  git add example_usage.py"
    echo "  git commit -m 'docs: add example usage script'"
    ;;
  13)
    echo "Commit 13: Quick comparison"
    echo "Files: run_comparison.py"
    echo ""
    echo "Run:"
    echo "  git add run_comparison.py"
    echo "  git commit -m 'feat: add quick comparison script'"
    ;;
  14)
    echo "Commit 14: Core documentation"
    echo "Files: README.md QUICKSTART.md IMPLEMENTATION_SUMMARY.md"
    echo ""
    echo "Run:"
    echo "  git add README.md QUICKSTART.md IMPLEMENTATION_SUMMARY.md"
    echo "  git commit -m 'docs: add comprehensive README and guides'"
    ;;
  15)
    echo "Commit 15: Distributed network"
    echo "Files: distributed/__init__.py distributed/network_real.py"
    echo ""
    echo "Run:"
    echo "  git add distributed/__init__.py distributed/network_real.py"
    echo "  git commit -m 'feat: add distributed network layer with HTTP communication'"
    ;;
  16)
    echo "Commit 16: Node server"
    echo "Files: distributed/node_server.py"
    echo ""
    echo "Run:"
    echo "  git add distributed/node_server.py"
    echo "  git commit -m 'feat: add REST API server for DHT nodes'"
    ;;
  17)
    echo "Commit 17: Orchestrator"
    echo "Files: distributed/orchestrator.py"
    echo ""
    echo "Run:"
    echo "  git add distributed/orchestrator.py"
    echo "  git commit -m 'feat: add orchestrator for distributed experiments'"
    ;;
  18)
    echo "Commit 18: Docker support"
    echo "Files: docker/Dockerfile docker/docker-compose.yml docker/.dockerignore"
    echo ""
    echo "Run:"
    echo "  git add docker/"
    echo "  git commit -m 'feat: add Docker containerization support'"
    ;;
  19)
    echo "Commit 19: Kubernetes manifests"
    echo "Files: k8s/"
    echo ""
    echo "Run:"
    echo "  git add k8s/"
    echo "  git commit -m 'feat: add Kubernetes deployment manifests'"
    ;;
  20)
    echo "Commit 20: Deployment scripts"
    echo "Files: scripts/"
    echo ""
    echo "Run:"
    echo "  git add scripts/*.sh"
    echo "  git commit -m 'feat: add helper scripts for deployment'"
    ;;
  21)
    echo "Commit 21: Setup script"
    echo "Files: setup.sh"
    echo ""
    echo "Run:"
    echo "  git add setup.sh"
    echo "  git commit -m 'feat: add setup script for virtual environment'"
    ;;
  22)
    echo "Commit 22: Distributed docs"
    echo "Files: DISTRIBUTED_*.md"
    echo ""
    echo "Run:"
    echo "  git add DISTRIBUTED_QUICKSTART.md DISTRIBUTED_DEPLOYMENT.md DISTRIBUTED_SUMMARY.md"
    echo "  git commit -m 'docs: add distributed deployment documentation'"
    ;;
  23)
    echo "Commit 23: Additional docs"
    echo "Files: SETUP_GUIDE.md PROJECT_OVERVIEW.md RESULTS_INTERPRETATION.md"
    echo ""
    echo "Run:"
    echo "  git add SETUP_GUIDE.md PROJECT_OVERVIEW.md RESULTS_INTERPRETATION.md"
    echo "  git commit -m 'docs: add setup guide and project overview'"
    ;;
  24)
    echo "Commit 24: Test utilities"
    echo "Files: test_plots.py"
    echo ""
    echo "Run:"
    echo "  git add test_plots.py"
    echo "  git commit -m 'test: add plot testing utility'"
    ;;
  25)
    echo "Commit 25: Fix Pastry routing"
    echo "Files: dht/pastry.py (already modified)"
    echo ""
    echo "Run:"
    echo "  git add dht/pastry.py"
    echo "  git commit -m 'fix: prevent infinite routing loop in Pastry'"
    ;;
  26)
    echo "Commit 26: Fix experiment runner"
    echo "Files: experiments/runner.py (already modified)"
    echo ""
    echo "Run:"
    echo "  git add experiments/runner.py"
    echo "  git commit -m 'fix: handle string values in experiment operations'"
    ;;
  27)
    echo "Commit 27: Fix Docker orchestrator"
    echo "Files: distributed/orchestrator.py (already modified)"
    echo ""
    echo "Run:"
    echo "  git add distributed/orchestrator.py"
    echo "  git commit -m 'fix: correct Docker network addressing in orchestrator'"
    ;;
  28)
    echo "Commit 28: Add directories"
    echo ""
    echo "Run:"
    echo "  mkdir -p data results"
    echo "  touch data/.gitkeep results/.gitkeep"
    echo "  git add data/.gitkeep results/.gitkeep"
    echo "  git commit -m 'chore: add placeholder for data and results directories'"
    ;;
  29)
    echo "Commit 29: Add .gitignore"
    echo ""
    echo "See COMMIT_PLAN.md for .gitignore content"
    echo "Then run:"
    echo "  git add .gitignore"
    echo "  git commit -m 'chore: add .gitignore'"
    ;;
  *)
    echo "Unknown commit number: $COMMIT_NUM"
    echo "Valid range: 1-29"
    echo ""
    echo "Usage: ./scripts/commit-helper.sh [1-29]"
    echo "Or see: COMMIT_PLAN.md for full details"
    ;;
esac

echo ""
echo "Next: ./scripts/commit-helper.sh $((COMMIT_NUM + 1))"
