#!/usr/bin/env bash
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.
# Ubuntu 26.04 launcher - handles CUDA paths; runs as the desktop user
# (no sudo: hotkeys are read from /dev/input via the input group, and the
# system tray needs the process on the user's session D-Bus - 26.04's dbus
# refuses root connections)

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

# QT_QPA_PLATFORM=wayland: stock 26.04 no longer ships the xcb client libs the
# Qt "xcb" plugin needs (libxcb-icccm4 etc.); the bundled wayland plugin has no
# missing deps, so native Wayland is the reliable path. Everything else (audio,
# session D-Bus for the tray, ydotoold socket) is inherited naturally from the
# user's session.
QT_QPA_PLATFORM=wayland \
    LD_LIBRARY_PATH="$FINAL_LD_PATH" \
    "${VENV_PYTHON}" "${SCRIPT_DIR}/dbdude-v2t.py" "$@"
