#!/usr/bin/env bash
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.
# Double-click to launch dbdude-v2t, or drag to Dock for quick access.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "${SCRIPT_DIR}/venv" ]; then
    echo "ERROR: venv not found. Run setup.bash first."
    echo "Press any key to close..."
    read -n 1
    exit 1
fi

pkill -9 -f "dbdude-v2t.py" 2>/dev/null

source "${SCRIPT_DIR}/venv/bin/activate"
python3 "${SCRIPT_DIR}/dbdude-v2t.py" "$@"
