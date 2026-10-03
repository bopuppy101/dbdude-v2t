# Sleep/wake test results

Updated: 2026-09-15T16:52:24-04:00.
Branch: `codex/macos-sleep-wake`. Changes are uncommitted.
Runtime source SHA-256: `644afab207f22b6871f6f9a71c6dff591d4a86b3bede44fb4b4738924da9e1d1`.

## Results

| Check | Result | Evidence / limit |
| --- | --- | --- |
| Existing macOS baseline | PASS | 28 tests before changes |
| Expanded macOS suite | PASS | 70 tests, real application wiring plus fake hardware |
| Repository formatting regression | PASS | 1 test |
| Python compilation | PASS | Runtime modules compile |
| Diff whitespace | PASS | `git diff --check` |
| Locked startup, real macOS adapter | PASS | PID 40977 stayed suspended with no engine; locally posted screen notifications dispatched |
| Real microphone recovery probe | PASS | PID 41490: 20/20 releases and recoveries; first live callback readiness in 0.211–0.223 seconds; built-in mic, battery |
| Actual automatic display sleep / recovery | PASS (built-in display, battery) | Display off and V2T assertion off at 17:26:26; display on at 18:03:27; same PID 41374 resumed, user reports dictation working |
| Actual lid-close system sleep / recovery | PASS (battery, built-in display) | 18:06:38 Clamshell Sleep → 18:35:27 lid-triggered wake; same V2T PID; immediate dictation reported working |
| Automatic idle system sleep | PENDING | Earlier dinner interval had no system sleep; printing service retained NetworkClientActive |
| Studio Display / lid / power changes | PENDING | Requires Mike and connected hardware |
| Overnight and 24–48-hour sleep | PENDING | Requires actual elapsed time |

Automated tests cover state transitions, notification order and duplicates,
maintenance wakes, locked/inactive sessions, missing initial audio callback,
stopped/silent devices, failed startup and teardown, retry timing, stale callbacks,
in-flight rebuild suspension, Fn release requirements, delayed output, and shutdown.
A 10,000-event deterministic randomized test checks lifecycle invariants. This does
not establish native resource leak freedom; real cycle/resource checks remain pending.

## Baseline observations

At 16:45 EDT, the regular V2T process PID 37929 held a Core Audio
PreventUserIdleSystemSleep assertion. CoreSpeech PID 1298 and ChatGPT also had
separate assertions. These must be distinguished during actual automatic-sleep
testing. Baseline Fn-to-first-buffer latency has not yet been measured.

At 16:49 EDT, the first hardware probe timed out waiting for Ready because the
Mac was locked. Investigation confirmed `CGSSessionScreenIsLocked = 1` and
`session_awake() = False`. This was a blocked awake test, not an audio failure.
At 16:51 EDT, the updated probe explicitly verified locked startup and successful
native notification dispatch. It then reported BLOCKED rather than opening audio
in the locked session. Probe logs are local ignored files in `macos/docs/`.
The locked probe preceded the final small cleanup/test changes; rerun with the
recorded final source hash before final hardware acceptance.

## Next execution steps

1. Mike unlocks the Mac and leaves the lid open.
2. Run the 20-cycle real microphone probe and record its source hash, timings,
   audio assertions, and resource counts.
3. Replace the regular V2T process with the validated patch, then check a spoken
   first-dictation sample in a dedicated destination.
4. Execute the real hardware matrix in the implementation checklist. Ask Mike
   for each cable/lid action when needed; confirm actual sleep through macOS logs.

Mike restarted regular V2T at 17:23 EDT; PID 41374 runs from the modified macOS repository. No system power settings, wake
schedules, or unrelated applications have been changed. No commit or push has
been made. This task is **not complete** until hardware acceptance is finished.

## Awake probe, 17:24 EDT

The real audio probe completed 20 cycles successfully with locally injected screen
notifications. All 20 suspended intervals had no audio assertion attributed to
probe PID 41490. This is not actual system sleep. Native resource counts have not
yet been measured. Actual lock/unlock observation begins next for PID 41374.

