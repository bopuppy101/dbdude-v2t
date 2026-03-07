#!/usr/bin/env bash
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.
# Ubuntu launcher - handles CUDA paths and runs with sudo

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/venv/bin/python3"

# Check venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: venv not found at ${SCRIPT_DIR}/venv"
    echo "  Run setup.bash first to create it"
    exit 1
fi

# Set library path for CUDA/cuDNN (if nvidia packages installed)
LD_LIBRARY_PATH_EXTRA=""
CUDNN_PATH=$("${VENV_PYTHON}" -c "import nvidia.cudnn; print(nvidia.cudnn.__path__[0])" 2>/dev/null)/lib || true
CUBLAS_PATH=$("${VENV_PYTHON}" -c "import nvidia.cublas; print(nvidia.cublas.__path__[0])" 2>/dev/null)/lib || true

if [ -d "$CUDNN_PATH" ]; then
    LD_LIBRARY_PATH_EXTRA="${CUDNN_PATH}"
fi
if [ -d "$CUBLAS_PATH" ]; then
    if [ -n "$LD_LIBRARY_PATH_EXTRA" ]; then
        LD_LIBRARY_PATH_EXTRA="${LD_LIBRARY_PATH_EXTRA}:${CUBLAS_PATH}"
    else
        LD_LIBRARY_PATH_EXTRA="${CUBLAS_PATH}"
    fi
fi

# Build final LD_LIBRARY_PATH
if [ -n "$LD_LIBRARY_PATH_EXTRA" ]; then
    FINAL_LD_PATH="${LD_LIBRARY_PATH_EXTRA}:${LD_LIBRARY_PATH:-}"
else
    FINAL_LD_PATH="${LD_LIBRARY_PATH:-}"
fi

# Run with sudo, preserving DISPLAY for xdotool
sudo DISPLAY="$DISPLAY" LD_LIBRARY_PATH="$FINAL_LD_PATH" "${VENV_PYTHON}" "${SCRIPT_DIR}/dbdude-v2t.py" "$@"
