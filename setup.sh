#!/bin/bash
# Setup script for DHT project

set -e

echo "Setting up DHT project..."
echo ""

# Create virtual environment
echo "1. Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "2. Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "3. Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "4. Installing dependencies..."
pip install -r requirements.txt

# Set PYTHONPATH
echo "5. Setting PYTHONPATH..."
export PYTHONPATH="${PWD}:${PYTHONPATH}"

echo ""
echo "✓ Setup complete!"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "To set PYTHONPATH (needed each time), run:"
echo "  export PYTHONPATH=\$PWD:\$PYTHONPATH"
echo ""
echo "Or source the activate script:"
echo "  source scripts/activate-env.sh"
echo ""
echo "Now you can run:"
echo "  python main.py --test"
echo "  python distributed/orchestrator.py --protocol chord --deployment local --num-nodes 5"
