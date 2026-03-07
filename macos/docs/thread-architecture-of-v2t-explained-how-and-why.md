# Thread Architecture of Voice2Text: How and Why

## Overview

Voice2Text is a multi-threaded application that handles audio capture, transcription, system tray management, and GUI dialogs concurrently. Understanding the thread architecture is critical for debugging issues and adding new features, especially those involving GUI components.

## Why Multiple Threads?

Voice2Text must perform several tasks simultaneously without blocking:
- Listen for keyboard shortcuts (Alt+Shift for recording)
- Respond to system tray menu clicks
- Capture audio from the microphone
- Transcribe audio using the Whisper model
- Display GUI dialogs for settings and license management

Without threading, any long-running operation (like transcription) would freeze the entire application.

## Thread Inventory

### 1. Main Thread

**What it does:**
- Runs the keyboard listener loop
- Polls every 20ms for:
  - Keyboard state (Alt+Shift held for recording)
  - Restart requests from configurator
  - License dialog requests from menu
- Calls tkinter dialogs when requested (license management)
- Coordinates shutdown of other threads

**Why main thread:**
- Windows ties the message pump to the main thread
- GUI frameworks (tkinter, PySide6) require main thread for proper operation
- The startup license dialog works because it's called from main() before the loop starts

**Code location:** `run_voice2text()` function, specifically the `while not shutdown_event.is_set():` loop

### 2. pystray Thread (System Tray)

**What it does:**
- Displays the Voice2Text icon in the Windows system tray
- Shows the right-click context menu
- Handles menu item callbacks (Manage License, Show Configurator, Exit, etc.)
- Updates icon state (normal, recording, transcribing)

**Why separate thread:**
- `pystray.Icon.run()` is a blocking call that runs its own event loop
- If run on main thread, it would block the keyboard listener
- Menu callbacks execute on this thread

**Code location:**
```python
self._icon_thread = threading.Thread(target=self.icon.run, daemon=True)
self._icon_thread.start()
```

**Important limitation:** Menu callbacks run on the pystray thread, NOT the main thread. This is why GUI dialogs called directly from callbacks fail in compiled executables.

### 3. Audio Thread

**What it does:**
- Opens the audio stream from the microphone
- Captures audio chunks when recording is active
- Queues audio data for the transcription thread
- Handles audio device errors gracefully

**Why separate thread:**
- Audio capture is time-sensitive and must not be interrupted
- Uses a callback-based model with `sounddevice` library
- Cannot be blocked by transcription or GUI operations

**Code location:** Runs within `run_voice2text()` using `sd.InputStream` with callback

### 4. Transcription Thread

**What it does:**
- Pulls captured audio from the transcription queue
- Runs the Whisper model to convert speech to text
- Types the transcribed text using `type_text.exe`
- Applies mapping rules and transformations

**Why separate thread:**
- Transcription can take several seconds depending on audio length and model size
- Must not block audio capture or keyboard listening
- Uses a queue-based producer/consumer pattern

**Code location:**
```python
transcription_thread = threading.Thread(target=transcription_worker, daemon=True)
```

### 5. Subprocess Threads (Daemon)

**What they do:**
- Launch external executables (configurator, mapping rules editor)
- Handle subprocess communication if needed

**Why separate threads:**
- Prevents blocking the menu callback
- Allows the main application to continue while external tools run
- These are fire-and-forget operations

**Code location:** Various `threading.Thread(target=..., daemon=True).start()` calls

## The GUI Thread Problem

### The Issue

GUI frameworks on Windows (tkinter, PySide6/Qt) require the main thread to function correctly. This is because:

1. **Windows Message Pump**: Windows uses a message-based system for GUI events (mouse clicks, keyboard input, window updates). This message pump is tied to the thread that created the window.

