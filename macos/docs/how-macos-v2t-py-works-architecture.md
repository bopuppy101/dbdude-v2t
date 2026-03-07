# How It Works

## The Three Workers

### 1. Main Thread (rumps)
- `rumps` is a library that puts an icon in your menu bar (the little colored dot)
- It runs a loop waiting for you to click the menu
- macOS rule: only this thread can change the icon/menu - if other threads try, the app freezes

### 2. Recording Control Worker (background thread)
- Runs a simple loop every 20ms: "Is Fn key held down right now?"
- Uses `CGEventSourceFlagsState` - a macOS function that returns the current state of all modifier keys (Shift, Ctrl, Fn, etc.)
- If Fn just got pressed → start capturing audio
- If Fn just got released → stop capturing, send audio to transcription

### 3. Transcription Worker (background thread)
- Waits for audio to appear in a queue
- Runs Whisper (the AI speech-to-text model) on the audio
- Types the result into whatever app is focused

## The Key Insights

### Why poll instead of events?
macOS has a fancy system called CGEventTap that notifies you when keys are pressed. But it kept dying silently. Polling is dumber but reliable - we just ask "what's the key state?" 50 times per second.

### Why keep the microphone running?
`sounddevice` (audio capture library) uses PortAudio under the hood. Starting/stopping the audio stream rapidly caused PortAudio to hang. Solution: start it once, leave it running. We just ignore the audio data when not recording.

### Why the UI queue?
When the recording worker wants to change the icon to "recording", it can't touch the UI directly (macOS will freeze). So it puts a message in a queue. The main thread checks the queue 20 times per second and applies the changes itself.

## Data Flow

```
You press Fn
    ↓
Recording worker notices (polling every 20ms)
    ↓
Sets recording=True, audio starts accumulating
    ↓
You release Fn
    ↓
Recording worker notices
    ↓
Audio chunk goes into transcription_queue
    ↓
Transcription worker picks it up
    ↓
Whisper converts speech → text
    ↓
pynput types the text into your active app
```

## What Fixed the Hangs

We went through several architectural iterations before landing on something stable. Here's what went wrong and how we fixed it.

### 1. CGEventTap → Direct Polling

**The original approach:** We used macOS's `CGEventTap` API to get notified whenever a key was pressed or released. This is the "proper" way to monitor keyboard events on macOS - you register a callback, and the OS calls your function whenever something happens. Professional apps like iTerm2 use this approach.

**What went wrong:** The event tap would silently stop delivering events after a period of use (sometimes minutes, sometimes longer). The app would still be running, the menu bar icon would still be there, but pressing Fn Thank you.(the record button, actually you hold down FN to record) would do nothing. No error, no warning - it just stopped working. macOS has a mechanism to disable event taps if they become slow or unresponsive (`kCGEventTapDisabledByTimeout`), and we handled that by re-enabling the tap. But even with that fix, the tap would still die in ways we couldn't detect or recover from.

**The fix:** Instead of waiting for the OS to tell us when keys change, we now poll `CGEventSourceFlagsState()` every 20ms. This function returns the current state of all modifier keys (Fn, Shift, Control, etc.) at the moment you call it. It's a simpler, "dumber" approach - we're asking "is Fn held?" 50 times per second instead of waiting to be told. But it's rock solid. There's no callback to stop working, no event tap to die. We just read the current state directly from the system.

**Trade-off:** Polling uses slightly more CPU than event-based approaches (though 50 checks per second is negligible). The benefit is reliability.

### 2. Create/Destroy Audio Stream → Persistent Stream

**The original approach:** Each time you pressed Fn, we created a new audio input stream. When you released Fn, we called `stream.stop()` and `stream.close()` to tear it down. This seemed clean - only use the microphone when actually recording.

**What went wrong:** The `sounddevice` library uses PortAudio under the hood, which is a cross-platform audio I/O library. When you rapidly start and stop audio streams (like tapping Fn quickly several times), PortAudio would hang. Specifically, `stream.stop()` would block forever waiting for audio buffers to drain. We tried `stream.abort()` instead (which should return immediately), but that would also hang after rapid start/stop cycles. The stream operations just weren't designed for rapid cycling.

**The fix:** Create the audio stream once on first use and never destroy it. The stream runs continuously - the microphone is always "listening" from PortAudio's perspective. But we only *capture* the data when the `recording` flag is True. The `audio_callback` function checks this flag and only appends audio data to our buffer when we're actually recording. When not recording, the callback just ignores the incoming audio.

**Trade-off:** The microphone icon shows in the menu bar 100% of the time because the stream is always active. For a voice transcription app, this is acceptable. The benefit is we never hang on stream operations.

### 3. Direct UI Updates → Queue-Based Updates

**The original approach:** When the recording worker wanted to update the menu bar icon (e.g., change from "ready" to "recording"), it would call `app.set_recording()` directly, which would set `self.icon = ICON_RECORDING`.

**What went wrong:** The `rumps` library is built on top of AppKit (macOS's native UI framework). AppKit has a strict rule: all UI updates must happen on the main thread. Our recording worker runs on a background thread. When it tried to update the icon, we were violating this rule. AppKit doesn't always crash when you do this - sometimes it works, sometimes it hangs, sometimes it causes subtle corruption. In our case, it would cause random freezes that were hard to reproduce.

**The fix:** Background threads never touch the UI directly. Instead, they put a message in a thread-safe queue (`ui_status_queue`). The main thread runs a timer that checks this queue 20 times per second. When it finds a pending update, it applies it. This way, all actual UI changes happen on the main thread where they're safe.

**Trade-off:** There's a slight delay (up to 50ms) between requesting a UI update and seeing it. This is imperceptible to humans. The benefit is no more random freezes.

## Summary

The final architecture is less elegant than what we started with, but it's reliable:

| Component | Original Approach | Problem | Current Approach |
|-----------|------------------|---------|------------------|
| Keyboard | CGEventTap callbacks | Silently stopped working | Poll key state directly every 20ms |
| Audio | Create/destroy stream per recording | Hung on rapid start/stop | Keep stream running forever |
| UI | Direct updates from any thread | Random freezes | Queue updates, apply on main thread |

Sometimes the "dumb" approach wins.
