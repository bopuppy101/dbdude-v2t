# Feature: FN Poll Timeout

**Branch:** `feature/fn-poll-timeout`

## Problem

There is a known macOS bug where `CGEventSourceFlagsState()` — the Quartz call we use to detect whether the FN key is held down — can block indefinitely. This is triggered by rapid FN key presses. When it blocks, the entire polling loop freezes, and V2T stops responding to key input. The app appears hung even though the menu bar icon is still visible.

## Fix

The polling loop (`recording_control_worker`) no longer calls `CGEventSourceFlagsState` directly on its own thread. Instead, each poll cycle:

1. Spawns a short-lived daemon thread to make the Quartz call
2. Waits up to **200ms** for it to return
3. If the call returns in time, uses the result normally
4. If the call is stuck, logs a warning and skips that cycle — the loop stays alive and retries on the next 20ms tick

This means a blocked Quartz call can no longer hang the app. The worst case is a skipped poll cycle (imperceptible to the user).

## Additional Changes

### Debug Logging While Recording
Every ~2 seconds during an active recording, a status line is printed confirming the polling loop is alive, the current FN state, and the poll count. This helps diagnose any future issues.

### Optional File Logging
If `"log": true` is set in the V2T settings file, stdout and stderr are teed to `~/logs/dbdude-v2t.log`. This allows capturing logs from the menu bar app which otherwise has no visible terminal output.

## Files Changed

- **`macos/dbdude-v2t.py`** — poll timeout wrapper, debug logging, file logging
- **`macos/configurator_gui.py`** — (related settings changes)
- **`macos/TROUBLESHOOTING-FN-HANG.md`** — user-facing troubleshooting guide for the FN hang issue
