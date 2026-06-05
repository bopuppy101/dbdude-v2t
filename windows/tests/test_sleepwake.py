#!/usr/bin/env python3
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.
"""Unit tests for sleep/wake hardening pure helpers.

Run from the windows/ dir (or anywhere):  python tests/test_sleepwake.py
These tests cover ONLY the platform-agnostic pure helpers — no hardware,
no keyboard hook, no audio. SLEEPWAKE-L1.
"""

import os
import sys
import unittest

# Make `import sleepwake` work regardless of where the test is run from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sleepwake import sleepwake_l1_stuck_flags


# ----------------------------------------------------------------------------
# SLEEPWAKE-L1: key-state watchdog pure helper
# ----------------------------------------------------------------------------
class TestSleepwakeL1StuckFlags(unittest.TestCase):
    def test_no_flags_held_returns_empty(self):
        held = {'left_alt_held': False, 'shift_held': False}
        pressed = {'left_alt_held': False, 'shift_held': False}
        self.assertEqual(sleepwake_l1_stuck_flags(held, pressed), [])

    def test_genuinely_held_is_not_stuck(self):
        # The key exit-criterion: a key the user is really holding must NEVER
        # be cleared (would cut off dictation mid-sentence).
        held = {'left_alt_held': True, 'shift_held': True}
        pressed = {'left_alt_held': True, 'shift_held': True}
        self.assertEqual(sleepwake_l1_stuck_flags(held, pressed), [])

    def test_missed_release_is_stuck(self):
        # Our flag says held, but the key is physically up -> stuck.
        held = {'left_alt_held': True, 'shift_held': False}
        pressed = {'left_alt_held': False, 'shift_held': False}
        self.assertEqual(sleepwake_l1_stuck_flags(held, pressed), ['left_alt_held'])

    def test_multiple_stuck(self):
        held = {'left_alt_held': True, 'shift_held': True, 'caps_lock_held': False}
        pressed = {'left_alt_held': False, 'shift_held': False, 'caps_lock_held': False}
        self.assertEqual(sorted(sleepwake_l1_stuck_flags(held, pressed)),
                         ['left_alt_held', 'shift_held'])

    def test_partial_stuck_preserves_genuinely_held(self):
        # alt really held, shift stuck -> clear ONLY shift, keep alt.
        held = {'left_alt_held': True, 'shift_held': True}
        pressed = {'left_alt_held': True, 'shift_held': False}
        self.assertEqual(sleepwake_l1_stuck_flags(held, pressed), ['shift_held'])

    def test_missing_physical_entry_treated_as_not_pressed(self):
        held = {'left_alt_held': True}
        pressed = {}  # no info -> treat as not pressed -> stuck
        self.assertEqual(sleepwake_l1_stuck_flags(held, pressed), ['left_alt_held'])

    def test_unset_flag_never_cleared_even_if_pressed(self):
        # Flag not set; key physically down -> not "stuck", nothing to clear.
        held = {'left_alt_held': False}
        pressed = {'left_alt_held': True}
        self.assertEqual(sleepwake_l1_stuck_flags(held, pressed), [])

    def test_empty_inputs(self):
        self.assertEqual(sleepwake_l1_stuck_flags({}, {}), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
