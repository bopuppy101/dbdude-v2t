# Troubleshooting: Fn Key Hang on macOS

## Problem
dbdude-v2t occasionally gets stuck in "Recording" (green icon) and never stops.
The `CGEventSourceFlagsState` API reports Fn as held even after release.

Observed on: MacBook Pro M2 32GB, macOS Tahoe 26.3, Python 3.11.7 in venv.
Not observed on: MacBook Pro with macOS Tahoe 26.4, Python 3.12.13 in venv.

## Step 1: Upgrade macOS to 26.4
Already in progress. Reboot after update completes and test.

If the hang stops, done. If not, continue to Step 2.

## Step 2: Rebuild venv with Python 3.12

### Install Python 3.12
```bash
brew install python@3.12
```

Verify it installed:
```bash
python3.12 --version
```

### Delete old venv and rebuild
```bash
cd /Users/mike/git/dbdude-v2t/macos
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
```

### Verify
```bash
source venv/bin/activate
python3 --version
# Should show 3.12.x
```

### Test
Launch dbdude-v2t and try to reproduce the hang.

## Step 3: Compare package versions (if still hanging)
On this machine:
```bash
cd /Users/mike/git/dbdude-v2t/macos
source venv/bin/activate
pip list
```

On the working machine, run the same and compare versions, especially:
- `pyobjc-framework-Quartz` (provides CGEventSourceFlagsState)
- `sounddevice`
- `pyobjc-core`

## Notes
- Logging is enabled. Check `~/logs/dbdude-v2t.log` for poll debug messages.
- Fn key is set to "Show Emoji & Symbols" on both machines — potential conflict with macOS intercepting the key-up event.
- Diagnostic poll logging is active in `dbdude-v2t.py` (prints every ~2s while recording).
