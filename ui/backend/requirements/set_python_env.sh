#!/bin/bash
# Set up Python environment for Azure Cost Optimizer using UV
# This script creates a virtual environment and installs dependencies

set -e

echo "Setting up Python environment with UV..."

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "UV is not installed. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Create virtual environment
echo "Creating virtual environment..."
uv venv .venv

# Activate and install
echo "Installing dependencies..."
source .venv/bin/activate
uv pip install --prerelease=allow -e .

echo ""
echo "Setup complete! To activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the application:"
echo "  flask run"
