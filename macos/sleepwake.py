#!/usr/bin/env python3
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).
"""
Sleep/Wake hardening helpers for dbdude-v2t (macOS).

This is the macOS port of windows/sleepwake.py. The *pure* helpers (no I/O,
unit-tested in tests/test_sleepwake.py) are identical to the Windows ones —
they are platform-agnostic logic over state and timestamps. Only the glue
differs:

  Windows glue                         macOS glue
  ------------------------------       ------------------------------------
  Win32 GetAsyncKeyState (L1)          NSEvent.modifierFlags() class method
  sounddevice stream reopen (L2)       full AVAudioEngine rebuild
  keyboard.unhook_all/re-hook (L3)     NSEvent monitor remove + re-add

Layer tags:
  SLEEPWAKE-L1  key-state watchdog   (phantom-record fix)
  SLEEPWAKE-L2  audio self-heal      (stops-working fix)
  SLEEPWAKE-L3  resume re-arm        (catch-all)

macOS-SPECIFIC DESIGN NOTE (L1 ground truth):
The Windows L1 watchdog polls GetAsyncKeyState every main-loop tick (~50Hz).
The direct macOS analog, CGEventSourceFlagsState polling at 50Hz, hits a
documented macOS bug that PERMANENTLY blocks the API (see
macos/docs/fn-key-detection-approaches.md, approach #3 — required pkill -9).
So on macOS the L1 ground-truth check runs at LOW frequency (the ~2s watchdog
timer), ONLY while recording, via the NSEvent.modifierFlags() class method.
The sleep-induced stuck flag is primarily handled by L3's resume re-arm.
"""

# Per-layer enable flags — flip a layer off to isolate a regression / retrofit.
SLEEPWAKE_L1_ENABLED = True
SLEEPWAKE_L2_ENABLED = True
SLEEPWAKE_L3_ENABLED = True


# ============================================================================
# SLEEPWAKE-L1: Key-state watchdog (fixes phantom recording after sleep/wake)
# ============================================================================
# The _fn_held flag is set on FN-press and cleared on FN-release by the NSEvent
# monitor. If the release event is lost (across a sleep transition, or if the
# monitor goes deaf), the flag stays stuck True and recording runs with no key
# held (e.g. transcribing the TV). This watchdog compares the flag against the
# REAL hardware modifier state and clears it when stuck.

# Debounce: a flag must be observed stuck on this many consecutive watchdog
# ticks before it is cleared, so a single misread can't cut off real dictation.
SLEEPWAKE_L1_DEBOUNCE_TICKS = 2


def sleepwake_l1_stuck_flags(held_flags, physically_pressed):
    """SLEEPWAKE-L1 (pure): return names of held-flags that are stuck.

    A flag is "stuck" when our state says it is held (True) but the physical
    keyboard reports it is NOT pressed. Those flags should be cleared.

    Args:
        held_flags: dict {flag_name: bool} — our tracked state.
        physically_pressed: dict {flag_name: bool} — real key state.
                            A missing entry is treated as not pressed.
    Returns:
        list of flag names to clear (empty if none stuck).

    Pure function: no I/O, fully unit-testable on any platform. Critically, a
    flag that is genuinely held (held=True AND pressed=True) is NEVER returned,
    so the watchdog can never cut off an in-progress dictation.
    """
    return [name for name, is_held in held_flags.items()
            if is_held and not physically_pressed.get(name, False)]


def sleepwake_l1_fn_physically_down():
    """SLEEPWAKE-L1 (macOS glue): real FN/Globe key state, independent of the
    NSEvent monitor callback stream.

    Uses the +[NSEvent modifierFlags] CLASS method, which reads the current
    hardware modifier state directly — so it catches a release the monitor
    missed across sleep/wake.

    CALL FREQUENCY WARNING: call this at low frequency only (the ~2s watchdog
    tick, while recording). Do NOT poll at 50Hz — see module docstring re: the
    CGEventSourceFlagsState permanent-block bug on this machine.
    """
    from Cocoa import NSEvent, NSFunctionKeyMask
    return bool(NSEvent.modifierFlags() & NSFunctionKeyMask)
# ============================================================================
# END SLEEPWAKE-L1
# ============================================================================


