# dbdude-v2t Windows Setup
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).

# -WithR2T2: also install the optional R2T2 (Confucius4-R2T2) model stack
# (PyTorch CUDA build + qwen-asr, several GB). Whisper works without it.
param([switch]$WithR2T2)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $ScriptDir "venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

Write-Host "=== dbdude-v2t Windows Setup ===" -ForegroundColor Cyan

# Create venv if it doesn't exist
if (-not (Test-Path $venvPath)) {
    # Python on PATH is only needed to create the venv
    try {
        $pyVersion = python --version 2>&1
        Write-Host "Found $pyVersion"
    } catch {
        Write-Host "ERROR: Python not found. Install Python 3.10+ and ensure it is in your PATH." -ForegroundColor Red
        exit 1
    }
    Write-Host "Creating Python virtual environment..."
    python -m venv --copies $venvPath
} else {
    $pyVersion = & $venvPython --version 2>&1
    Write-Host "Using existing venv ($pyVersion)"
}

# Use the venv's Python explicitly for all pip operations to avoid
# conflicts with Anaconda or other Python installations on PATH
Write-Host "Installing Python packages (this may take several minutes)..."
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $ScriptDir "requirements.txt")

# Check for NVIDIA GPU
$hasNvidia = $false
try {
    nvidia-smi | Out-Null
    $hasNvidia = $true
} catch {}

if ($hasNvidia) {
    Write-Host ""
    Write-Host "NVIDIA GPU detected. Installing CUDA packages for GPU acceleration..."
    & $venvPython -m pip install --no-cache-dir nvidia-cudnn-cu12 nvidia-cublas-cu12
} else {
    Write-Host ""
    Write-Host "No NVIDIA GPU detected. Skipping CUDA packages (will use CPU mode)."
}

# Optional R2T2 stack. torch comes from the PyTorch cu128 index so it matches
# the CUDA 12 runtime libs faster-whisper already uses; the CPU-only torch is
# used when there is no NVIDIA GPU.
if ($WithR2T2) {
    Write-Host ""
    Write-Host "Installing R2T2 (Confucius4-R2T2) model stack..."
    if ($hasNvidia) {
        & $venvPython -m pip install torch --index-url https://download.pytorch.org/whl/cu128
    } else {
        & $venvPython -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    }
    & $venvPython -m pip install -r (Join-Path $ScriptDir "requirements-r2t2.txt")
    Write-Host "R2T2 weights (~4 GB) download from Hugging Face on first launch with model 'r2t2'."
}

# Create logs directory
$logsDir = Join-Path $env:USERPROFILE "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

# Create desktop shortcut
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "dbdude-v2t.lnk"
$batPath = Join-Path $ScriptDir "dbdude-v2t.bat"
$iconPath = Join-Path $ScriptDir "icons\v2t.ico"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $batPath
$shortcut.WorkingDirectory = $ScriptDir
if (Test-Path $iconPath) {
    $shortcut.IconLocation = $iconPath
}
$shortcut.Description = "dbdude-v2t - Voice to Text"
$shortcut.Save()
Write-Host "Desktop shortcut created."

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "To run: double-click the dbdude-v2t shortcut on your Desktop."
Write-Host ""
