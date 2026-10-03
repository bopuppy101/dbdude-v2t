# macOS V2T sleep/wake implementation and test plan

Created: 2026-09-15. Status: implementation and automated checks complete; hardware validation in progress.
Repository: `/Users/mike/git/dbdude-v2t`.
Branch: `codex/macos-sleep-wake`, based on `develop`.

## Agreed behavior

Keep V2T running and its microphone ready while Mike uses the Mac. When macOS
puts the screens to sleep, release the microphone so V2T does not prevent
automatic system sleep. Restore capture automatically when Mike returns to an
awake, active session. Do not require quitting/relaunching V2T or starting its
microphone on every Fn press. Changes apply only to macOS.

The Studio Display screen and its USB audio device have separate lifecycles.
Screen sleep must therefore explicitly suspend V2T audio. A final system-sleep
notification alone is insufficient because active audio can prevent idle sleep.

## Findings and limits

- On September 15, the old Python process PID 2784 held an audio sleep assertion
  through the Studio Display for approximately 119.5 hours. Its audio connection
  stopped at 15:50:19, immediately followed by the system beginning sleep.
- The old process is identified as Python, not conclusively by script name.
  The current V2T process is confirmed to hold the same class of audio assertion.
- Existing `setup_audio_engine()` starts capture continuously. The tap discards
  samples outside dictation. The watchdog rebuilds any stopped or stale engine.
- The existing timer-gap detector assumes a delayed timer proves sleep; this is
  not reliable evidence by itself.
- Historical system-power samples averaged 20.4 W during 15:30-15:50 while the
  battery was not charging. Chrome renderers dominated recorded process activity.
  This does not establish per-process wattage or prove V2T alone caused the heat.

## Execution rules

Check each item only after completing its verification. Record failed, blocked,
pending, and not-applicable outcomes explicitly. Simulated sleep never counts as
real sleep. Actual long-sleep tests require actual elapsed time. Record every
hardware run against a code revision or patch identifier and rerun affected cases
after fixes. Keep all implementation and test artifacts under `macos/`.

## 1. Baseline

- [x] Inspect audio lifecycle, Fn handling, watchdog, and existing helper tests.
- [x] Confirm the repository was clean on develop before starting.
- [x] Create codex/macos-sleep-wake from develop.
- [x] Save this checklist in the existing repository.
- [x] Run existing macOS tests and record the baseline result.
- [ ] Record current Fn-to-audio latency and current V2T power assertions.
- [ ] Verify actual macOS notification and startup-state APIs on this machine,
      including external-display and clamshell behavior.

## 2. Implementation

- [x] Introduce explicit ready, recording, suspended, recovering, and shutting-down
      states with independently testable transition logic.
- [x] Serialize lifecycle transitions; prevent concurrent Fn processing, engine
      rebuilds, and audio callbacks from violating suspended state.
- [x] Register screen-sleep/wake and system-sleep/wake observers; incorporate
      current session state so background wakes do not reopen the microphone.
- [x] Initialize from current screen/session state; launching while unattended
      must not briefly open the microphone before discovering suspension.
- [x] Suspend before teardown: clear Fn state, invalidate stale work, stop and
      release the audio engine/tap, and prevent new recording while suspended.
- [x] Gate watchdog recovery on desired audio state. Suspension is healthy and
      must not trigger a rebuild, even after many timer ticks.
- [x] Replace timer-gap-as-proof-of-sleep with notification/state-based handling;
      use appropriate clocks for durations and recovery deadlines.
- [x] Restore Fn monitoring and rebuild the current default input only when the
      user returns. Ignore duplicate events and obsolete rebuild completions.
- [x] Confirm live audio callbacks before reporting Ready; bound startup attempts
      and keep retries responsive without busy loops.
- [x] Handle microphone/device changes, changed sample rate, unavailable devices,
      denied permission, and errors with an accurate visible status.
- [x] Define interrupted-recording and queued-output handling: clear phantom
      capture; prevent automatic typing on the lock screen or after suspension.
      Preserve already-completed user dictation for deliberate recovery where
      practical, rather than silently delivering it into a different application.
