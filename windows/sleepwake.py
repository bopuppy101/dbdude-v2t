#!/usr/bin/env python3
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.
"""
Sleep/Wake hardening helpers for dbdude-v2t (Windows).

This module isolates the sleep/wake fix logic so each layer is independently
testable and togglable. The *pure* helpers here have no I/O and are unit-tested
in tests/test_sleepwake.py; they are platform-agnostic and intended for reuse
when porting the fix to Ubuntu and macOS. Only the Win32 glue (GetAsyncKeyState)
is Windows-specific.

Layer tags:
  SLEEPWAKE-L1  key-state watchdog   (phantom-record fix)
  SLEEPWAKE-L2  audio self-heal      (stops-working fix)      [not yet implemented]
  SLEEPWAKE-L3  resume re-arm         (catch-all)             [not yet implemented]
"""

import ctypes

# Per-layer enable flags — flip a layer off to isolate a regression / retrofit.
SLEEPWAKE_L1_ENABLED = True
SLEEPWAKE_L2_ENABLED = True
SLEEPWAKE_L3_ENABLED = False  # not implemented yet


# ============================================================================
# SLEEPWAKE-L1: Key-state watchdog (fixes phantom recording after sleep/wake)
# ============================================================================
# Held-flags are set on key-press and cleared on key-release by the keyboard
# hook. If a release is lost across a sleep transition, a flag stays stuck True
# and recording runs with no key held (e.g. transcribing the TV). This watchdog
# compares our flags against the OS's REAL key state and clears any that are stuck.
#
# Ground truth comes from Win32 GetAsyncKeyState, NOT keyboard.is_pressed().
# The keyboard library tracks key state from the SAME hook that feeds our flags,
# so a missed release leaves BOTH our flag and is_pressed() wrongly True — they
# would agree and the stuck flag would go undetected. GetAsyncKeyState queries
# the OS real-time key state independent of the hook, so it catches the miss.

# held-flag name -> Win32 virtual-key code
SLEEPWAKE_L1_VK = {
    'left_alt_held':  0xA4,  # VK_LMENU
    'right_alt_held': 0xA5,  # VK_RMENU
    'shift_held':     0x10,  # VK_SHIFT (either shift)
    'caps_lock_held': 0x14,  # VK_CAPITAL (high bit = physically down)
    'left_ctrl_held': 0xA2,  # VK_LCONTROL
}


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


def sleepwake_l1_read_physical_keys(flag_names):
    """SLEEPWAKE-L1 (Windows glue): real key state via Win32 GetAsyncKeyState.

    Independent of the keyboard-library hook, so it catches releases the hook
    missed across sleep/wake. Returns {flag_name: bool} for the given names.
    """
    pressed = {}
    for name in flag_names:
        vk = SLEEPWAKE_L1_VK.get(name)
        if vk is None:
            pressed[name] = False
            continue
        # High-order bit (0x8000) set => key is currently physically down.
        pressed[name] = bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
    return pressed
# ============================================================================
# END SLEEPWAKE-L1
# ============================================================================


# ============================================================================
# SLEEPWAKE-L2: Self-healing audio worker (fixes "stops working" after sleep/wake)
# ============================================================================
# The audio worker opens the mic stream once. On wake the device handle is stale,
# so the stream either throws (worker dies -> app exits) or goes silently deaf
# (callbacks stop firing, app looks alive but captures nothing). Layer 2 makes the
# worker self-healing: it reopens the stream on failure, and detects a silently-
# deaf stream via a callback heartbeat and reopens that too. The app never exits
# on a transient audio failure.
#
# Retry policy is a FLAT fixed interval — deliberately NOT exponential/unbounded
# backoff (which can grow to minutes and feel like a hang). It retries forever
# only in the sense of "until shutdown"; the caller gates the loop on the shutdown
# event and uses an interruptible wait so exits stay instant.

SLEEPWAKE_L2_RETRY_INTERVAL_S = 2.0   # fixed delay between stream-reopen attempts
SLEEPWAKE_L2_STALE_TIMEOUT_S = 1.0    # no callback for this long => stream is deaf


def sleepwake_l2_next_retry_delay(attempt=None):
    """SLEEPWAKE-L2 (pure): delay before the next stream-reopen attempt.

    Always the same fixed interval regardless of how many attempts have failed.
    The `attempt` arg is accepted and intentionally ignored — it documents that
    we deliberately do NOT grow the delay (no exponential/unbounded backoff).
    """
    return SLEEPWAKE_L2_RETRY_INTERVAL_S


def sleepwake_l2_stream_is_stale(last_callback_ts, now, timeout=SLEEPWAKE_L2_STALE_TIMEOUT_S):
    """SLEEPWAKE-L2 (pure): True if the audio stream appears deaf.

    The audio callback stamps the time it last fired. While a healthy stream is
    open, callbacks fire continuously (every blocksize). If none has fired within
    `timeout` seconds, the stream has gone silent and should be reopened.

    Args:
        last_callback_ts: timestamp of the last callback, or None if none yet.
        now: current timestamp.
        timeout: max allowed seconds between callbacks.
    Returns:
        bool. Returns False when last_callback_ts is None (stream not yet
        producing callbacks — nothing to declare stale), and False for a
        non-positive elapsed time (clock anomaly), to avoid false restarts.
    """
    if last_callback_ts is None:
        return False
    return (now - last_callback_ts) > timeout
# ============================================================================
# END SLEEPWAKE-L2
# ============================================================================
