#!/usr/bin/env bash
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).
# Omarchy (Arch + Hyprland) launcher - handles CUDA paths; runs as the desktop
# user (no sudo: hotkeys are read from /dev/input via the logind ACL that the
# uaccess udev rule grants the active desktop user, and the system tray needs
# the process on the user's session D-Bus where quickshell hosts the
# StatusNotifier tray)

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

# QT_QPA_PLATFORM=wayland: Hyprland has no Xorg; run PySide6 natively on
# Wayland via qt6-wayland rather than through XWayland. Everything else (audio,
# session D-Bus for the tray, ydotoold socket) is inherited naturally from the
# user's session.
# GPU: dbdude-v2t.py autodetects CUDA and uses the card whenever one is
# visible. To force CPU mode (e.g. to keep VRAM free for a local model server),
# uncomment the next line - hiding the card is the only switch.
# export CUDA_VISIBLE_DEVICES=""
QT_QPA_PLATFORM=wayland \
    LD_LIBRARY_PATH="$FINAL_LD_PATH" \
    "${VENV_PYTHON}" "${SCRIPT_DIR}/dbdude-v2t.py" "$@"