- [x] Clean up observers, timers, Fn listener, engine, and queued work on exit.
- [x] Log timestamped state transitions, device identity, recovery timing, and
      errors without recording audio or dictated text in test diagnostics.
- [x] Update macOS documentation to describe behavior and recovery.

## 3. Automated tests

Use unittest and fake clocks, audio adapters, notification sources, keyboard
events, and output adapters. Unit tests must not sleep the computer, access the
microphone, load transcription models, or type into another app. Add adapter
integration tests to cover actual application wiring beyond pure helpers.

- [x] Normal startup, Fn press/release, repeated dictation, and long dictation.
- [x] Screen sleep, system sleep, both orders, repeated events, and startup asleep.
- [x] Screen wake, system wake, reversed/duplicate events, and maintenance wake.
- [x] Lock/unlock and inactive/active session transitions; no capture while suspended.
- [x] Watchdog ticks never restart intentionally suspended audio.
- [x] Active-state recovery for stopped engine, silent tap, missing first callback,
      startup errors, and eventual success.
- [x] Simulated short, hour-long, overnight, and multi-day sleeps.
- [x] Forward/backward wall-clock changes and delayed event loop without real sleep.
- [x] Fn held across sleep, lost release, press during recovery, and concurrent events.
- [x] Late tap callback, sleep during rebuild, and obsolete rebuild completion.
- [x] Device loss/replacement, reconnect, different sample rate, and no input device.
- [x] Permission denial and teardown exceptions without false Ready status.
- [x] Sleep during capture, queued transcription, and completion while suspended;
      no phantom/duplicate text or output into the lock screen.
- [x] Quit from ready, suspended, and recovering states.
- [ ] Repeated randomized event sequences preserve lifecycle invariants and do not
      accumulate engines, taps, listeners, timers, or queued retries.
- [x] Run the complete macOS suite; record results and fix failures.
- [x] Confirm the diff contains no Windows/Ubuntu implementation changes.

## 4. Hardware test harness

- [ ] Give each run an ID, prerequisites, expected behavior, actual result, and evidence.
- [ ] Capture V2T lifecycle events plus macOS sleep/wake and power-source records.
- [ ] Check audio assertions attributable to V2T, identifying unrelated blockers
      separately. Do not treat a nonzero global assertion as proof V2T failed.
- [ ] Suppress typing using the existing test mode; use known test speech and a
      dedicated destination for any deliberate end-to-end typing check.
- [ ] Verify wake/recovery arrangements before unattended sleep tests. Record and
      cancel only test-owned wake schedules; restore temporary settings afterward.
- [ ] Account for Codex/test tools themselves preventing sleep. Observation must
      not keep the Mac awake or invalidate the condition being tested.
- [ ] Establish measured release/recovery timing and resource-count baselines.

## 5. Real laptop test matrix

Run the core sleep/wake cases on AC and battery, using built-in and Studio Display
microphones where physically supported. Record exceptions rather than inventing
impossible configurations. Exercise relevant combinations of power/device changes
and sleep duration. Physical lid/cable actions and spoken checks need Mike.

| ID | Scenario | Status |
| --- | --- | --- |
| H01 | Automatic screen sleep while V2T waits | PASS: built-in display on battery, 17:26–18:03; other configurations pending |
| H02 | Actual automatic system sleep after screen sleep | Pending |
| H03 | Explicit Apple-menu system sleep | PARTIAL: docked request remained DarkWake; full sleep occurred for 6s after undocking (19:11:02–19:11:08) |
| H04 | Lid close/open without external display | PASS on battery: 28m49s interval, two dark wakes, lid-triggered return; immediate dictation worked |
| H05 | Supported closed-lid Studio Display use; correct clamshell behavior | Dictation/release/recovery working; sustained docked full sleep unresolved |
| H06 | Display-only sleep/wake without system sleep | PASS: built-in display on battery; same process resumed dictation |
| H07 | Lock/unlock and user-session changes | Pending |
| H08 | Approximately 30-second and 5-minute system sleeps | Pending |
| H09 | Approximately 1-hour system sleep | Pending |
| H10 | At least 8-hour overnight sleep | Pending |
| H11 | 24-48-hour unattended sleep reproducing the original usage | Pending |
| H12 | Disconnect/reconnect AC while asleep; wake on changed power source | Pending |
| H13 | Disconnect/reconnect Studio Display while asleep | Pending |
| H14 | Wake with a different default microphone or no input device | Pending |
| H15 | Sleep during dictation and during transcription | Pending |
| H16 | At least 20 repeated rapid sleep/wake cycles | Pending |
| H17 | Actual maintenance/network wake, if reproducible; audio remains closed | Two dark wakes observed during H04; no V2T reactivation recorded; continuous app-log corroboration pending |
| H18 | Immediate first dictation after return; capture opening words | Pending |
| H19 | Microphone failure then reconnect; automatic recovery | Pending |
| H20 | Launch/restart V2T while screens/session are inactive | Pending |
| H21 | Dock/device change while awake, then sleep and wake | PARTIAL PASS: reconnect with external Apple keyboard and Studio mic succeeded after restart; docked sleep/wake remains pending |

