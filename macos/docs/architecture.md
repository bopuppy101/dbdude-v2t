# dbdude-v2t macOS - Architecture

> **Last major update:** 2026-04-17. Key changes from the original Dec 2025 design:
> - **FN key detection** moved from `CGEventSourceFlagsState` polling (Quartz) to an NSEvent global monitor with a thread-safe flag read by a polling control loop (merged April 2026, branch `feature/event-based-transcription`).
> - **Audio capture** converted from `sounddevice`/PortAudio to `AVAudioEngine` + installed input tap via PyObjC (merged April 2026, branch `feature/avaudioengine`). This fixed the first-word drop and the stale-mic / 50% miss rate that kept trading places under the sounddevice path.

## Current Architecture

The app uses three main components running concurrently:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Main Thread                             │
│  rumps.App (menu bar) + UI Timer (polls ui_status_queue)        │
│  + NSEvent global monitor (fires on FN modifier changes)        │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ ui_status_queue (thread-safe)
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                    recording_control_worker                     │
│  Polls _fn_held flag every 20ms (flag set by NSEvent callback)  │
│  Controls recording flag, calls start/stop_recording            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ transcription_queue
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     transcription_worker                        │
│  Processes audio from queue, runs MLX Whisper, types result     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     AVAudioEngine (audio thread)                │
│  Runs continuously from app start. Input tap appends samples    │
│  to audio_chunks list only when recording flag is True.         │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. FN Key Detection — NSEvent Global Monitor

**Why:** `CGEventSourceFlagsState` polling (previous approach) had a macOS bug where the API would permanently block after rapid FN presses, requiring `pkill -9` to recover. Earlier, `CGEventTap` had silently stopped receiving events after a few minutes. NSEvent is stable when the user has "Press Globe key to" set to "Do Nothing" in System Settings (see `event-based-transcription-on-macos.md`).

**How:** Install an `NSEvent.addGlobalMonitorForEventsMatchingMask_handler_` monitor for `NSEventMaskFlagsChanged`. The callback flips a thread-safe `_fn_held` boolean; the `recording_control_worker` reads that flag every 20ms instead of calling a Quartz API.

```python
def _fn_flags_changed(event):
    global _fn_held
    fn_down = bool(event.modifierFlags() & NSFunctionKeyMask)
    with _fn_state_lock:
        _fn_held = fn_down

NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
    NSEventMaskFlagsChanged, _fn_flags_changed
)
```

**Trade-off:** Requires the user to disable the Globe key emoji shortcut in System Settings. Without that change, macOS intercepts FN events at the firmware level before any API can see them.

### 2. Audio Capture — AVAudioEngine (converted from sounddevice, April 2026)

**Why (history):** Three iterations have landed in this repo.

1. **Persistent `sounddevice` stream** — kept open with callback gated by `if recording:`. macOS powered down the idle mic and delivered near-silence on the next press (~50% miss rate).
2. **Per-recording `sounddevice` stream** (commit `1ad66f3`) — fresh `sd.InputStream` on each FN press. Solved the stale-mic issue but introduced a deterministic ~100–300ms first-word drop from CoreAudio mic warmup.
3. **`AVAudioEngine` + installed input tap** (April 2026, current). The engine pulls samples continuously from app startup to quit, so the mic stays powered (no stale-stream bug) and the tap fires with live audio on FN press (no warmup, first word captured).

**How:** An `AVAudioEngine` is created at startup. An input tap is installed on bus 0 at the native hardware format (48 kHz mono float32 on Apple Silicon). The tap callback extracts samples via `PyObjCPointer.pointerAsInteger` + ctypes, and appends them to `audio_chunks` **only when `recording` is True**. On FN release, `stop_recording` concatenates the chunks, resamples to 16 kHz with `scipy.signal.resample_poly`, and queues for mlx_whisper.

```python
def _audio_tap_callback(buffer, when):
    if not recording:
        return
    fcd = buffer.floatChannelData()
    addr = fcd.pointerAsInteger
    float_ptr_ptr = ctypes.cast(addr, POINTER(POINTER(c_float)))
    samples = np.ctypeslib.as_array(float_ptr_ptr[0], shape=(frame_length,)).copy()
    audio_chunks.append(samples)
```

