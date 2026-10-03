# dbdude-v2t

**Website:** https://dbdude-v2t.dbdude.net/

Local, privacy-first voice-to-text for your desktop. Hold a hotkey to record, release to transcribe, and text appears at your cursor - in any application.

## Features

- **System-wide input** - types into any focused window (browser, editor, terminal, etc.)
- **Fully local** - runs Whisper models on your machine, no cloud, no API keys, your audio never leaves your computer
- **Multiple models** - choose from tiny to large-v3 depending on your hardware
- **GPU accelerated** - automatic CUDA detection on Windows/Ubuntu/Omarchy, Apple Silicon (MLX) on macOS
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
| **Ubuntu** | Alt+Shift (hold) | xdotool | faster-whisper (CPU/CUDA) |
| **Omarchy** (Arch + Hyprland) | Alt+Shift (hold) | ydotool | faster-whisper (CPU/CUDA) |

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
python3 --version   # macOS / Ubuntu / Omarchy
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

#### Optional: R2T2 model (experimental)

Windows can also run [Confucius4-R2T2](https://huggingface.co/netease-youdao/Confucius4-R2T2)
(see the Omarchy section below for what it is). Install the extra stack with `.\setup.ps1 -WithR2T2`,
then pick `r2t2` in the Configurator. An NVIDIA GPU is strongly recommended; the weights (about 4 GB)
download from Hugging Face on first launch. Whisper models are unaffected unless `r2t2` is selected.

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

#### Optional: R2T2 model (experimental)

macOS can also run [Confucius4-R2T2](https://huggingface.co/netease-youdao/Confucius4-R2T2)
(see the Omarchy section below for what it is) natively on Apple Silicon through `mlx-audio`, using a
community 4-bit MLX conversion. Install the extra stack with `bash setup.bash --with-r2t2`, then pick
`r2t2` in the Configurator. The weights (about 1.5 GB) download from Hugging Face on the first
transcription. Whisper models are unaffected unless `r2t2` is selected.

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

### Omarchy (Arch Linux + Hyprland)

```bash
cd omarchy
bash setup.bash
```

`setup.bash` installs `ydotool` via pacman, loads the `uinput` kernel module (persisted in
`/etc/modules-load.d/`), installs udev `uaccess` rules so your desktop login gets access to
`/dev/uinput` and `/dev/input/event*` without `sudo` or group changes, and enables the
`ydotool` user service. Sudo is needed once during setup only.

To launch:

```bash
cd omarchy
./run-dbdude-v2t.bash
```

Or add an alias to `~/.bashrc`:

```bash
alias rv='/path/to/omarchy/run-dbdude-v2t.bash'
```

The tray icon appears in the Omarchy bar's tray drawer. To keep it always visible, add it to the
tray's pinned list in `~/.config/omarchy/shell.json`:

```json
{ "id": "omarchy.tray", "pinned": ["dbdude-v2t.py"] }
```

#### Optional: R2T2 model (experimental)

The Omarchy dialect can also run [Confucius4-R2T2](https://huggingface.co/netease-youdao/Confucius4-R2T2),
NetEase Youdao's 2B-parameter Qwen3-ASR fine-tune, as an alternative to Whisper. It runs in
offline (whole-clip) mode through the `qwen-asr` transformers backend, so each push-to-talk
clip is transcribed as one unit, the same as with Whisper. Install the extra stack (PyTorch plus
`qwen-asr`, several GB), then pick `r2t2` in the Configurator or launch with `--model r2t2`:

```bash
cd omarchy
bash setup.bash --with-r2t2
./run-dbdude-v2t.bash --model r2t2
```

The weights (about 4 GB) download from Hugging Face on first use and are covered by NetEase's
Model Use License, not this project's GPL. An NVIDIA GPU is strongly recommended; CPU mode works
but is slow.

## License

[GPL-3.0-or-later](LICENSE) - Free and open source. You may use, modify, and redistribute it, including commercially; distributed versions must also be released under the GPL.

Copyright (c) 2025-2026 Michael Foster / DBDude Inc.