## Dinner interval: real automatic display sleep, September 15

- **17:26:26 EDT:** macOS records display off and V2T PID 41374's audio assertion
  turning off in the same second. The passive observer confirms inactive session
  and no V2T assertion at 17:26:28; it continued through 17:28:23.
- **17:26:29:** the separate CoreSpeech audio assertion turns off.
- **17:41:26 and 17:56:26:** macOS summaries list the printing service's
  `NetworkClientActive` assertion; no V2T audio assertion appears.
- **18:03:27:** display turns on. At 18:04:22, V2T's current audio assertion has
  age 54 seconds, consistent with reopening around 18:03:28. Process PID 41374
  still has the original 17:23:17 start time. Mike reports transcription working.
- **Duration:** 37 minutes 1 second of recorded display-off time. There is no
  system Sleep/Wake entry in this interval, so it is not a long system-sleep pass.

`lpstat -t` identifies a Brother printer job queued September 8, still in
"Looking for printer" state. This corresponds to the persistent CUPS network
assertion and is a candidate blocker for automatic system sleep. The queued print
job has not been cancelled or changed. Evidence is in the local ignored file
`dinner-sleep-evidence.log`. Current runtime source matches the awake probe.

Next: lid-close/open system sleep on the built-in display, followed by explicit
sleep and external-display tests. The printing blocker must be addressed or
isolated before accepting automatic system sleep.

## Lid-close sleep: 18:06–18:35 EDT, September 15

| Event | Timestamp | Evidence |
| --- | --- | --- |
| Lid/display off; V2T microphone released | 18:06:33 | Display off and PID 41374 audio assertion turned off |
| Actual system sleep | 18:06:38 | `Entering Sleep state due to 'Clamshell Sleep'`, battery 62% |
| First background wake | 18:07:09–18:07:54 | DarkWake, wireless/SMC reason; 45 seconds; then Maintenance Sleep |
| Second background wake | 18:24:48–18:24:50 | DarkWake, rtc/SleepService reason; 2 seconds; then back to sleep |
| Display on | 18:35:26 | Display turned on |
| User wake | 18:35:27 | `Wake from Deep Idle`, reason includes `lid` and HID activity |
| V2T capture active again | Approximately 18:35:29 | At 18:36:23, PID 41374 audio assertion age was 54 seconds |

Elapsed from initial system sleep to user wake: **28 minutes 49 seconds**.
Logged sleep durations total **28 minutes 2 seconds**; the two background wakes
account for 47 seconds. This was real system sleep, not merely a dark display,
but it was not 30 uninterrupted minutes asleep.

V2T PID 41374 retains its 17:23:17 start time, confirming no relaunch. Mike reports
immediate successful Fn dictation after opening the lid. No V2T audio-assertion
reactivation is recorded during the two dark wakes; continuous native-app logging
was not captured, so do not treat missing log events alone as exhaustive proof.
The external display was disconnected, and the Mac ran on battery.

H04 passes for this configuration. This also provides a real approximately
30-minute sleep recovery case. One-hour, overnight, extended sleep, external
microphone changes, and automatic idle system sleep remain pending.

## Studio Display connection failure and Fn recovery follow-up

Mike reported that dictation did not work after connecting the Studio Display.
His log shows audio recovering at 18:40:10 with `Studio Display Microphone`,
followed by Ready about 0.698 seconds later. That verifies audio callbacks, not
Fn input or successful transcription. The exact failed stage remains unconfirmed.
The repository documents Fn monitor failures after external keyboard changes.
Inspection found audio-only recovery did not replace the Fn monitor, although
session wake did. This is a plausible cause, not a confirmed diagnosis.

The follow-up patch makes every active audio recovery replace the Fn monitor,
and rejects a missing monitor handle instead of presenting a healthy input state.
73 automated macOS tests pass, including real application wiring tests for
listener replacement after device failure and listener installation failure.
Regular PID 41374 has not loaded this follow-up patch yet. A Studio Display
real-audio probe and a user device-switch retest are pending. Earlier hardware
passes apply to the earlier patch and affected cases must be rerun.

