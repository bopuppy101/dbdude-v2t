# Voice2Text macOS - Architecture (2025-12-20)

## Current Architecture

The app uses three main components running concurrently:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Main Thread                              │
│  rumps.App (menu bar) + UI Timer (polls ui_status_queue)        │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ ui_status_queue (thread-safe)
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                    recording_control_worker                      │
│  Polls CGEventSourceFlagsState every 20ms for Fn key state      │
│  Controls recording flag, calls start/stop_recording            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ transcription_queue
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     transcription_worker                         │
│  Processes audio from queue, runs MLX Whisper, types result     │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Direct Key State Polling (Not CGEventTap)

**Why:** CGEventTap was unreliable - it would silently stop receiving events after a period of use, causing the app to become unresponsive to keyboard input.

**How:** Poll `CGEventSourceFlagsState(kCGEventSourceStateHIDSystemState)` every 20ms to read the current modifier key state directly.

```python
from Quartz import (
    CGEventSourceFlagsState, kCGEventSourceStateHIDSystemState,
    kCGEventFlagMaskSecondaryFn
)

def recording_control_worker():
    while not shutdown_event.is_set():
        flags = CGEventSourceFlagsState(kCGEventSourceStateHIDSystemState)
        fn_held = bool(flags & kCGEventFlagMaskSecondaryFn)

        if fn_held and not recording:
            start_recording()
        elif not fn_held and recording:
            stop_recording()

        time.sleep(0.02)  # 20ms polling interval
```

**Trade-off:** Microphone stays active continuously (shows in menu bar), but this is much more reliable than event-based approaches.

### 2. Persistent Audio Stream

**Why:** Creating and destroying `sounddevice.InputStream` on each recording caused PortAudio hangs, especially with rapid start/stop cycles.

**How:** Create the stream once on first recording, keep it running forever. The `recording` flag controls whether `audio_callback` captures data.

```python
def audio_callback(indata, frames, time, status):
    if recording:  # Only capture when recording flag is True
        audio_data.append(indata.copy())

def start_recording():
    global stream
    audio_data.clear()
    if stream is None:
        stream = sd.InputStream(...)
        stream.start()
    # Stream stays running even when not recording

def stop_recording():
    # DON'T close the stream - just stop capturing
    # Stream keeps running, audio_callback just ignores data
```

**Trade-off:** Microphone is always "in use" from the OS perspective. This is fine for a voice transcription app.

### 3. Thread-Safe UI Updates

**Why:** `rumps` is built on AppKit, which requires all UI updates to happen on the main thread. Calling `app.set_recording()` from background threads caused random hangs.

**How:** Background threads put status updates on a `queue.Queue`. A `rumps.Timer` on the main thread polls the queue every 50ms and applies updates.

```python
ui_status_queue = queue.Queue()

class V2TApp(rumps.App):
    def __init__(self):
        self.ui_timer = rumps.Timer(self._process_ui_queue, 0.05)
        self.ui_timer.start()

    def _process_ui_queue(self, _):
        while not ui_status_queue.empty():
            status, icon_path = ui_status_queue.get_nowait()
            self._apply_status(status, icon_path)  # Safe: runs on main thread

    def set_recording(self):
        # Thread-safe: just queues the update
        ui_status_queue.put(("Recording...", ICON_RECORDING))
```

### 4. Non-Blocking Transcription

**Why:** Whisper transcription takes time. Blocking the recording control thread would cause missed recordings.

**How:** `stop_recording()` queues audio data and returns immediately. A separate `transcription_worker` thread processes the queue.

```python
def stop_recording():
    audio = np.concatenate(audio_data).flatten()
    transcription_queue.put((audio, duration))  # Returns immediately

def transcription_worker():
    while True:
        audio, duration = transcription_queue.get()
        result = mlx_whisper.transcribe(audio, ...)
        typer.type(result['text'])
```

## Thread Summary

| Thread | Purpose | Blocking? |
|--------|---------|-----------|
| Main | rumps app, UI updates via timer | No (event loop) |
| recording_control_worker | Poll Fn key, control recording | No (sleeps 20ms) |
| transcription_worker | Run Whisper, type output | Yes (but isolated) |

## What We Tried and Rejected

### CGEventTap (Event-Based Keyboard Monitoring)
- **Problem:** Would silently stop receiving events after minutes of use
- **Attempted fixes:** Re-enable on timeout, watchdog timer, minimal callback
- **Result:** Still unreliable - direct polling is simpler and works

### Create/Destroy Audio Stream Per Recording
- **Problem:** `stream.stop()` and `stream.abort()` would hang after rapid start/stop cycles
- **Attempted fixes:** Use `abort()` instead of `stop()`, add timeouts
- **Result:** Still hung - keeping stream persistent eliminates the issue

### Direct UI Updates from Background Threads
- **Problem:** Random hangs due to AppKit thread-safety violations
- **Solution:** Queue + Timer pattern (see above)

## Files

- `voice2text-2026-macos.py` - Main application (all logic in one file)
- `icons/` - Menu bar icons (ready, recording, transcribing states)
- `docs/` - This documentation

## Dependencies

- `mlx-whisper` - Speech-to-text on Apple Silicon
- `sounddevice` - Audio capture
- `rumps` - Menu bar app framework
- `pynput` - Keyboard output (typing transcribed text)
- `pyobjc-framework-Quartz` - For `CGEventSourceFlagsState`
