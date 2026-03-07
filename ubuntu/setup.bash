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

# Create venv if it doesn't exist
if [ ! -d "${SCRIPT_DIR}/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "${SCRIPT_DIR}/venv"
fi

# Activate and install
echo "Installing Python packages..."
source "${SCRIPT_DIR}/venv/bin/activate"
pip install --upgrade pip
pip install -r "${SCRIPT_DIR}/requirements.txt"

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
