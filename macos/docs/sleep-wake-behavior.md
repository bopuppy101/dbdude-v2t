# macOS microphone sleep and recovery

V2T keeps the microphone ready while the user session and at least one connected
screen are awake. Screen sleep, system sleep, screen lock, and an inactive user
session suspend capture. Returning to an awake, unlocked session automatically
rebuilds the microphone connection and refreshes the Fn listener. Active audio-device recovery also refreshes the Fn listener, because a dock change can affect both devices. A maintenance wake with dark screens leaves
capture suspended.

## Status and recovery

- **Ready:** the audio engine has produced a live callback. Hold Fn to dictate.
- **Recording:** V2T is collecting audio while Fn is held.
- **Suspended:** the microphone is closed intentionally; no watchdog rebuild.
- **Recovering:** V2T is opening audio and waiting for its first callback.
- **Microphone unavailable:** startup failed; the error appears in the status.
  Retries occur at two-second intervals. Check macOS microphone permission or
  reconnect the input device if needed.

A held Fn key must be released before a new recording can begin after recovery.
A recording interrupted by suspension is discarded. Completed transcription
results that arrive after suspension are retained in memory instead of typed.
Use **Copy held dictation** in the menu to copy those results deliberately.
Unstarted queued transcription from an older audio session is discarded. Held
results are not persisted and are lost when V2T exits.

Capture, engine rebuilds, Fn control, notifications, and output delivery run on
the main event loop. Audio callbacks use a generation token and a nonblocking
lock: callbacks from removed engines cannot add audio to a new session or block
engine teardown. The background transcription worker cannot type directly.

## Automated checks

From the repository root:

```sh
macos/venv/bin/python -m unittest discover -s macos/tests -v
macos/venv/bin/python -m unittest discover -s tests -v
```

These tests use fake devices and notifications. They do not sleep the Mac,
access its microphone, load a transcription model, or type into another app.

## Real microphone probe

Leave the Mac unlocked with its lid open, then run:

```sh
V2T_TEST_HOOKS=1 macos/venv/bin/python macos/tests/hardwareprobe.py
```

The probe runs a separate V2T instance using the real microphone. It injects
notifications into that process, verifies audio closes for longer than one
watchdog interval, checks for sleep assertions attributed to its PID, and
verifies recovery across 20 cycles. It never transcribes or types. Its machine
readable `PROBE_RESULT` distinguishes this probe from actual system sleep.

A locked session is a valid suspended-startup test, but blocks the awake recovery
probe. Unlocking is required to test readiness. Avoid pressing Fn while another
regular V2T instance is running during this probe.

## Real sleep tests

Follow [the implementation checklist](sleep-wake-implementation-plan.md).
For each run, capture the source hash, V2T PID/log, `pmset -g assertions`,
`pmset -g batt`, and macOS sleep/wake records (`pmset -g log`). Correlate the
sleep interval with the V2T transition timestamps. A dark display or a successful
injected notification does not prove system sleep.

Check other blockers independently: Codex/ChatGPT, CoreSpeech, media playback,
and other applications can prevent sleep after V2T releases its own microphone.
Do not remove unrelated assertions or alter system power settings without a
specific test reason. Record and restore any temporary test settings.

Physical display connections, lid actions, spoken first-word verification,
overnight sleep, and 24–48-hour sleep require separate real tests. These remain
pending until evidence is collected. Current results are in
[sleep-wake-test-results.md](sleep-wake-test-results.md).
