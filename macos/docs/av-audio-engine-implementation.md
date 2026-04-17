# AVAudioEngine Implementation Plan (feature/avaudioengine)

## Branch
`feature/avaudioengine` off `develop`.

## Problem being solved
Two bugs in the current sounddevice/PortAudio audio path on macOS:

1. **First-word drop (~100–300ms).** `start_recording()` creates a fresh `sd.InputStream` and calls `.start()` on every FN press. CoreAudio takes 100–300ms to actually begin delivering samples (mic power-up + buffer allocation). The user's first word is lost in that warmup window.
2. **Stale-stream / mic-power-down (~50% miss rate, fixed in `1ad66f3` by closing the stream per recording).** When the stream was kept open with the callback gated by `if recording:`, macOS interpreted us as not consuming audio and powered down the mic. Next press got near-silence.

We're stuck between these two: closing the stream avoids stale audio but introduces warmup; keeping it open avoids warmup but introduces stale audio. **The bind only exists because sounddevice's callback model lets macOS judge us as "not consuming."** A framework that pulls samples continuously regardless of what the app does with them dodges both.

## Solution
Replace the sounddevice input path on macOS with **AVAudioEngine** + an installed input tap, accessed via PyObjC. The engine pulls samples continuously, so:

- The mic stays powered (no stale-stream bug).
- The tap callback fires immediately on FN press with already-flowing audio (no warmup).

This matches the standard Apple-recommended approach for low-latency mic capture (used by AVAudioEngine-based dictation apps including the open-source Wispr clone `sebsto/wispr`).

## Architecture

### Current (sounddevice)
```
App startup    → nothing audio-related
FN press       → start_recording() creates sd.InputStream, .start()
               → 100–300ms CoreAudio warmup
               → audio_callback fires with samples, appends to audio_data
FN release     → stream.stop() + stream.close()
               → process audio_data
```

### New (AVAudioEngine)
```
App startup    → setup_audio_engine() creates engine, installs tap, .start()
               → tap fires continuously with samples, discarded when recording=False
FN press       → set recording=True
               → next tap callback starts appending to audio_data (no warmup — engine is already running)
FN release     → set recording=False
               → process audio_data
App quit       → engine.stop(), remove tap
```

The `recording_control_worker` polling loop and the NSEvent FN-key monitor are unchanged. The change is entirely in the audio capture layer.

## Step-by-step

### 1. Imports and globals
- Remove: `import sounddevice as sd`
- Add: load AVAudioEngine, AVAudioFormat, AVAudioPCMBuffer, AVAudioTime via `objc.loadBundle` / `objc.lookUpClass` (same pattern as existing AVCaptureDevice load)
- Replace `stream` global with `audio_engine` global

### 2. New `setup_audio_engine()` function
- `engine = AVAudioEngine.alloc().init()`
- `input_node = engine.inputNode()`
- Build target format: `AVAudioFormat(standardFormatWithSampleRate:16000.0 channels:1)` if input node accepts it, otherwise capture at native rate (44.1k or 48k) and resample in the callback
- `input_node.installTapOnBus_bufferSize_format_block_(0, 4096, format, _audio_tap_callback)`
- `engine.prepare()`
- `(success, error) = engine.startAndReturnError_(None)`
- Log result

### 3. New `_audio_tap_callback(buffer, when)` function
- Set block signature: `_audio_tap_callback.__block_signature__ = b'v@?@@'`
- Read `frame_length = buffer.frameLength()`
- Get `float_channel_data = buffer.floatChannelData()` (pointer to channel-0 floats)
- Convert to 1D numpy `float32` array of length `frame_length`
- Read `recording` flag; if True, append numpy slice to `audio_data`

### 4. Simplify `start_recording()`
- Reset `audio_data = []`
- Set `recording_start_time = time.time()`
- Update UI status to "Recording..."
- **No stream creation.** Engine is already running.

### 5. Simplify `stop_recording()`
- Same as today, minus the `stream.stop()`/`stream.close()` block
- Just process `audio_data` and queue for transcription

### 6. Update `cleanup()`
- Call `audio_engine.stop()` and remove the tap on bus 0
- Existing transcription-queue join behavior unchanged

### 7. Wire into startup
- After `request_microphone_permission()`, call `setup_audio_engine()`
- If engine fails to start, log error and exit (no point continuing without a mic)

## Open questions / risks

1. **PyObjC block signature for the tap.** The signature `b'v@?@@'` is my best guess (`void` return, block self, two object args). We've hit block-signature issues before (see `project_pyobjc_block_fix.md` for the AVCaptureDevice permission callback). If the callback never fires, this is the first thing to check.

2. **Sample rate.** AVAudioEngine's input node is usually locked to the hardware's native rate (44.1 or 48 kHz). If `installTapOnBus` rejects a 16 kHz format, we have two choices:
   - Capture native, resample in the tap callback with `scipy.signal.resample_poly` or numpy decimation. Adds a CPU cost per buffer.
   - Insert an `AVAudioMixerNode` between input and tap to convert format. More complex graph.

3. **AVAudioPCMBuffer → numpy.** `floatChannelData()` returns a `**float` (pointer to per-channel pointers). PyObjC may expose this as an opaque pointer object — converting to numpy without copying needs `np.frombuffer(..., dtype=np.float32, count=frame_length)` or PyObjC's `objc.array_at`. May need experimentation.

4. **Threading.** The tap callback fires on a high-priority audio thread. Appending to a Python list is GIL-protected so it's safe, but we should keep the callback short. No transcription, no I/O — just buffer-copy and append.

5. **Device change handling.** If the user plugs/unplugs a mic mid-session, the engine may stop or fail silently. AVAudioEngine has notifications for this (`AVAudioEngineConfigurationChangeNotification`); handling them is out of scope for v1. Workaround: restart the app, same as today's external-keyboard issue.

## Out of scope
- Pre-roll buffer (not needed — engine has no warmup once started).
- Windows/Linux changes (sounddevice stays everywhere except macOS).
- `recording_control_worker` polling loop (unchanged — still reads `_fn_held` from NSEvent monitor).
- Refactoring the FN-key detection layer.

## Testing
1. Verify first word is captured (the bug that motivated this work).
2. Sit idle for 5+ minutes between recordings, then record — confirm no stale-mic / silence.
3. Quit cleanly via menu — confirm engine stops, no orphaned audio thread.
4. Run for 1–2 hours of intermittent dictation; watch for missed recordings, audio glitches, or hangs.

## Rollback
If this goes sideways: `git checkout develop && git branch -D feature/avaudioengine`. Develop has the working sounddevice path.

## Related
- `1ad66f3` — Original stale-stream fix that traded 50% miss rate for ~200ms first-word drop.
- `macos/docs/event-based-transcription-on-macos.md` — NSEvent FN-key detection (already merged to develop, separate concern).
- [sebsto/wispr](https://github.com/sebsto/wispr) — Open-source clone of Wispr Flow using AVAudioEngine.
