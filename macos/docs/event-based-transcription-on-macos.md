# Event-Based Transcription on macOS (feature/event-based-transcription)

## Branch
`feature/event-based-transcription` off `develop`

## Problem
The macOS version used `CGEventSourceFlagsState` (Quartz API) to poll FN key state every 20ms. This API has a macOS bug where it permanently blocks after rapid FN presses, causing:

1. **Stuck recording** — FN release not detected, app stays in recording state
2. **Full hang every 15-30 minutes** — the polling thread blocks permanently, requiring `pkill -9` to recover

A previous attempt to wrap the API call in a threaded 200ms timeout (commit `6dd2d01`) was reverted (commit `aa50071`) because once the bug triggers, all new calls to the API also block permanently — spawning timeout threads just accumulates hung threads.

## Solution
Replaced `CGEventSourceFlagsState` polling with an **NSEvent global monitor** using the same hybrid pattern as the stable Windows version:

1. **NSEvent callback** (`_fn_flags_changed`) receives `NSEventMaskFlagsChanged` events from macOS and flips a thread-safe `_fn_held` boolean (protected by `_fn_state_lock`)
2. **Polling loop** (`recording_control_worker`) reads `_fn_held` every 20ms and starts/stops recording — identical structure to before, just reads a flag instead of calling the Quartz API
3. **Monitor installed on main thread** via `setup_fn_monitor()` called from `V2TApp.__init__()` — required because NSEvent monitors need the NSApplication run loop

## What changed in `macos/dbdude-v2t.py`
- **Import**: `Quartz.CGEventSourceFlagsState` replaced with `Cocoa.NSEvent`, `NSEventMaskFlagsChanged`, `NSFunctionKeyMask`
- **New globals**: `_fn_state_lock` (threading.Lock), `_fn_held` (bool)
- **New function**: `_fn_flags_changed(event)` — NSEvent callback, only flips `_fn_held`
- **New function**: `setup_fn_monitor()` — installs the global monitor
- **Modified**: `recording_control_worker()` — reads `_fn_held` with lock instead of calling `CGEventSourceFlagsState`
- **Modified**: `V2TApp.__init__()` — calls `setup_fn_monitor()` after timer setup

## Why this pattern (hybrid event + polling)
- **Event-driven key detection** avoids the Quartz API bug entirely
- **Polling loop for recording control** keeps the recording start/stop logic simple and sequential, avoiding the bugs that occurred in a previous attempt to go fully event-driven
- **Same architecture as Windows** (`keyboard.on_press_key`/`on_release_key` callbacks set flags, main loop reads them) which has been stable

## Testing
Run for 1-2 weeks of heavy transcription use. Watch for:
- Stuck recordings (FN release not detected)
- Full hangs (process becomes unresponsive)
- Missed recordings or double transcriptions

If stable, merge to `develop`. If not, `git checkout develop` to revert.

## Related commits
- `6dd2d01` — Added (broken) threaded timeout workaround
- `aa50071` — Reverted timeout workaround, noted NSEvent as proper fix
- `1ad66f3` — Fixed stale audio stream (separate issue, still in place)