### Follow-up native Studio Display probe

PASS: probe PID 42947 completed 20/20 real-audio cycles using the Studio Display
microphone at 48 kHz. All 20 suspended intervals lacked that PID's audio assertion.
Recovery to live-callback Ready took 0.235–0.349 seconds. The probe logged 21 Fn
monitor installations (startup plus 20 recoveries). Notifications were injected
locally; actual hardware reconnect and human Fn/text delivery are still pending.
Runtime source SHA-256 for this follow-up: `b16e07aa55386908a0dcd3a49a679e21239e8b0f7f7b40eb230694f5a96c09b1`.
Regular V2T requires a restart to load this change. Files changed in the follow-up:
`dbdude-v2t.py`, `lifecycle.py`, `tests/testintegration.py`, `tests/testlifecycle.py`,
and the Fn/sleep-wake documentation. No dependencies or system settings changed.

### User clarification, approximately 18:45 EDT

Mike clarified that the first attempt after connecting the Studio Display did
not record, but dictation began working automatically after approximately a
minute with the lid open. This is a delayed-recovery observation, not a persistent
Fn failure. PID 41374 still started at 17:23:17, so the later Fn-rearm change did
not cause this spontaneous recovery and is not a confirmed fix for the delay.

macOS records connection/power-chime activity at 18:39:43 and 18:40:03; V2T's
old built-in input assertion closes at 18:40:09. The user-supplied log shows
Studio Display engine recovery and Ready at 18:40:10 (~0.698 seconds within the
rebuild). Those records do not establish the exact cable action time, first Fn
attempt, keyboard used, or first successful recording. A Bluetooth connection
request at 18:40:37 is another observation, not proof of causation.

Next: load the current patch, then measure a physical disconnect/reconnect using
the laptop's Fn key first to separate audio recovery from external-keyboard
connection behavior. Capture first press, Recording, and successful output timing.
Do not claim the minute-long delay is fixed based on simulated notifications.

### Reconnect retest prepared, 18:48 EDT

Mike restarted V2T at 18:48:08; PID 43216 currently owns a Studio Display audio
assertion. The Fn-rearm follow-up is now available in the restarted process.
A three-minute passive assertion/session observation is running for a physical
disconnect/reconnect test using the laptop keyboard. Result pending.

### External Apple keyboard reconnect retest: PASS

Mike disconnected and reconnected the Studio Display with the external Apple
keyboard attached and laptop lid open. He reports the keyboard and dictation
returned together in about a second. The supplied app log shows the Fn monitor
installed, Studio Display input at 48 kHz, Ready at 18:52:33, recording at 18:52:37,
and successful transcription of 8.25-second and 3.10-second recordings.

macOS recorded a connection power chime at 18:52:25. Thus the recorded interval
from that chime to app Ready is approximately eight seconds; it is not a measured
one-second cable-to-dictation latency. The human report establishes responsive
Fn/dictation once the keyboard returned. No minute-long failure was reported.
An ObjCPointerWarning occurred while extracting float audio samples, but capture
and both transcriptions completed; no runtime change was made for this warning.

This passes the awake reconnect portion of H21 on the Fn-rearm patch. Docked
screen sleep and recovery remain pending. A bounded 30-minute passive observer
is prepared for the 20-minute Studio Display walk-away test, monitoring PID 43216.
The earlier three-minute reconnect observer ended before this physical reconnect;
this retest uses the supplied app log and macOS historical power records.

## Docked Apple-menu Sleep attempt, 18:55:56 EDT

The sleep request (`Software Sleep pid=916`) entered DarkWake and returned to
FullWake within the same timestamped second. Wake reason: `HID Activity`.
WindowServer recorded a simultaneous input event from `USB Receiver`, eventType
17. This implicates input activity associated with that receiver; the record alone
does not identify whether the underlying peripheral was a mouse or keyboard or
whether the input was intentional. V2T PID 43216 turned off its microphone sleep
assertion at 18:55:56 before the immediate full wake. The display went off/on in
that same second. No sustained system sleep occurred, so this is not a sleep pass.