**Trade-off:** PyObjC bridging is non-trivial — requires `objc.registerMetaDataForSelector` to declare the tap block signature and `pointerAsInteger` to extract the raw pointer from the PyObjC wrapper. See `av-audio-engine-implementation.md` for the full write-up.

### 3. Thread-Safe UI Updates

**Why:** `rumps` is built on AppKit, which requires all UI updates on the main thread. Calling `app.set_recording()` from background threads caused random hangs.

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
            self._apply_status(status, icon_path)

    def set_recording(self):
        ui_status_queue.put(("Recording...", ICON_RECORDING))
```

### 4. Non-Blocking Transcription

**Why:** Whisper transcription takes time. Blocking the recording control thread would cause missed recordings.

**How:** `stop_recording()` queues audio data and returns immediately. A separate `transcription_worker` thread processes the queue.

```python
def stop_recording():
    audio = np.concatenate(audio_chunks).flatten()
    # resample native 48k -> 16k
    audio = resample_poly(audio, TARGET_SAMPLE_RATE, int(native_sample_rate))
    transcription_queue.put((audio, duration))

def transcription_worker():
    while not shutdown_event.is_set():
        audio, duration = transcription_queue.get(timeout=0.5)
        result = mlx_whisper.transcribe(audio, ...)
        typer.type(result['text'])
```

## Thread Summary

| Thread | Purpose | Blocking? |
|--------|---------|-----------|
| Main | rumps app, UI updates via timer, NSEvent monitor callbacks | No (event loop) |
| recording_control_worker | Poll `_fn_held` flag, control recording | No (sleeps 20ms) |
| transcription_worker | Run Whisper, type output | Yes (but isolated) |
| AVAudioEngine audio thread | Pull mic samples, fire tap callback | Short-lived per buffer |

## What We Tried and Rejected

### FN key detection (chronological)
1. **pynput `Listener`** — Dropped release events after extended use.
2. **CGEventTap (listen-only)** — Silently stopped receiving events after minutes. Re-enable on timeout and watchdog didn't help.
3. **`CGEventSourceFlagsState` polling** — macOS bug where the API permanently blocks after rapid FN presses. Required `pkill -9` to recover.
4. **NSEvent global monitor (current)** — Stable *when* the Globe key emoji shortcut is disabled in System Settings.

See `fn-key-detection-approaches.md` for the full write-up.

### Audio capture (chronological)
1. **Persistent sounddevice stream, callback-gated** — 50% recordings captured near-silence due to idle-mic power-down.
2. **Per-recording sounddevice stream** — Fixed stale-mic. Introduced ~100-300ms first-word drop from CoreAudio warmup.
3. **AVAudioEngine with continuous input tap (current)** — Fixes both. Requires PyObjC bridging.

See `av-audio-engine-implementation.md` for the full write-up.

### Direct UI updates from background threads
- **Problem:** Random hangs due to AppKit thread-safety violations.
- **Solution:** Queue + Timer pattern.

## Files

- `dbdude-v2t.py` — Main application (all logic in one file)
- `configurator_gui.py` — Settings GUI (still uses sounddevice just to list available input devices via `sd.query_devices()`)
- `icons/` — Menu bar icons (ready, recording, transcribing states)
- `docs/` — This documentation

## Dependencies

- `mlx-whisper` — Speech-to-text on Apple Silicon
- `numpy` — Audio array handling
- `scipy` — 48 kHz → 16 kHz resampling in `stop_recording` (transitively present via mlx-whisper)
- `pyobjc` + `pyobjc-framework-Quartz` — Cocoa / AVFoundation bindings for NSEvent monitor and AVAudioEngine
- `rumps` — Menu bar app framework
- `pynput` — Keyboard output (typing transcribed text)
- `sounddevice` — Retained for `configurator_gui.py` device listing only; not used in the capture path anymore