# ============================================================================
# SLEEPWAKE-L2: Self-healing audio engine (fixes "stops working" after sleep/wake)
# ============================================================================
# The AVAudioEngine is started once at app launch and never touched again.
# macOS stops the engine on system sleep and on audio-configuration changes
# (wake, default-device switch): after wake, isRunning() is often False, or the
# input tap goes silently deaf (callbacks stop firing while the app looks
# alive). Layer 2 detects both — a not-running engine, and a deaf tap via a
# callback heartbeat — and does a FULL engine rebuild (new engine, re-read
# input format/sample rate, reinstall tap, start).
#
# Retry policy is a FLAT fixed interval — deliberately NOT exponential/unbounded
# backoff (which can grow to minutes and feel like a hang). The watchdog timer's
# tick interval IS the retry cadence: one rebuild attempt per tick until healthy.

SLEEPWAKE_L2_RETRY_INTERVAL_S = 2.0   # fixed delay between rebuild attempts
SLEEPWAKE_L2_STALE_TIMEOUT_S = 2.0    # no tap callback for this long => engine is deaf
                                      # (healthy tap fires every ~85ms @ 4096 frames)


def sleepwake_l2_next_retry_delay(attempt=None):
    """SLEEPWAKE-L2 (pure): delay before the next engine-rebuild attempt.

    Always the same fixed interval regardless of how many attempts have failed.
    The `attempt` arg is accepted and intentionally ignored — it documents that
    we deliberately do NOT grow the delay (no exponential/unbounded backoff).
    """
    return SLEEPWAKE_L2_RETRY_INTERVAL_S


def sleepwake_l2_stream_is_stale(last_callback_ts, now, timeout=SLEEPWAKE_L2_STALE_TIMEOUT_S):
    """SLEEPWAKE-L2 (pure): True if the audio tap appears deaf.

    The tap callback stamps the time it last fired. While a healthy engine is
    running, tap callbacks fire continuously (every buffer, independent of the
    recording flag). If none has fired within `timeout` seconds, the engine has
    gone silent and should be rebuilt.

    Args:
        last_callback_ts: timestamp of the last callback, or None if none yet.
        now: current timestamp.
        timeout: max allowed seconds between callbacks.
    Returns:
        bool. Returns False when last_callback_ts is None (engine not yet
        producing callbacks — nothing to declare stale), and False for a
        non-positive elapsed time (clock anomaly), to avoid false restarts.
    """
    if last_callback_ts is None:
        return False
    return (now - last_callback_ts) > timeout


def sleepwake_l2_should_rebuild(engine_running, heartbeat_stale):
    """SLEEPWAKE-L2 (pure): decide whether the AVAudioEngine needs a rebuild.

    Rebuild when the engine reports not-running, OR when it claims to be
    running but the tap heartbeat says it is deaf. (macOS-specific helper —
    the Windows port has no engine-running concept, only a stream.)
    """
    return (not engine_running) or heartbeat_stale
# ============================================================================
# END SLEEPWAKE-L2
# ============================================================================


# ============================================================================
# SLEEPWAKE-L3: Resume re-arm via time-gap detection (catch-all)
# ============================================================================
# The process can't be notified mid-sleep (it's frozen), so we infer a resume
# AFTER it happens: the watchdog timer ticks every ~2s, so a multi-second gap
# between two ticks means the process was suspended (i.e. the machine slept).
# On detecting that, the caller does a full re-arm — clear FN/recording state,
# DISCARD any phantom audio (never transcribe it), remove + re-add the NSEvent
# monitor, force an engine rebuild — and prints a RESUME DETECTED console line.

SLEEPWAKE_L3_RESUME_GAP_S = 5.0  # tick gap beyond this => system was asleep


def sleepwake_l3_detect_resume(elapsed_seconds, threshold=SLEEPWAKE_L3_RESUME_GAP_S):
    """SLEEPWAKE-L3 (pure): True if the gap between watchdog ticks indicates a sleep.

    Normal ticks are ~2s apart; recording/transcribing don't block the timer.
    Only a suspended (slept) process produces a gap beyond the threshold, so a
    long dictation is NOT mistaken for sleep — the timer was firing the whole time.

    Args:
        elapsed_seconds: wall-clock seconds since the previous tick.
        threshold: gap above which we declare a resume.
    Returns:
        bool (strictly greater-than; non-positive elapsed returns False).
    """
    return elapsed_seconds > threshold
# ============================================================================
# END SLEEPWAKE-L3
# ============================================================================
