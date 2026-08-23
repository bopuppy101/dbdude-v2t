#!/usr/bin/env bash
# Setup script for faster-whisper on Ubuntu 26.04 (Wayland)
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== faster-whisper Ubuntu 26.04 Setup ==="

# System dependencies
# ydotool replaces xdotool: 26.04 is Wayland-only and xdotool cannot type into
# Wayland-native windows. pulseaudio-utils provides pactl (no longer preinstalled).
echo "Installing system packages..."
sudo apt update
sudo apt install -y portaudio19-dev ydotool pulseaudio-utils python3-venv libxcb-cursor0

# ydotoold needs write access to /dev/uinput, and the hotkey reader needs read
# access to /dev/input/event* (both root:input 0660 by default, and desktop
# users are not in the input group on stock 26.04). uaccess udev rules make
# logind grant the active desktop user an ACL on the devices at login and
# revoke it at logout - immediate effect, no group membership, no re-login.
echo "Granting desktop-user access to /dev/uinput and /dev/input..."
echo 'KERNEL=="uinput", SUBSYSTEM=="misc", TAG+="uaccess", OPTIONS+="static_node=uinput"' \
    | sudo tee /etc/udev/rules.d/70-uinput-uaccess.rules > /dev/null
echo 'SUBSYSTEM=="input", KERNEL=="event*", TAG+="uaccess"' \
    | sudo tee /etc/udev/rules.d/70-input-uaccess.rules > /dev/null
sudo udevadm control --reload-rules
sudo udevadm trigger --name-match=uinput
sudo udevadm trigger --subsystem-match=input

# ydotool types via /dev/uinput through the ydotoold daemon; run it as a user
# service so it starts on login. The launcher points the app at its socket.
echo "Enabling ydotool daemon (user service)..."
systemctl --user reset-failed ydotool.service 2>/dev/null || true
systemctl --user enable --now ydotool.service
if ! systemctl --user is-active --quiet ydotool.service; then
    echo "WARNING: ydotoold failed to start - check: systemctl --user status ydotool.service"
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
echo "NOTE: Runs as your user (no sudo). Hotkeys read /dev/input via a"
echo "      logind ACL granted to whoever is logged into the desktop -"
echo "      effective immediately, per active session, no group needed."
