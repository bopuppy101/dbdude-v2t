# dbdude-v2t — macOS Python venv and model setup

> **Updated 2026-04-17.** macOS audio capture was converted from `sounddevice` to `AVAudioEngine` via PyObjC in April 2026. The `sounddevice` dependency is still present because `configurator_gui.py` uses `sd.query_devices()` to list available input devices, but the main capture path in `dbdude-v2t.py` no longer uses it. See `docs/audio-capture-library-per-platform.md` and `macos/docs/av-audio-engine-implementation.md` for detail.

## Quick setup (via setup.bash)

From the repo root:

```bash
cd ~/git/dbdude-v2t/macos
./setup.bash
```

`setup.bash` verifies Python 3.10+ is installed, creates `macos/venv/`, installs everything from `macos/requirements.txt`, sets the custom icon on the `.command` launcher, and warns if the Globe/FN key is not set to "Do Nothing" in System Settings.

## Manual setup (what setup.bash does under the hood)

```bash
# Repo is at ~/git/dbdude-v2t
cd ~/git/dbdude-v2t/macos

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies from requirements.txt
pip install -r requirements.txt
```

Current dependencies (from `macos/requirements.txt`):

- `mlx-whisper` — Speech-to-text via Apple MLX (Metal GPU)
- `numpy` — Audio array handling
- `sounddevice` — Retained for `configurator_gui.py` device listing only; capture path no longer uses it
- `pynput` — Keyboard output (typing the transcribed text)
- `rumps` — Menu bar app framework
- `pyobjc-framework-Quartz` — Used for Cocoa (NSEvent) and AVFoundation (AVAudioEngine) bindings
- `PySide6` — UI for configurator and mapping/rules editors

`scipy` is not in requirements.txt but is pulled in transitively via `mlx-whisper`. It's used in `dbdude-v2t.py` for 48 kHz → 16 kHz resampling in `stop_recording` (`scipy.signal.resample_poly`).

## Python version

macOS builds have been pinned to **Python 3.12** because pyobjc 12.x is yanked from PyPI and pyobjc 11.x has compatibility issues with Python 3.13. See `project_macos_setup.md` in Claude memory for history.

## Model usage

```python
import mlx_whisper

result = mlx_whisper.transcribe(
    "audio.wav",
    path_or_hf_repo="mlx-community/whisper-small.en-mlx",
    condition_on_previous_text=False,
)
print(result["text"])
```

The model is loaded from a bundled directory if present (`Resources/models/whisper-<model>.en-mlx/`), otherwise downloaded from Hugging Face on first use.

## Verify FN key setting

Both `setup.bash` and `dbdude-v2t.py` check on startup:

```bash
defaults read com.apple.HIToolbox AppleFnUsageType
```

Expected value: `3` ("Do Nothing"). If not, the FN key detection may be unreliable — see `docs/macos-fn-key-setup.md` for the user-facing fix.
