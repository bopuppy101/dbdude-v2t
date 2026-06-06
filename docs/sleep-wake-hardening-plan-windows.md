# Sleep/Wake Hardening — Implementation Plan (Windows)

**Target:** `windows/dbdude-v2t.py` (Windows dialect first)
**Started:** 2026-06-05
**Status:** Plan approved for tracking — **not yet approved to start coding.**

## Background

Two intermittent bugs appear after the machine sleeps and wakes. Both stem from
one root cause: **nothing re-initializes audio + keyboard + held-key state after a
system resume.**

- **Bug A — Phantom record.** Push-to-talk held-flags (`left_alt_held`,
  `shift_held`) are set on key-press and only cleared on key-release, with no
  re-validation against the physical key. If a release event is lost across the
  sleep transition, the flag stays stuck `True` → recording runs with no key held
  (e.g. it transcribes the TV).
- **Bug B — Stops working.** `sd.InputStream` is opened once in the audio worker
  (`dbdude-v2t.py:1305`). On wake it either throws (worker thread dies → main loop
  exits the whole app at `:1569`) or goes silently deaf (no callbacks, app looks
  alive but captures nothing). There is no retry or re-arm.

## Approach (agreed)

Build **three complementary layers**, **Windows-first**, **one at a time**.
Each layer must be **bulletproof before moving to the next** — unit tests +
non-sleep regression + repeated sleep/wake repro **over several days** (the bug is
intermittent, so a single clean wake proves nothing).

### Delimitation convention (so layers stay isolatable / retrofittable)

- Every layer's code (pure helper + main-loop wiring + tests) is wrapped in
  grep-able banner comments tagged `SLEEPWAKE-L1`, `SLEEPWAKE-L2`, `SLEEPWAKE-L3`.
- Each layer has a module-level enable flag (`SLEEPWAKE_L1_ENABLED`, etc.) so any
  single layer can be toggled off to isolate a regression or retrofit later.
- Pure helpers are platform-agnostic (logic over state/timestamps only) so they can
  be reused when porting to Ubuntu and macOS. (macOS uses AVAudioEngine, so only its
  audio glue differs.)

### "Bulletproof" exit criteria for each layer

1. Unit tests for the pure helper pass across all state combinations.
2. No regression on normal use — Left Alt+Shift still records/stops exactly as today,
   repeatedly, with no missed captures.
3. The targeted bug does not recur across **multiple** sleep/wake cycles over days.
4. No new failure introduced (e.g. watchdog must never clear a flag while the key is
   genuinely held and cut off dictation).

---

## Layer 1 — Key-state watchdog (fixes Bug A: phantom record)

Tag: `SLEEPWAKE-L1` · Flag: `SLEEPWAKE_L1_ENABLED`

- [x] Write pure helper: given held-flags state + physical key status, return which
      flags are stuck and must be cleared. → `windows/sleepwake.py` `sleepwake_l1_stuck_flags`
- [x] Add unit tests for the helper (key held, key up, stuck-true, correct-false, …).
      → `windows/tests/test_sleepwake.py` (8 tests, all green)
- [x] Wire into the main loop: each tick, re-sync flags vs **Win32 `GetAsyncKeyState`**
      (NOT `keyboard.is_pressed()` — see design note below); clear stuck flags, and when
      a stuck flag was holding recording on, stop AND **discard** the phantom audio
      (do not transcribe it). 2-poll debounce so a single misread can't cut off genuine
      dictation. → `dbdude-v2t.py` main loop, `SLEEPWAKE-L1` block.
- [x] Wrap all of the above in `SLEEPWAKE-L1` banners + enable flag.
- [x] **Test:** unit tests green (8/8). Also: `py_compile` clean; `GetAsyncKeyState`
      glue smoke-tested on-machine (all-False with no keys held).
- [x] **Test:** non-sleep regression — normal Left Alt+Shift push-to-talk unaffected.
      2026-06-05: 4 clean paired record/transcribe cycles, zero SLEEPWAKE-L1 lines
      (no false positives), running from source.
- [ ] **Test:** sleep/wake repeatedly → no phantom recording. *(needs manual run)*
- [ ] **Bulletproof sign-off** (multi-day real use) before starting Layer 2.

## Layer 2 — Self-healing audio worker (fixes Bug B: stops working)

Tag: `SLEEPWAKE-L2` · Flag: `SLEEPWAKE_L2_ENABLED`

