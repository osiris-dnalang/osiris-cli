#!/bin/bash
set -e

echo "========================================"
echo " OSIRIS FULL INSTALL (antiX compatible)"
echo "========================================"

# System deps
if command -v apt-get &>/dev/null; then
    echo "[1/5] Installing system packages..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        python3 python3-pip python3-venv \
        git build-essential cmake \
        libopenblas-dev curl wget
else
    echo "[1/5] Skipping apt (not available). Ensure Python 3.9+ is installed."
fi

# Virtualenv
echo "[2/5] Setting up virtual environment..."
if [ ! -d "osiris-env" ]; then
    python3 -m venv osiris-env
fi
# shellcheck disable=SC1091
source osiris-env/bin/activate

pip install --upgrade pip wheel --quiet

# Base CLI deps
echo "[3/5] Installing base CLI dependencies..."
pip install -r requirements.txt --quiet

# Production stack deps (heavy — skip with --lite)
if [ "${1}" != "--lite" ]; then
    echo "[4/5] Installing production stack dependencies..."
    pip install -r requirements_stack.txt --quiet
else
    echo "[4/5] Skipping heavy deps (--lite mode). Only base CLI available."
fi

# Critical extras
echo "[5/5] Installing extras..."
pip install networkx sentencepiece --quiet

echo ""
echo "========================================"
echo " OSIRIS INSTALLED SUCCESSFULLY"
echo "========================================"
echo ""
echo "  source osiris-env/bin/activate"
echo "  python osiris_cli.py --help"
echo "  python osiris_cli.py stack \"Build a leaderboard NCLM\" --iterations 2"
echo ""
