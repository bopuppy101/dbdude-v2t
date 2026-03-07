# Claude Code Orientation

## Current State

The Python virtual environment is set up and working. Core functionality has been tested.

## What's Done

1. **Virtual environment created** at `venv/` with all dependencies installed:
   - mlx-whisper, sounddevice, numpy, pynput, pystray, Pillow

2. **Microphone + transcription tested** - `test_mic.py` works:
   - Records for 15 seconds, transcribes with MLX Whisper
   - Output prefixed with `[Python output]` to distinguish from Wispr Flow

3. **Hotkey script created** - `test_hotkey.py`:
   - Uses Control+Shift (hold to record, release to transcribe)
   - Chose this hotkey to avoid conflict with Wispr Flow (which uses FN)

## What's Next

1. **Grant Accessibility permissions** to Terminal (or whatever app runs Claude Code):
   - System Preferences → Security & Privacy → Privacy → Accessibility
   - Add Terminal.app (or iTerm, VS Code, etc.)
   - Restart the terminal after granting permissions

2. **Test hotkey script** once permissions are granted:
   ```bash
   source venv/bin/activate
   python test_hotkey.py
   ```

3. **Continue building** - next features after hotkey works:
   - Text output to active window (AppleScript or pynput)
   - System tray icon
   - Main application structure

## Key Files

- `test_mic.py` - Simple 15-second record and transcribe test
- `test_hotkey.py` - Hold Control+Shift to record, release to transcribe
- `CLAUDE.md` - Project guidance for Claude Code
- `docs/macos-v2t-port-plan.md` - Full port plan from Windows version

## Remember

- Don't freeze requirements during development
- Prefix transcription output with `[Python output]` to distinguish from Wispr Flow
