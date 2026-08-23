---
summary: dbdude-v2t — Local, privacy-first voice-to-text desktop app: hold a hotkey to record, release to transcribe Whisper locally, and text appears at the cursor in any app
stack: Python 3.10+, Whisper (faster-whisper on Windows/Ubuntu, mlx-whisper on Apple Silicon); per-platform input (AutoHotkey, Quartz, xdotool); system-tray + configurator GUI
status: active — multi-platform product with a public website
---

# dbdude-v2t

A fully local, privacy-first voice-to-text utility. Hold a hotkey to record, release to transcribe via a local Whisper model, and the text is typed into whatever window is focused — no cloud, no API keys, audio never leaves the machine. Features include multiple model sizes, GPU acceleration, custom word/abbreviation mappings with bundled Punctuation and Programmer packs, a system-tray app, a configurator GUI, and a continuous dictation mode. Distributed under GPL-3.0-or-later (free and open source); website at https://dbdude-v2t.dbdude.net.

The repo is organized by platform — `windows/`, `macos/`, and `ubuntu/` — each containing its own `dbdude-v2t.py` entry point, `configurator_gui.py`, `mapping_rules_gui.py`, a setup script (`setup.ps1` / `setup.bash`) that builds a venv and installs dependencies, and launchers. Hotkeys and text-output mechanisms differ per platform (Alt+Shift via AutoHotkey on Windows, Fn via Quartz on macOS, Alt+Shift via xdotool on Ubuntu). Requires Python 3.10+.

**Full detail:** see this repo's `docs/`.
