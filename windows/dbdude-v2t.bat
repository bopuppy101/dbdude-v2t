@echo off
REM Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).
REM Double-click to launch dbdude-v2t, or pin to taskbar for quick access.

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo ERROR: venv not found. Run setup.ps1 first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python dbdude-v2t.py %*
