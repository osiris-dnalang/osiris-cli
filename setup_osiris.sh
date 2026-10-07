#!/bin/bash
##############################################################################
# OSIRIS Automated Discovery - Setup Script
# 
# This script sets up your environment for automated quantum discovery
# with rigorous statistical validation and Zenodo publishing.
#
# Usage:
#   bash setup_osiris.sh
#
##############################################################################

set -e

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                  OSIRIS AUTOMATED DISCOVERY - SETUP                          ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python
echo "→ Checking Python installation..."
python3 --version
echo "✓ Python OK"
echo ""

# Create virtual environment
if [ -d "osiris_env" ]; then
    echo "✓ Virtual environment already exists"
else
    echo "→ Creating virtual environment..."
    python3 -m venv osiris_env
    echo "✓ Virtual environment created"
fi

# Activate
echo "→ Activating virtual environment..."
source osiris_env/bin/activate
echo "✓ Activated"
echo ""

# Install dependencies
echo "→ Installing dependencies..."
pip install --upgrade pip
pip install -r requirements_automation.txt
echo "✓ Dependencies installed"
echo ""

# Check environment variables
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                      ENVIRONMENT CONFIGURATION                               ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

if [ -z "$IBM_QUANTUM_TOKEN" ]; then
    echo "⚠  IBM_QUANTUM_TOKEN not set"
    echo "   Get token at: https://quantum.ibm.com/"
    echo "   Set with: export IBM_QUANTUM_TOKEN='your_token'"
else
    echo "✓ IBM_QUANTUM_TOKEN is set"
fi

if [ -z "$ZENODO_TOKEN" ]; then
    echo "⚠  ZENODO_TOKEN not set (optional)"
    echo "   Get token at: https://zenodo.org/account/settings/"
    echo "   Set with: export ZENODO_TOKEN='your_token'"
else
    echo "✓ ZENODO_TOKEN is set"
fi

if [ -z "$IBM_BACKEND" ]; then
    echo "ℹ  IBM_BACKEND not set (using default: ibm_torino)"
    export IBM_BACKEND="ibm_torino"
else
    echo "✓ IBM_BACKEND is set to: $IBM_BACKEND"
fi

echo ""

# Create output directory
mkdir -p discoveries
echo "✓ Created discoveries directory"
echo ""

# Test imports
echo "→ Testing imports..."
python3 -c "
import qiskit; print(f'  ✓ Qiskit {qiskit.__version__}')
import numpy; print(f'  ✓ NumPy {numpy.__version__}')
import scipy; print(f'  ✓ SciPy {scipy.__version__}')
import requests; print(f'  ✓ Requests installed')
"
echo ""

# Summary
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                           SETUP COMPLETE ✓                                  ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1. Set API tokens (if not already set):"
echo "   export IBM_QUANTUM_TOKEN='your_ibm_token'"
echo "   export ZENODO_TOKEN='your_zenodo_token'  # optional"
echo ""
echo "2. View available experiments:"
echo "   python osiris_cli.py list"
echo ""
echo "3. Run week-1 campaign:"
echo "   python osiris_cli.py run --campaign week1_foundation"
echo ""
echo "4. Check results:"
echo "   python osiris_cli.py status"
echo ""
echo "5. Publish to Zenodo (dry-run first):"
echo "   python osiris_cli.py publish --dry-run"
echo ""
echo "For detailed documentation, see: OSIRIS_README.md"
echo ""
