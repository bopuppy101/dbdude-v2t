#!/usr/bin/env bash
# dbdude-v2t macOS Setup
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== dbdude-v2t macOS Setup ==="

# Pick a Python 3.10+ interpreter.
# On macOS bare `python3` is usually Apple's stub Python 3.9 (/usr/bin/python3),
# which is first on PATH ahead of Homebrew. So prefer explicit versioned binaries
# and only fall back to bare `python3` if it happens to be new enough.
PY=""
PYTHON_VERSION=""
for cand in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    command -v "$cand" &> /dev/null || continue
    read -r MAJ MIN <<< "$("$cand" -c 'import sys; print(sys.version_info.major, sys.version_info.minor)' 2>/dev/null)" || continue
    if [ "${MAJ:-0}" -eq 3 ] && [ "${MIN:-0}" -ge 10 ]; then
        PY="$cand"
        PYTHON_VERSION="${MAJ}.${MIN}"
        break
    fi
done

if [ -z "$PY" ]; then
    echo "ERROR: Python 3.10+ is required, but none was found."
    echo "       Install it from python.org or via Homebrew (e.g. 'brew install python@3.14'), then re-run."
    exit 1
fi

echo "Found Python ${PYTHON_VERSION} (${PY})"

# Create venv if it doesn't exist
if [ ! -d "${SCRIPT_DIR}/venv" ]; then
    echo "Creating Python virtual environment..."
    "$PY" -m venv "${SCRIPT_DIR}/venv"
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

# Set custom icon on .command launcher (resource fork gets stripped by git/editors)
COMMAND_FILE="${SCRIPT_DIR}/dbdude-v2t.command"
ICON_FILE="${SCRIPT_DIR}/icons/v2t.icns"
if [ -f "$COMMAND_FILE" ] && [ -f "$ICON_FILE" ]; then
    echo "Setting custom icon on dbdude-v2t.command..."
    "${SCRIPT_DIR}/venv/bin/python3" -c "
import Cocoa, sys
image = Cocoa.NSImage.alloc().initWithContentsOfFile_('${ICON_FILE}')
if image and Cocoa.NSWorkspace.sharedWorkspace().setIcon_forFile_options_(image, '${COMMAND_FILE}', 0):
    print('Icon set successfully.')
else:
    print('WARNING: Could not set icon.', file=sys.stderr)
" 2>&1 || echo "WARNING: Could not set icon (pyobjc issue)."
fi

# Check Globe/FN key setting (non-critical, never errors out)
FN_USAGE=$(defaults read com.apple.HIToolbox AppleFnUsageType 2>/dev/null || echo "unknown")
case "$FN_USAGE" in
    0) FN_LABEL="Change Input Source" ;;
    1) FN_LABEL="Show Emoji & Symbols" ;;
    2) FN_LABEL="Start Dictation" ;;
    3) FN_LABEL="Do Nothing" ;;
    *) FN_LABEL="Unknown ($FN_USAGE)" ;;
esac
if [ "$FN_USAGE" = "3" ]; then
    echo "Globe/FN key set to: $FN_LABEL"
else
    echo "WARNING: Globe/FN key may not be set to 'Do Nothing' (detected: $FN_LABEL)."
    echo "         If FN key is unreliable, check:"
    echo "         System Settings > Keyboard > Press Globe key to > Do Nothing"
fi
echo ""

echo "=== Setup Complete ==="
echo ""
echo "To run:"
echo "  cd ${SCRIPT_DIR}"
echo "  source venv/bin/activate"
echo "  python3 dbdude-v2t.py"
echo ""
