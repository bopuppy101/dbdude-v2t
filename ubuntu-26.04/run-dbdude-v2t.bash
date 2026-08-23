#!/usr/bin/env bash
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.
# Ubuntu 26.04 launcher - handles CUDA paths and runs with sudo

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

# Run with sudo, preserving the desktop session env the root process needs:
# - QT_QPA_PLATFORM=wayland + WAYLAND_DISPLAY: Qt (tray/GUIs) talks to the
#   compositor natively. Stock 26.04 no longer ships the xcb client libs the
#   Qt "xcb" plugin needs (libxcb-icccm4 etc.), and the bundled wayland plugin
#   has no missing deps — so native Wayland is the reliable path.
# - DISPLAY + XAUTHORITY kept as a fallback for anything that still wants X11
#   via XWayland (the GNOME cookie is at /run/user/<uid>/.mutter-Xwaylandauth.*
#   and sudo strips XAUTHORITY by default).
# - YDOTOOL_SOCKET: ydotoold runs as the desktop user; point the root-side
#   ydotool client at the user's daemon socket.
# - XDG_RUNTIME_DIR + PULSE_*: root reaches the user's PipeWire/Pulse session
#   (USB mics are exposed there with rate/channel conversion; raw ALSA hw:
#   devices are not) and the session D-Bus for the tray icon.
USER_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
sudo QT_QPA_PLATFORM=wayland \
     WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}" \
     DISPLAY="$DISPLAY" \
     XAUTHORITY="${XAUTHORITY:-}" \
     XDG_RUNTIME_DIR="$USER_RUNTIME_DIR" \
     YDOTOOL_SOCKET="${YDOTOOL_SOCKET:-${USER_RUNTIME_DIR}/.ydotool_socket}" \
     PULSE_SERVER="${PULSE_SERVER:-unix:${USER_RUNTIME_DIR}/pulse/native}" \
     PULSE_COOKIE="${PULSE_COOKIE:-${HOME}/.config/pulse/cookie}" \
     LD_LIBRARY_PATH="$FINAL_LD_PATH" \
     "${VENV_PYTHON}" "${SCRIPT_DIR}/dbdude-v2t.py" "$@"
