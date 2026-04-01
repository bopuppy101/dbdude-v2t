#!/usr/bin/env bash
# Setup script for faster-whisper on Ubuntu
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== faster-whisper Ubuntu Setup ==="

# System dependencies
echo "Installing system packages..."
sudo apt update
sudo apt install -y portaudio19-dev xdotool python3-venv

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
echo "Installing Python packages..."
source "${SCRIPT_DIR}/venv/bin/activate"
pip install -q --upgrade pip
pip install -q -r "${SCRIPT_DIR}/requirements.txt"

# Check for NVIDIA GPU and offer to install CUDA packages
if command -v nvidia-smi &> /dev/null; then
    echo ""
    echo "NVIDIA GPU detected. Installing CUDA packages for GPU acceleration..."
    pip install nvidia-cudnn-cu12 nvidia-cublas-cu12
else
    echo ""
    echo "No NVIDIA GPU detected. Skipping CUDA packages (will use CPU mode)."
fi

# Make launcher executable
chmod +x "${SCRIPT_DIR}/run-dbdude-v2t.bash"

# Create logs directory
mkdir -p ~/logs

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To run:"
echo "  cd ${SCRIPT_DIR}"
echo "  ./run-dbdude-v2t.bash"
echo ""
echo "Or add this alias to ~/.bashrc:"
echo "  alias rv='${SCRIPT_DIR}/run-dbdude-v2t.bash'"
echo ""
echo "NOTE: Requires sudo to run (keyboard module needs root on Linux)"
