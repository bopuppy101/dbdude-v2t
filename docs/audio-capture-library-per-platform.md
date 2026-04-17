# Audio Capture Library per Platform

dbdude-v2t runs on Windows, Linux, and macOS. The audio *capture* path is not the same on all three, even though the rest of the app (hotkey handling, transcription, mappings, rules, UI) is cross-platform.

## What each platform uses

| Platform | Library | Underlying OS layer |
| --- | --- | --- |
| Windows | [`sounddevice`](https://python-sounddevice.readthedocs.io/) (PortAudio) | WASAPI |
| Linux (Ubuntu) | [`sounddevice`](https://python-sounddevice.readthedocs.io/) (PortAudio) | ALSA / PulseAudio |
| macOS | `AVAudioEngine` via [PyObjC](https://pyobjc.readthedocs.io/) | CoreAudio / AVFoundation |

## Why macOS is different

On Windows and Linux the PortAudio path is rock solid — mics initialize fast, stay awake, and `sd.InputStream(...).start()` delivers samples effectively immediately.

On macOS the same library hit two CoreAudio-specific bugs that kept swapping with each other:

1. **First-word drop (~100–300ms).** Creating a fresh `sd.InputStream` per recording incurred CoreAudio's mic power-up + buffer allocation latency. The first word of every utterance was lost.
2. **Stale-stream / ~50% miss rate.** Keeping the stream open between recordings caused macOS to power down the mic when the callback wasn't actively consuming samples, delivering near-silence on the next press.

Neither a single stream nor per-recording streams worked. The real fix was to stop using a library that lets macOS judge us as "not consuming audio" and switch to an Apple framework that pulls samples continuously.

## The macOS solution

`macos/dbdude-v2t.py` uses **AVAudioEngine** with an installed input tap. The engine runs from app startup to quit, continuously pulling 48 kHz float32 samples from the mic. The tap callback only appends to the recording buffer when the FN key is held; when the key is released, the captured samples are resampled to 16 kHz with `scipy.signal.resample_poly` and queued for mlx_whisper.

Result: mic stays powered continuously (no stale-stream bug), tap fires with live audio on FN press (no warmup — first word is captured), and rapid FN taps don't hang.

The code path for everything *after* capture — transcription queue, mappings, rules, typing — is identical across all three platforms.

## Deep dive

For the macOS implementation details (PyObjC bridging, `installTapOnBus` block signature registration, `pointerAsInteger` pointer extraction, resampling) see `macos/docs/av-audio-engine-implementation.md`.
