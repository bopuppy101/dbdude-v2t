#!/usr/bin/env bash
# dbdude-v2t macOS Setup
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== dbdude-v2t macOS Setup ==="

# Check Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Install Python 3.10+ from python.org or via Homebrew."
    exit 1
fi

echo "Found $(python3 --version)"

# Create venv if it doesn't exist
if [ ! -d "${SCRIPT_DIR}/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "${SCRIPT_DIR}/venv"
fi

# Activate and install
echo "Installing Python packages (this may take several minutes)..."
source "${SCRIPT_DIR}/venv/bin/activate"
pip install --upgrade pip
pip install -r "${SCRIPT_DIR}/requirements.txt"

echo ""
echo "Installing v2t-push / v2t-pull aliases..."
python3 "${SCRIPT_DIR}/../setup-aliases.py"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To run:"
echo "  cd ${SCRIPT_DIR}"
echo "  source venv/bin/activate"
echo "  python3 dbdude-v2t.py"
echo ""
