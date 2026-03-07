# macOS Port Plan: Voice2Text → macos-v2t

## Overview

Port the Windows Voice2Text application to macOS, replacing Windows-specific components with macOS equivalents while preserving business logic, text processing, and licensing infrastructure.

---

## Phase 1: Core Infrastructure Changes

| Component | Windows (Current) | macOS (Target) | Effort |
|-----------|-------------------|----------------|--------|
| **Speech Engine** | `faster_whisper` + CTranslate2/CUDA | `mlx_whisper` + Metal | Medium |
| **Keyboard Hooks** | `keyboard` library | `pynput` library | Medium |
| **Text Output** | AutoHotkey (`type_text.exe`) | AppleScript or `pynput` | Low |
| **System Tray** | `pystray` + Windows icons | `pystray` + macOS icons | Low |
| **Console Mgmt** | `ctypes.windll` | Not needed (Terminal behavior) | Remove |
| **Machine Fingerprint** | WMIC commands | `ioreg` / system_profiler | Low |
| **Audio Capture** | `sounddevice` | `sounddevice` (unchanged) | None |

---

## Phase 2: File-by-File Changes

### Keep As-Is (minor tweaks)

- Licensing infrastructure (API calls, config encryption)
- Text processing (email detection, mappings, rules, hallucination filtering)
- Settings persistence (JSON config)
- GUI (tkinter works on macOS)
- Logging

### Replace Entirely

- `keyboard` → `pynput` for hotkey detection
- `type_text.exe` (AutoHotkey) → AppleScript `osascript` or `pynput.keyboard.Controller`
- Console show/hide functions → Remove (not applicable on macOS)
- Machine fingerprint → Use `ioreg` for hardware IDs

### Modify

- Model loading: `WhisperModel()` → `mlx_whisper.transcribe()`
- GPU detection: `ctranslate2.get_cuda_device_count()` → Always Metal on Apple Silicon
- Path handling: `%APPDATA%` → `~/Library/Application Support/Voice2Text`

---

## Phase 3: Implementation Steps

### Step 1: Create Project Structure

```
~/git/macos-v2t/
├── venv/
├── voice2text_macos.py      # Main script
├── icons/
│   ├── v2t.icns             # macOS icon format
│   ├── v2t_recording.icns
│   └── v2t_transcribing.icns
├── maps/
│   └── packs/               # Copy from Windows
├── help/                    # Copy from Windows
└── requirements.txt
```

### Step 2: Implement Keyboard Handling with pynput

```python
from pynput import keyboard

# Track modifier state
alt_pressed = False
shift_pressed = False

def on_press(key):
    global alt_pressed, shift_pressed
    if key == keyboard.Key.alt:
        alt_pressed = True
    elif key == keyboard.Key.shift:
        shift_pressed = True

def on_release(key):
    global alt_pressed, shift_pressed
    if key == keyboard.Key.alt:
        alt_pressed = False
    elif key == keyboard.Key.shift:
        shift_pressed = False

# Start listener
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()
```

### Step 3: Implement Text Output

```python
import subprocess

def type_text_macos(text):
    """Type text using AppleScript."""
    # Escape for AppleScript
    escaped = text.replace('\\', '\\\\').replace('"', '\\"')
    script = f'tell application "System Events" to keystroke "{escaped}"'
    subprocess.run(['osascript', '-e', script], check=True)
```

### Step 4: Implement MLX Whisper Transcription

```python
import mlx_whisper

def transcribe_audio(audio_np, model_path="mlx-community/whisper-medium.en-mlx"):
    result = mlx_whisper.transcribe(
        audio_np,
        path_or_hf_repo=model_path,
        language="en"
    )
    return result["text"]
```

### Step 5: Implement macOS Machine Fingerprint

```python
import subprocess
import hashlib
import platform

def get_machine_fingerprint_macos():
    """Generate unique machine fingerprint from macOS hardware IDs."""
    try:
        result = subprocess.run(
            ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
            capture_output=True, text=True
        )
        # Extract IOPlatformUUID
        for line in result.stdout.split('\n'):
            if 'IOPlatformUUID' in line:
                uuid = line.split('"')[-2]
                return f"sha256:{hashlib.sha256(uuid.encode()).hexdigest()}"
    except Exception:
        pass
    return f"node:{platform.node()}"
```

### Step 6: Update Paths for macOS

```python
from pathlib import Path
import sys

def get_user_data_dir():
    """Get path to user data directory."""
    if sys.platform == 'darwin':
        return Path.home() / "Library" / "Application Support" / "Voice2Text"
    elif sys.platform == 'win32':
        appdata = os.environ.get('APPDATA', '')
        if appdata:
            return Path(appdata) / "Voice2Text"
    # Fallback
    return Path.home() / ".voice2text"
```

---

## Phase 4: Testing Checklist

- [ ] Virtual environment setup works
- [ ] MLX Whisper loads model and transcribes
- [ ] Audio capture from microphone works
- [ ] Hotkeys (Option+Shift) trigger recording
- [ ] Text output types into active application
- [ ] System tray icon appears and menus work
- [ ] Licensing validates against server
- [ ] Custom mappings load and apply
- [ ] Logging works to ~/logs
- [ ] Nuitka compilation produces working .app

---

## Phase 5: Nuitka Build Command (macOS)

```bash
python -m nuitka \
    --standalone \
    --macos-create-app-bundle \
    --macos-app-icon=icons/v2t.icns \
    --include-data-dir=maps=maps \
    --include-data-dir=help=help \
    --include-data-dir=icons=icons \
    --enable-plugin=tk-inter \
    voice2text_macos.py
```

---

## Phase 6: Dependencies (requirements.txt)

```
mlx-whisper
sounddevice
numpy
pynput
pystray
Pillow
```

---

## Estimated Effort

| Phase | Time |
|-------|------|
| Setup & dependencies | 30 min |
| Core port (transcription, keyboard, output) | 2-3 hours |
| GUI & systray adjustments | 1 hour |
| Testing & debugging | 1-2 hours |
| Nuitka packaging | 1 hour |
| **Total** | **5-7 hours** |

---

## Questions Before Proceeding

1. **Hotkey choice**: On macOS, Alt is called "Option". Keep Option+Shift, or prefer Cmd+Shift?

2. **Model bundling**: Bundle the MLX model in the .app, or download on first run like Windows?

3. **Text output method**: AppleScript (`osascript`) is reliable but slightly slower. `pynput` is faster but may need Accessibility permissions. Preference?

---

## Notes

- macOS requires Accessibility permissions for keyboard monitoring and text injection
- First run will prompt user to grant permissions in System Preferences → Security & Privacy → Privacy → Accessibility
- MLX models are downloaded from Hugging Face on first use and cached in `~/.cache/huggingface/`
- System tray on macOS appears in the menu bar (top right)
