#!/bin/bash
# Activate virtual environment and set PYTHONPATH

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found."
    echo "Please run: ./setup.sh"
    return 1
fi

# Activate virtual environment
source venv/bin/activate

# Set PYTHONPATH to current directory
export PYTHONPATH="${PWD}:${PYTHONPATH}"

echo "✓ Virtual environment activated"
echo "✓ PYTHONPATH set to: $PYTHONPATH"
echo ""
echo "You can now run:"
echo "  python main.py --test"
echo "  python distributed/orchestrator.py --protocol chord --deployment local --num-nodes 5"
