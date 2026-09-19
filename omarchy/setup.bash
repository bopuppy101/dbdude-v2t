#!/usr/bin/env bash
# Setup script for faster-whisper on Omarchy (Arch Linux + Hyprland, Wayland)
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== faster-whisper Omarchy Setup ==="

# System dependencies
# ydotool replaces xdotool: Hyprland is Wayland-only and xdotool cannot type into
# Wayland-native windows. libpulse provides pactl (PipeWire answers it via
# pipewire-pulse), qt6-wayland lets PySide6 run natively on Wayland, and
# portaudio backs the sounddevice capture path. Arch's python ships venv.
echo "Installing system packages..."
sudo pacman -S --needed --noconfirm portaudio libpulse qt6-wayland ydotool

# ydotoold needs write access to /dev/uinput, and the hotkey reader needs read
# access to /dev/input/event* (/dev/uinput is root:root 0600 and event* are
# root:input 0660 on stock Omarchy; desktop users are not in input). uaccess udev rules make
# logind grant the active desktop user an ACL on the devices at login and
# revoke it at logout - immediate effect, no group membership, no re-login.
# Arch does not autoload the uinput module: /dev/uinput exists only as a static
# placeholder node until something opens it, and udev cannot tag a device that
# is not there. Load it now and at every boot so ydotoold has it before login.
echo "Loading uinput kernel module..."
sudo modprobe uinput
echo 'uinput' | sudo tee /etc/modules-load.d/uinput.conf > /dev/null

echo "Granting desktop-user access to /dev/uinput and /dev/input..."
echo 'KERNEL=="uinput", SUBSYSTEM=="misc", TAG+="uaccess", OPTIONS+="static_node=uinput"' \
    | sudo tee /etc/udev/rules.d/70-uinput-uaccess.rules > /dev/null
echo 'SUBSYSTEM=="input", KERNEL=="event*", TAG+="uaccess"' \
    | sudo tee /etc/udev/rules.d/70-input-uaccess.rules > /dev/null
sudo udevadm control --reload-rules
sudo udevadm trigger --name-match=uinput
sudo udevadm trigger --subsystem-match=input

# ydotool types via /dev/uinput through the ydotoold daemon. Arch ships a
# ydotool.service user unit (WantedBy=default.target, Restart=always); this
# drop-in re-homes it to the graphical session, after device ACLs are granted,
# and caps restarts. Hyprland activates graphical-session.target on Omarchy.
echo "Enabling ydotool daemon (user service)..."
mkdir -p "${HOME}/.config/systemd/user/ydotool.service.d"
cat > "${HOME}/.config/systemd/user/ydotool.service.d/retry.conf" <<'EOF'
[Unit]
# Start with the graphical session, after logind grants desktop device access.
After=graphical-session.target
PartOf=graphical-session.target
# Initial start plus one retry; never keep restarting indefinitely.
StartLimitIntervalSec=infinity
StartLimitBurst=2

[Service]
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=
WantedBy=graphical-session.target
EOF
systemctl --user daemon-reload
systemctl --user reset-failed ydotool.service 2>/dev/null || true
systemctl --user reenable ydotool.service
if ! systemctl --user start ydotool.service || ! systemctl --user is-active --quiet ydotool.service; then
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
