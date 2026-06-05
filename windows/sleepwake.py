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
SLEEPWAKE_L2_ENABLED = False  # not implemented yet
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
