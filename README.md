# dbdude-v2t

**Website:** https://dbdude-v2t.dbdude.net/

Local, privacy-first voice-to-text for your desktop. Hold a hotkey to record, release to transcribe, and text appears at your cursor - in any application.

## Features

- **System-wide input** - types into any focused window (browser, editor, terminal, etc.)
- **Fully local** - runs Whisper models on your machine, no cloud, no API keys, your audio never leaves your computer
- **Multiple models** - choose from tiny to large-v3 depending on your hardware
- **GPU accelerated** - CUDA detection on Windows, X11 Ubuntu, and Omarchy; Apple Silicon (MLX) on macOS. The Ubuntu 26.04 launcher currently uses CPU
- **Custom mappings** - correct misheard words, expand abbreviations, add programming symbols
- **Mapping packs** - bundled Punctuation and Programmer packs for common replacements
- **System tray app** - runs in the background with status icons (idle/recording/transcribing)
- **Configurator GUI** - settings, model selection, audio device selection
- **Continuous mode** - toggle on for long-form dictation

### Dictation punctuation

All platform versions omit the automatic final period for a single sentence,
regardless of its length. Multiple sentences keep punctuation and have their
sentence starts capitalized. Sentence detection uses the recognizer's punctuation
and accounts for common abbreviations; ambiguous abbreviations may still need correction.
Question marks and exclamation marks are preserved.

Enable the **Punctuation** mapping pack, or add individual custom mappings, to use
`question mark` → `?`, `exclamation point` / `bang` → `!`, and `dot` → `.`.
Spoken `dot` preserves an explicitly requested period even for a single sentence.
Punctuation attached by the recognizer to a spoken command is replaced along with
the command, so `bang!` produces `!`; `bang bang` still produces `!!`.
Windows and macOS custom formatting rules continue to run after sentence formatting.

Restart the app after updating the Python code. Mapping-only edits can be loaded
with **Reload Mapping Files**.

## Platforms

| Platform | Hotkey | Text Output | AI Engine |
|----------|--------|-------------|-----------|
| **Windows** | Alt+Shift (hold) | AutoHotkey | faster-whisper (CPU/CUDA) |
| **macOS** | Fn (hold) | Quartz events | mlx-whisper (Apple Silicon) |
| **Ubuntu (X11)** | Alt+Shift (hold) | xdotool | faster-whisper (CPU/CUDA) |
| **Ubuntu 26.04 (Wayland)** | Alt+Shift (hold) | ydotool | faster-whisper (launcher uses CPU) |
| **Omarchy** (Arch + Hyprland) | Alt+Shift (hold) | ydotool | faster-whisper (CPU/CUDA) |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Alt+Shift (hold/release) | Record / Stop & transcribe |
| Ctrl+Shift+Space | Toggle continuous mode |
| Ctrl+Shift+Q | Exit |

macOS uses Fn instead of Alt+Shift.

## Installation

Choose your platform and preferred level of detail. Each guide is self-contained.

**macOS (Apple Silicon)**

- [docs/installation-macos-beginners.md](docs/installation-macos-beginners.md) — step-by-step installation, first dictation, updates, and troubleshooting.
- [docs/installation-macos-technical.md](docs/installation-macos-technical.md) — commands, dependencies, models, permissions, updates, and diagnostics.

**Windows**

- [docs/installation-windows-beginners.md](docs/installation-windows-beginners.md) — step-by-step installation, first dictation, updates, and troubleshooting.
- [docs/installation-windows-technical.md](docs/installation-windows-technical.md) — commands, dependencies, models, permissions, updates, and diagnostics.

**Ubuntu with X11/Xorg**

- [docs/installation-ubuntu-x11-beginners.md](docs/installation-ubuntu-x11-beginners.md) — step-by-step installation, first dictation, updates, and troubleshooting.
- [docs/installation-ubuntu-x11-technical.md](docs/installation-ubuntu-x11-technical.md) — commands, dependencies, models, permissions, updates, and diagnostics.

**Ubuntu 26.04 with Wayland**

- [docs/installation-ubuntu-26-04-wayland-beginners.md](docs/installation-ubuntu-26-04-wayland-beginners.md) — step-by-step installation, first dictation, updates, and troubleshooting.
- [docs/installation-ubuntu-26-04-wayland-technical.md](docs/installation-ubuntu-26-04-wayland-technical.md) — commands, dependencies, models, permissions, updates, and diagnostics.

**Omarchy (Arch Linux + Hyprland)**

- [docs/installation-omarchy-beginners.md](docs/installation-omarchy-beginners.md) — step-by-step installation, first dictation, updates, and troubleshooting.
- [docs/installation-omarchy-technical.md](docs/installation-omarchy-technical.md) — commands, dependencies, models, permissions, updates, and diagnostics.

## License

[GPL-3.0-or-later](LICENSE) - Free and open source. You may use, modify, and redistribute it, including commercially; distributed versions must also be released under the GPL.

Copyright (c) 2025-2026 Michael Foster / DBDude Inc.