2. **Main Thread Expectation**: Both tkinter and Qt expect to own the main thread's message pump. When called from other threads, they either:
   - Fail silently (tkinter in compiled Nuitka executables)
   - Corrupt their internal state (Qt's QApplication singleton)

### Symptoms

**Tkinter (compiled exe):**
- Dialog simply doesn't appear
- No error messages
- Works fine in interpreted Python, fails in Nuitka-compiled exe

**PySide6/Qt:**
- First dialog works
- Second invocation fails with: `QEventDispatcherWin32::wakeUp: Failed to post a message (Invalid window handle.)`
- QApplication singleton becomes corrupted when the creating thread ends

### The Solution: Flag-Based Main Thread Dispatch

Instead of calling GUI dialogs directly from pystray callbacks (wrong thread), we use a flag pattern:

1. **Menu callback sets a flag:**
   ```python
   def _manage_license(self, icon=None, item=None):
       request_license_dialog()  # Just sets _license_dialog_requested = True
   ```

2. **Main thread checks flag every 20ms:**
   ```python
   if is_license_dialog_requested():
       clear_license_dialog_request()
       show_license_management_dialog()  # Runs on main thread!
   ```

3. **Dialog runs on main thread** - tkinter works correctly

This pattern already existed for restart requests from the configurator. License dialog now uses the same pattern.

## Thread Communication

### Flags (Simple State)
- `_restart_requested` - Configurator requests engine restart
- `_license_dialog_requested` - Menu requests license dialog
- `shutdown_event` - Signals all threads to terminate

### Queues (Data Transfer)
- `audio_queue` - Raw audio chunks from capture callback
- `transcription_queue` - Complete audio segments for transcription

### Events (Synchronization)
- `recording_event` - Signals when recording is active
- `shutdown_event` - Threading.Event for clean shutdown

## Best Practices for Future Development

### Adding New GUI Dialogs

**DO:**
1. Create a request flag: `_my_dialog_requested = False`
2. Add helper functions: `request_my_dialog()`, `is_my_dialog_requested()`, `clear_my_dialog_request()`
3. Set flag from pystray callback
4. Check flag in main loop and call dialog from there

**DON'T:**
- Call tkinter or PySide6 directly from pystray callbacks
- Spawn threads to run GUI dialogs
- Assume interpreted Python behavior matches compiled exe behavior

### Adding New Background Operations

**DO:**
- Use daemon threads for fire-and-forget operations
- Use queues for producer/consumer patterns
- Use events for synchronization

**DON'T:**
- Block the main thread with long operations
- Block the audio thread with anything
- Access shared state without proper synchronization

## Diagram

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                        MAIN THREAD                          │
                    │                                                             │
                    │  ┌─────────────────────────────────────────────────────┐   │
                    │  │  Keyboard Listener Loop (20ms polling)              │   │
                    │  │  - Check Alt+Shift for recording                    │   │
                    │  │  - Check restart_requested flag                     │   │
                    │  │  - Check license_dialog_requested flag              │   │
                    │  │  - Show tkinter dialogs when requested              │   │
                    │  └─────────────────────────────────────────────────────┘   │
                    └─────────────────────────────────────────────────────────────┘
                                              │
                                              │ sets flags
                                              ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│   PYSTRAY THREAD     │    │    AUDIO THREAD      │    │ TRANSCRIPTION THREAD │
│                      │    │                      │    │                      │
│ - System tray icon   │    │ - Microphone capture │    │ - Whisper model      │
│ - Menu callbacks     │    │ - Audio buffering    │    │ - Text output        │
│ - Sets request flags │    │ - Queue audio chunks │    │ - Mapping rules      │
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
         │                           │                           ▲
         │                           │      audio_queue          │
         │                           └───────────────────────────┘
         │
         │ subprocess.Popen()
         ▼
┌──────────────────────┐
│ EXTERNAL PROCESSES   │
│                      │
│ - v2t-configurator   │
│ - v2t-mapping-rules  │
└──────────────────────┘
```

## Related Documentation

- `docs/pyside6-threading-issue-windows.md` - Detailed analysis of PySide6 threading failure
- `docs/windows-pyside6-migration.md` - Plans for future PySide6 migration

## Date

2025-12-25