Suggested retry: close the lid first, then select Sleep using the Studio Display,
and leave external input devices untouched. No power settings, peripheral settings,
or runtime code were changed for this investigation. All test/observation processes
were stopped at Mike's request earlier; do not start any new observers. Tests run
on Mike's schedule and subsequent checks use only existing macOS logs.

## Docked sleep request and undocked return, 18:56–19:11 EDT

Mike reports the laptop underside was not hot when picked up and immediate
successful dictation using the laptop Fn key. This is a subjective temperature
observation, not a sensor measurement or proof of low power draw.

- 18:56:22: software sleep entered **DarkWake** on AC at 74% battery; display
  turned off and V2T PID 43216's Studio Display audio assertion turned off.
- 19:06:22: system remained in a state summarized as `[System: NetAcc kCPU]` on
  AC at 82%. No full Sleep entry occurred during the docked interval.
- 19:11:00: V2T's obsolete Studio Display aggregate assertions were released.
- 19:11:01: power changed to battery at 86%.
- 19:11:02: actual Sleep state entered, software sleep reason.
- 19:11:08: full wake from Deep Idle with lid/HID wake reason, after six seconds.
- 19:11:09: display on. At 19:11:43 V2T owned a built-in audio assertion aged
  30 seconds, consistent with capture reopening approximately 19:11:13.

PID 43216 still has its original 18:48:08 start time: no V2T restart was needed.
Microphone release and recovery across the dock-to-laptop transition succeeded.
Sustained full sleep while docked remains unresolved; this is **not** a 15-minute
full system-sleep pass. Remaining dock/network assertions need separate diagnosis;
the evidence does not establish a single responsible device or service.
No observers or hardware probes were running during this test. Existing macOS
logs were read after Mike returned. Raw evidence: local ignored
`docked-sleep-return-evidence.log`.

## Strong docked-sleep diagnosis: stuck network print job

At 19:13 EDT, `lpstat -t` still shows Brother_HL_L2395DW_series-1 queued since
September 8 at 13:56:30, in "Looking for printer" state. CUPS PID 59997 holds
NetworkClientActive named org.cups.cupsd continuously (about 173 hours).

The historical kernel log at 19:11:01 explicitly says system sleep was prevented
by kPMCPUAssertion. At 19:06:22 the user assertion mask was 0x1 and the power
summary was NetAcc kCPU. At 19:11:01.765, coinciding with the AC-to-battery policy
change, the kernel user assertion mask changed 0x1 -> 0x0 and summary became
NetAcc without kCPU. Actual software-requested sleep followed at 19:11:02.

Apple's published PowerManagement/pmconfigd/PMAssertions.c maps NetworkClientActive
(kNetworkAccessType) to setKernelAssertions with kPrevDemandSlpEffect on AC, and
to modifySettings with kPrevIdleSlpEffect on battery (lines 6781–6794 in the
inspected main revision). The kernel assertion mapping uses the CPU bit. This
explains why the same CUPS assertion could hold the Mac in DarkWake on AC while
allowing the explicit Sleep request to complete on battery.

Source: https://github.com/apple-oss-distributions/PowerManagement/blob/main/pmconfigd/PMAssertions.c

The stuck print job is now the strongest identified cause, supported by matching
OS policy and live/historical assertions; verify causality by clearing that job
and retesting on AC. Do not attribute the issue to the Studio Display hardware
alone. Job cancellation has NOT been performed; Mike must confirm removal of the
specific pending print request. No observer or settings change was started.

## Authorized cancellation, 19:14:15 EDT

Mike explicitly requested cancellation of the pending print job. Executed
`cancel Brother_HL_L2395DW_series-1` successfully. `lpstat -o` returned no pending
jobs. An immediate `pmset -g assertions` snapshot showed NetworkClientActive = 0
and no CUPS assertion. This confirms the stale print job owned the persistent
network blocker. Full docked sleep must still be verified in the next user-run
sleep attempt. Printer configuration was not changed. No observer was started.
