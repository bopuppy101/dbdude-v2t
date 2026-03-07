# dbdude-v2t

Local, privacy-first voice-to-text for your desktop. Hold a hotkey to record, release to transcribe, and text appears at your cursor - in any application.

## Features

- **System-wide input** - types into any focused window (browser, editor, terminal, etc.)
- **Fully local** - runs Whisper models on your machine, no cloud, no API keys, your audio never leaves your computer
- **Multiple models** - choose from tiny to large-v3 depending on your hardware
- **GPU accelerated** - automatic CUDA detection on Windows/Ubuntu, Apple Silicon (MLX) on macOS
- **Custom mappings** - correct misheard words, expand abbreviations, add programming symbols
- **Mapping packs** - bundled Punctuation and Programmer packs for common replacements
- **System tray app** - runs in the background with status icons (idle/recording/transcribing)
- **Configurator GUI** - settings, model selection, audio device selection
- **Continuous mode** - toggle on for long-form dictation

## Platforms

| Platform | Hotkey | Text Output | AI Engine |
|----------|--------|-------------|-----------|
| **Windows** | Alt+Shift (hold) | AutoHotkey | faster-whisper (CPU/CUDA) |
| **macOS** | Fn (hold) | Quartz events | mlx-whisper (Apple Silicon) |
| **Ubuntu** | Alt+Shift (hold) | xdotool | faster-whisper (CPU/CUDA) |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Alt+Shift (hold/release) | Record / Stop & transcribe |
| Ctrl+Shift+Space | Toggle continuous mode |
| Ctrl+Shift+Q | Exit |

macOS uses Fn instead of Alt+Shift.

## Installation

**Requires Python 3.10 or later.** Verify your version:

```bash
python --version    # Windows
python3 --version   # macOS / Ubuntu
```

Each platform has a setup script that creates a Python virtual environment and installs all dependencies. The install downloads a significant number of packages including a Hugging Face Whisper model for speech recognition, so expect it to take several minutes depending on your internet connection.

### Windows

Open PowerShell in the project directory and run:

```powershell
cd windows
.\setup.ps1
```

If you get an execution policy error, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

To launch, double-click `windows\dbdude-v2t.bat` or pin it to your taskbar. You can also run manually:

```powershell
cd windows
.\venv\Scripts\python.exe dbdude-v2t.py
```

### macOS

```bash
cd macos
bash setup.bash
```

To launch, double-click `dbdude-v2t.command` or drag it to your Dock for quick access. You can also run manually:

```bash
cd macos
source venv/bin/activate
python3 dbdude-v2t.py
```

macOS will prompt for Accessibility and Microphone permissions on first use. Grant both for dbdude-v2t to function.

### Ubuntu

```bash
cd ubuntu
bash setup.bash
```

To launch:

```bash
cd ubuntu
./run-dbdude-v2t.bash
```

Or add an alias to `~/.bashrc` for quick access:

```bash
alias rv='/path/to/ubuntu/run-dbdude-v2t.bash'
```

A `dbdude-v2t.desktop` file is also included. To use it, update the paths inside the file and copy it to `~/.local/share/applications/`.

Note: Ubuntu requires `sudo` for keyboard input detection.

## License

[CC BY-NC 4.0](LICENSE) - Free for non-commercial use.

Copyright (c) 2025-2026 Michael Foster / DBDude Inc.
