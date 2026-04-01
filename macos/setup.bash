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

# Verify Python version is 3.10+
read -r PYTHON_MAJOR PYTHON_MINOR <<< "$(python3 -c 'import sys; print(sys.version_info.major, sys.version_info.minor)')"
PYTHON_VERSION="${PYTHON_MAJOR}.${PYTHON_MINOR}"
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo "ERROR: Python 3.10+ is required, but found Python ${PYTHON_VERSION}."
    exit 1
fi

echo "Found Python ${PYTHON_VERSION}"

# Create venv if it doesn't exist
if [ ! -d "${SCRIPT_DIR}/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "${SCRIPT_DIR}/venv"
fi

# Verify requirements.txt exists
if [ ! -f "${SCRIPT_DIR}/requirements.txt" ]; then
    echo "ERROR: requirements.txt not found in ${SCRIPT_DIR}."
    exit 1
fi

# Activate and install
echo "Installing Python packages (this may take several minutes)..."
source "${SCRIPT_DIR}/venv/bin/activate"
pip install -q --upgrade pip
pip install -q -r "${SCRIPT_DIR}/requirements.txt"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To run:"
echo "  cd ${SCRIPT_DIR}"
echo "  source venv/bin/activate"
echo "  python3 dbdude-v2t.py"
echo ""
