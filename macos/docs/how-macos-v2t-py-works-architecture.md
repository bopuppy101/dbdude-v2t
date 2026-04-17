# How It Works

> **Converted from sounddevice/PortAudio to AVAudioEngine on macOS, April 2026.** See `av-audio-engine-implementation.md` for the detailed writeup and `architecture.md` for the full current architecture.

## The Three Workers (plus one)

### 1. Main Thread (rumps + NSEvent monitor)
- `rumps` is a library that puts an icon in your menu bar (the little colored dot)
- It runs a loop waiting for you to click the menu
- macOS rule: only this thread can change the icon/menu — if other threads try, the app freezes
- Also hosts the **NSEvent global monitor** that fires whenever any modifier key changes state (Fn, Shift, Ctrl, Cmd, Option). Its callback just flips a `_fn_held` boolean — it doesn't do any work.

### 2. Recording Control Worker (background thread)
- Runs a simple loop every 20ms: "Is the `_fn_held` flag True right now?"
- The flag is set by the NSEvent callback on the main thread; this worker just reads it under a lock.
- If Fn just got pressed → start capturing audio (flip `recording = True`)
- If Fn just got released → stop capturing, resample, send audio to transcription

### 3. Transcription Worker (background thread)
- Waits for audio to appear in a queue
- Runs Whisper (the AI speech-to-text model) on the audio
- Types the result into whatever app is focused

### 4. AVAudioEngine audio thread (managed by the framework)
- AVAudioEngine owns a high-priority audio thread we don't create
- Our installed input tap callback fires on that thread every few milliseconds with a chunk of mic samples
- The callback checks `recording`; if True, extracts the samples and appends them to a list. That's it — no resampling, no transcription on the audio thread.

## The Key Insights

### Why event-driven FN detection now, instead of polling?
The doc used to say polling was more reliable than events. That was true for `CGEventTap` but *not* for the Quartz `CGEventSourceFlagsState` polling API we replaced it with — that API had its own macOS bug where it would permanently block after rapid FN presses, requiring a `pkill -9` to recover. The NSEvent global monitor gives us event-driven detection that's actually reliable **when** the user has disabled the Globe key emoji shortcut in System Settings. (Without that setting, macOS intercepts Fn at the firmware level before any API can see it.)

### Why keep the mic running — and why AVAudioEngine instead of sounddevice?
This one has gone through three versions:

1. **Persistent sounddevice stream (old):** stream stayed open, callback gated by `if recording:`. macOS decided we weren't actually consuming audio and powered the mic down. About half of recordings came back as near-silence.
2. **Per-recording sounddevice stream (commit `1ad66f3`):** fresh stream on every FN press. Fixed the stale mic, but every recording lost its first word to the ~100–300ms CoreAudio mic warmup.
3. **AVAudioEngine with input tap (April 2026, current):** Apple's native audio framework pulls samples continuously from app start to quit. The mic stays powered because the framework is always the consumer. The tap callback fires immediately on FN press — no warmup, first word captured. Same library is what Wispr Flow and the open-source `sebsto/wispr` use.

### Why the UI queue?
When the recording worker wants to change the icon to "recording", it can't touch the UI directly (macOS will freeze). So it puts a message in a queue. The main thread checks the queue 20 times per second and applies the changes itself.

## Data Flow

```
You press Fn
    ↓
NSEvent monitor fires → _fn_held = True
    ↓
Recording worker reads the flag (polling every 20ms)
    ↓
Sets recording=True; AVAudioEngine tap callback now appends samples
    ↓
You release Fn
    ↓
NSEvent monitor fires → _fn_held = False
    ↓
Recording worker notices → recording=False; runs stop_recording()
    ↓
stop_recording() concatenates samples, resamples 48kHz→16kHz, queues audio
    ↓
Transcription worker picks it up
    ↓
Whisper converts speech → text
    ↓
pynput types the text into your active app
```

## What Fixed the Hangs

We went through several architectural iterations before landing on something stable. Here's what went wrong and how it's fixed today.

### 1. FN key detection: CGEventTap → CGEventSourceFlagsState polling → NSEvent monitor

**CGEventTap (original):** Register a callback, the OS calls it on keypresses. Professional apps like iTerm2 do this. Ours would silently stop delivering events after a while — the app would keep running but Fn would do nothing.

**CGEventSourceFlagsState polling:** Moved to reading the current modifier-key state from a Quartz API every 20ms. Simpler, but this API itself had a macOS bug where rapid Fn presses would cause it to block *permanently*. Required `pkill -9` to recover.

**NSEvent global monitor (April 2026, current):** Installed on the main thread via `NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(NSEventMaskFlagsChanged, ...)`. The callback is short — just flips `_fn_held`. The `recording_control_worker` reads that flag. No Quartz APIs involved, no hangs observed under rapid tapping.

**Caveat:** requires the user to set "Press 🌐 key to" to "Do Nothing" in System Settings. Otherwise macOS swallows Fn events at the firmware level.

### 2. Audio capture: sounddevice → AVAudioEngine (April 2026)

**Persistent sounddevice stream (original):** Stream stayed open between recordings. `audio_callback` gated on `if recording:`. macOS decided we weren't consuming, suspended the mic hardware, and delivered silence on the next press. ~50% miss rate.

**Per-recording sounddevice stream (`1ad66f3`):** Fresh `sd.InputStream` on every FN press. No more stale-mic, but now every recording dropped its first word to the CoreAudio warmup window (~100–300ms).

**AVAudioEngine with continuous input tap (April 2026, current):** Apple's native audio framework. The engine runs for the lifetime of the app, continuously pulling samples. The tap callback fires immediately with live audio on FN press — nothing to warm up. Resampling from native 48 kHz down to Whisper's 16 kHz happens once per recording in `stop_recording` using `scipy.signal.resample_poly`.

**Trade-off:** PyObjC bridging is more work than `sd.InputStream(...)`. Required registering the tap block signature via `objc.registerMetaDataForSelector` and extracting the raw pointer via `PyObjCPointer.pointerAsInteger`. See `av-audio-engine-implementation.md`.

### 3. Direct UI Updates → Queue-Based Updates

**The original approach:** When the recording worker wanted to update the menu bar icon (e.g., change from "ready" to "recording"), it would call `app.set_recording()` directly, which would set `self.icon = ICON_RECORDING`.

**What went wrong:** The `rumps` library is built on top of AppKit (macOS's native UI framework). AppKit has a strict rule: all UI updates must happen on the main thread. Our recording worker runs on a background thread. Violations sometimes worked, sometimes hung, sometimes caused subtle corruption — random freezes that were hard to reproduce.

**The fix:** Background threads never touch the UI directly. They put a message in a thread-safe queue (`ui_status_queue`). The main thread runs a timer that checks this queue 20 times per second and applies the updates.

**Trade-off:** Up to 50ms delay between requesting a UI update and seeing it. Imperceptible.

## Summary

The final architecture is more reliable than any of the prior iterations:

| Component | Previous approach(es) | Problem | Current approach |
|-----------|-----------------------|---------|------------------|
| Keyboard | CGEventTap, then CGEventSourceFlagsState polling | Tap silently died / polling hung permanently | NSEvent global monitor sets a flag; worker polls flag |
| Audio | Persistent sounddevice stream, then per-recording sounddevice stream | Stale mic (50% miss) vs. first-word drop (~200ms) | AVAudioEngine input tap running continuously |
| UI | Direct updates from any thread | Random freezes | Queue updates, apply on main thread |