For each applicable case verify microphone release during suspension, no watchdog
restart, actual system sleep when expected, automatic recovery without relaunch,
current-device selection, and first-word capture. A screen going dark is not proof
of system sleep. Do not intentionally exhaust the battery to force emergency sleep.
Hardware-dependent deep-sleep/standby states must be observed in logs rather than
assumed from elapsed time. Mark unobserved maintenance/deep-sleep states pending.

## 6. Acceptance and closeout

- [ ] V2T releases its audio sleep blocker on suspension.
- [ ] Controlled automatic system sleep is confirmed in macOS records.
- [ ] Suspended watchdog ticks and maintenance wakes never reopen capture.
- [ ] User return restores dictation automatically with measured latency.
- [ ] First words are captured; no phantom recordings or unexpected text insertion.
- [ ] No accumulating resources, duplicate listeners, or restart loops after cycles.
- [ ] Real overnight and extended tests pass; simulated duration tests alone do not qualify.
- [ ] Record power observations before/after under comparable conditions, without
      attributing whole-system consumption solely to V2T.
- [ ] Restore temporary test settings and remove only test-owned wake schedules.
- [ ] Review the macOS-only diff and publish a final pass/fail/pending report.

## Execution log

| Date | Step | Result |
| --- | --- | --- |
| 2026-09-15 | Repository preparation | Clean develop verified; feature branch created; plan saved. |
| 2026-09-15 | Baseline | Existing 28 macOS tests passed; PID 37929 held an audio assertion. |
| 2026-09-15 | Implementation | Notification-driven suspension, guarded recovery, and delayed-output protection implemented. |
| 2026-09-15 | Automated checks | 70 macOS tests and 1 repository regression test passed. |
| 2026-09-15 | Hardware probe | Locked startup passed; subsequent awake real-microphone probe passed 20/20 cycles (0.211–0.223 s recovery). |
| 2026-09-15 | Real lid-close sleep | Clamshell Sleep 18:06:38; lid wake 18:35:27; same V2T PID and successful immediate dictation. Two brief dark wakes documented. |
| 2026-09-15 | Real display sleep | 17:26:26 microphone assertion released with display sleep; resumed around 18:03:28 in same PID. Printing service retained network assertion; actual system sleep not observed. |

Implementation now lives in `dbdude-v2t.py`, `lifecycle.py`, and `powerstate.py`.
Automated checks pass; see [test results](sleep-wake-test-results.md). Checked
implementation items describe code and automated verification, not hardware
acceptance. Native resource-count verification remains open.
The task sidebar association is unchanged; commands and edits use the authorized
repository directly. Mike restarted regular V2T at 17:23 EDT (PID 41374). Real automatic display sleep and recovery passed; actual system sleep remains pending.

## API references

- [Screen sleep notification](https://developer.apple.com/documentation/appkit/nsworkspace/screensdidsleepnotification)
- [System wake notification](https://developer.apple.com/documentation/appkit/nsworkspace/didwakenotification)
- [Idle sleep assertion semantics](https://developer.apple.com/documentation/iokit/kiopmassertiontypepreventuseridlesystemsleep)
- [Sleep/wake registration guidance](https://developer.apple.com/library/archive/qa/qa1340/_index.html)
