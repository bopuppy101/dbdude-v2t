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

## Using a shared speech server

On Omarchy, macOS and Windows, V2T can send each clip to a speech server instead
of loading its own Whisper model, for example `dbdude-tts serve` from dbdude-talk
running on another machine. The `--speech-server` switch picks the server for one run:

```bash
./run-dbdude-v2t.bash --speech-server 192.168.1.16
```

The examples below use `rv`, a shell alias for your platform's start command
(on Omarchy, `omarchy/run-dbdude-v2t.bash`):

```bash
rv --speech-server 192.168.1.16          # host or IP address; port 8880 is used
rv --speech-server 192.168.1.16:9000     # host:port
rv --speech-server http://192.168.1.16:8880   # full URL
rv --speech-server local                 # this machine's own server, http://127.0.0.1:8880
alias rvs='rv --speech-server 192.168.1.16'
```

A hostname such as `r16` works wherever that name resolves.

- The switch applies to that run only and is not saved.
- Without it, V2T uses `transcribe_url` from `settings.json`
  (`~/.dbdude-v2t/` on Omarchy and Windows, `~/Library/Application Support/dbdude-v2t/`
  on macOS). With neither, it loads its own model as usual.
- No environment variable is read for the server address.
- The `r2t2` model ignores the server and runs locally.

At startup V2T asks the server which model it runs and prints it:

```
INFO: Using shared transcription server http://192.168.1.16:8880 (large-v3-turbo, cuda, float16); local model not loaded
```

(macOS prints the same details on a line starting `Model: shared transcription server`.)
On Omarchy and macOS each clip also logs which one transcribed it:

```
INFO: Transcribed via server at http://192.168.1.16:8880 in 0.41s (3.20s audio)
INFO: Transcribed via local server (http://127.0.0.1:8880) in 0.38s (3.20s audio)
INFO: Transcribed locally (small, cpu) in 1.92s (3.20s audio)
```

macOS prints these without the `INFO:` prefix, and its local line reads
`Transcribed locally (small)`. The model names and times above are examples.

If the server can't be reached, V2T still starts. It prints a warning, suggests
starting without `--speech-server`, and transcribes each clip with a local `small`
model until the server answers; every clip tries the server first.

See [docs/installation-omarchy-technical.md](docs/installation-omarchy-technical.md)
for the `transcribe_url` setting.

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