> **Design constraint (user, 2026-06-05):** NO unbounded/exponential backoff — it can
> grow to minutes and feel like a hang. Use a **fixed interval** (default ~2s, retry
> forever) or at most a **capped** ramp (e.g. 0.5→1→2s, then hold at 2s). Never grow
> without bound, never give up (we always want the mic back). Retries run only in the
> audio worker thread so the main loop/hotkeys/systray never freeze; every retry is
> logged + reflected in the tray so it is never a silent wait. Decide exact numbers
> when we reach this layer; default to the simple fixed-interval unless agreed otherwise.

- [x] Wrap `sd.InputStream` in a **capped** retry loop (fixed interval, default ~2s)
      so the worker reopens instead of dying on error. NO unbounded backoff.
- [x] Add a callback heartbeat so a silently-deaf stream is detected and restarted.
      → `last_audio_callback_ts` stamped each callback; `sleepwake_l2_stream_is_stale`.
- [x] Stop the main loop from exiting the app on a transient audio failure.
      → self-healing worker keeps the thread alive; reopens instead of returning.
- [x] Extract retry/backoff decision into a pure, unit-testable helper.
      → `sleepwake_l2_next_retry_delay` + `sleepwake_l2_stream_is_stale` in `sleepwake.py`.
- [x] Wrap all of the above in `SLEEPWAKE-L2` banners + enable flag (`SLEEPWAKE_L2_ENABLED = True`).
- [x] **Test:** unit tests for retry/backoff logic green. (9 L2 tests; 17 total all green.)
- [x] **Test:** non-sleep regression — normal recording unaffected (2026-06-05 console log clean).
- [~] **Test:** device loss + sleep/wake.
      - SLEEP/WAKE (2026-06-05): 19-min auto-sleep, audio survived cleanly, no SLEEPWAKE-L2
        lines needed, dictation worked instantly on wake. App stayed up. PASS (soft case / no break).
      - HARD UNPLUG (2026-06-05): pulled Elgato USB-C; reopen did NOT recover, required restart.
        ROOT CAUSE: PortAudio enumerates devices once at init and does not see hot-plugged
        devices; a plain reopen grabs the stale/dead handle. Real recovery needs a PortAudio
        re-init (sd._terminate()/_initialize()) + re-resolve device. **Deferred to Layer 3's
        resume re-arm** (user only cares about sleep/wake; this machine survives sleep cleanly,
        so the hard path isn't triggered by sleeping here).
- [ ] **Bulletproof sign-off** (multi-day real use) before starting Layer 3.

> **Known limitation (2026-06-05):** Layer 2 recovers SOFT audio failures (stream throws or
> goes deaf, device still present). It does NOT recover a HARD device-loss (device leaves the
> USB bus and returns) — that requires a PortAudio re-init, which is folded into Layer 3.

## Layer 3 — Resume re-arm via time-gap detection (catch-all)

Tag: `SLEEPWAKE-L3` · Flag: `SLEEPWAKE_L3_ENABLED`

- [x] Write pure helper: detect a sleep from the wall-clock gap between main-loop
      ticks (threshold ~5s, tunable). → `sleepwake_l3_detect_resume` in `sleepwake.py`.
- [x] Add unit tests for the gap detector. (7 tests incl. long-dictation-not-resume.)
- [x] On detected resume (Option B): clear all state flags + `recording_event` (+ drain
      phantom audio), `unhook_all` + re-register keyboard hooks (revives push-to-talk if the
      hook died on wake), print a console `RESUME DETECTED` line. Audio recovery on resume is
      handled by Layer 2's stale-stream detector.
      **DEFERRED (Option A TODO):** full PortAudio re-init for the hard device-loss case —
      add only if a wake is ever observed to actually kill audio on this hardware.
- [x] Wrap all of the above in `SLEEPWAKE-L3` banners + enable flag (`SLEEPWAKE_L3_ENABLED = True`).
- [x] **Test:** unit tests green (7 L3; 24 total). py_compile clean; all 3 flags True.
- [ ] **Test:** non-sleep regression — normal push-to-talk; NO spurious RESUME lines. *(manual)*
- [ ] **Test:** repeated sleep/wake → `RESUME DETECTED` prints, push-to-talk still works
      after wake, no phantom recording. *(manual)*
- [ ] **Bulletproof sign-off** (multi-day real use). NOT pushed to remote until user signs off.

---

## Port later (separate efforts, not in this plan's scope)

- [ ] Port the three layers to **Ubuntu** (`ubuntu/dbdude-v2t.py`).
- [ ] Port to **macOS** (`macos/dbdude-v2t.py`) — audio layer differs (AVAudioEngine).
