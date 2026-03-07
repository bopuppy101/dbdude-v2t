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
| **Ubuntu** | Alt+Shift (hold) | xdotool | faster-whisper (CPU/CUDA) |
| **Windows** | Alt+Shift (hold) | AutoHotkey | faster-whisper (CPU/CUDA) |
| **macOS** | Fn (hold) | Quartz events | mlx-whisper (Apple Silicon) |

## Quick Start

Each platform has its own directory with a setup script:

```bash
# Ubuntu
cd ubuntu
bash setup.bash
./run-voice2text.bash

# macOS
cd macos
# See macos/docs/INSTALL.md

# Windows
cd windows
# Run voice2text.py with Python
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Alt+Shift (hold/release) | Record / Stop & transcribe |
| Ctrl+Shift+Space | Toggle continuous mode |
| Ctrl+Shift+Q | Exit |

macOS uses Fn instead of Alt+Shift.

## License

[CC BY-NC 4.0](LICENSE) - Free for non-commercial use.

Copyright (c) 2025-2026 Michael Foster / DBDude Inc.
