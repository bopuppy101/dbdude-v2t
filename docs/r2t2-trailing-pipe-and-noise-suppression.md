# r2t2 Trailing Pipe Fix and Noise Suppression Options

Date: 2026-09-20. Platform where this was done: Omarchy (Arch Linux, Hyprland, PipeWire).

Two separate things came out of one debugging session. The first is a code fix, committed. The second is a machine-level audio change outside the repo, plus a survey of the options that were considered and deliberately **not** implemented.

## 1. Trailing `|` in transcriptions (fixed, Omarchy only)

### Symptom

With the `r2t2` model (Confucius4-R2T2, a Qwen3-ASR fine-tune) selected, a `|` sometimes appeared at the end of typed text, e.g. `It's not worth|`.

### Cause

The model itself emits `|` when the audio ends on a partial word, i.e. when the record key is released mid-word. The raw `Transcribed:` log line already contains the pipe, before any mapping or `ydotool` output. Whisper does not do this, which is why it only showed up after switching models.

### Fix (commit `68f9bdc` on `develop`)

- `omarchy/text_formatting.py`: new `strip_trailing_pipe(text)`. String ops only, never raises, returns non-strings untouched. Removes one or more `|` at the very end of the text and nothing else.
- `omarchy/dbdude-v2t.py`: `process_and_validate_text` calls it right after whitespace cleanup and **before** any mapping. A transcript that was only a pipe returns `None`, the same path as an empty recording.
- `omarchy/tests/test_text_formatting.py`: unit tests for the helper and pipeline tests using the real transcripts from the log.

Why it is safe: a pipe the user dictates on purpose arrives as the spoken word "pipe" and is mapped to `|` later in the pipeline, after the strip has run. A pipe in the middle of the text (e.g. a dictated shell command) is untouched.

### Status on other platforms (not ported, by decision)

| Folder | Has r2t2? | Needs the fix? | Notes |
| --- | --- | --- | --- |
| `omarchy` | yes | done | |
| `windows` | yes | yes, if the symptom appears | Same `process_and_validate_text` structure; the two-line wiring is identical. |
| `macos` | yes | yes, if the symptom appears | No `process_and_validate_text`; find where the raw transcript is cleaned and hook there. |
| `ubuntu`, `ubuntu-26.04` | no | not until r2t2 is added | Harmless to add. |

Before this change `text_formatting.py` was byte-identical across all five folders, so the helper drops into each as-is.

## 2. Background noise (dehumidifier) and what was measured

Measured with PipeWire's `pw-record` reading the raw Elgato Wave XLR source and a filtered source at the same instant, RMS per second converted to dBFS.

| Condition | Raw mic | RNNoise-filtered |
| --- | --- | --- |
| Room quiet | -46 dBFS | -89 dBFS |
| Dehumidifier running, ~8-10 ft away | -39 to -41 dBFS | -72 to -97 dBFS |
| Speech (same capture) | -20 to -29 dBFS | -26 to -35 dBFS |

Takeaways: the hum sits ~18 dB below speech on the raw mic, which r2t2 handles but with reduced margin on quiet or fast phrases. The filter removes 35-55 dB of hum and lowers speech by ~6 dB, which the model does not care about. Dictation through the filter with the unit running came out clean.

Also found: one capture had `peak=0.999998`, i.e. the mic input clipped. Fixed by turning down the hardware gain knob on the Wave XLR. Healthy speech peaks are roughly 0.5-0.8.

## 3. Noise suppression: what was done (machine config, not in the repo)

Implemented on the Omarchy box only. Nothing in the app changed; the app opens the system default input and does not know the filter exists.

- Package: `noise-suppression-for-voice` (RNNoise LADSPA plugin), via pacman.
- Config: `~/.config/pipewire/filter-chain.conf.d/99-rnnoise-elgato.conf`, a `libpipewire-module-filter-chain` that captures from the Elgato node and exposes a virtual `Audio/Source` named `rnnoise_source` ("Noise Canceling source").
- VAD gating is **off** (`"VAD Threshold (%)" = 0.0`). The gate is the part of RNNoise that can chop quiet word onsets and hurt ASR. Only spectral suppression is applied.
- Service: `systemctl --user enable --now filter-chain.service` (ships with PipeWire; runs `pipewire -c filter-chain.conf`). Survives reboot.
- Default input set to the filtered source with `wpctl set-default <id>`. Running capture streams follow a default change without restart.

Switching it on/off is a default-source change, not an app setting:

```bash
wpctl status                      # find the ids
wpctl set-default <raw-mic-id>    # suppression off
wpctl set-default <rnnoise-id>    # suppression on
systemctl --user disable --now filter-chain.service   # remove entirely
```

Gotcha hit along the way: `pw-record --target <node id>` silently fell back to the default source and produced a file identical to the raw one. Target by node **name** (`--target rnnoise_source`) and verify with `cmp`.

## 4. Options considered and not taken

### 4a. Same PipeWire filter on Ubuntu

Ubuntu 22.10+ ships PipeWire. The identical config and package (`pipewire-audio` plus the RNNoise LADSPA `.so`, packaged as `noise-suppression-for-voice` or built from source) would work unchanged. Not done because r2t2 isn't on the Ubuntu builds yet and no noise problem has been reported there.

### 4b. Windows and macOS

No PipeWire, no user-level filter chain between the mic and every app. Alternatives that give the same "virtual filtered microphone" effect:

- Windows: Elgato Wave Link (noise gate, and noise removal on newer versions) exposed as a virtual mic; NVIDIA Broadcast on RTX machines.
- macOS: Wave Link. Apple's system "Voice Isolation" mic mode is per-app opt-in and would not cover a Python script.

### 4c. RNNoise inside the app (portable, all five platforms)

Run RNNoise on the captured buffer in Python before it goes to the model. Same behavior everywhere, and it would give an in-app on/off switch as a side effect.

Assessment, unmeasured judgment rather than a test:

- Improvement odds: better than even with steady noise present, mostly on marginal utterances. In a quiet room, a coin flip between "no change" and "slightly worse", because Whisper and Qwen3-ASR are already noise-robust and a denoiser can smear consonants.
- Serious-problem odds: low for audio (worst case is "slightly worse", never garbage; latency is milliseconds on a post-capture buffer). The real risk is packaging: the Python bindings wrap a C library, and prebuilt wheels may not exist for Python 3.14 or for whatever Python the Windows/macOS builds use.
- If ever done, do it safely: optional dependency with a one-line log and raw fallback if it fails to import; try/except around the call falling back to the raw buffer; off by default with a settings switch; and first an offline A/B (a dozen phrases with the hum, transcribed raw vs denoised, count word errors) to replace the guess above with a number.

Decision on 2026-09-20: leave it alone. Keep the pipe fix on Omarchy only, keep the PipeWire filter as a machine-level config, and do not build 4a, 4b, or 4c.
