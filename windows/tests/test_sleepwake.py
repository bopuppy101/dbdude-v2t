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

from sleepwake import (
    sleepwake_l1_stuck_flags,
    sleepwake_l2_next_retry_delay,
    sleepwake_l2_stream_is_stale,
    SLEEPWAKE_L2_RETRY_INTERVAL_S,
)


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


# ----------------------------------------------------------------------------
# SLEEPWAKE-L2: self-healing audio worker pure helpers
# ----------------------------------------------------------------------------
class TestSleepwakeL2RetryDelay(unittest.TestCase):
    def test_delay_is_the_fixed_interval(self):
        self.assertEqual(sleepwake_l2_next_retry_delay(), SLEEPWAKE_L2_RETRY_INTERVAL_S)

    def test_delay_never_grows_with_attempts(self):
        # The whole point: NO exponential/unbounded backoff.
        delays = [sleepwake_l2_next_retry_delay(attempt=n) for n in range(0, 100)]
        self.assertEqual(set(delays), {SLEEPWAKE_L2_RETRY_INTERVAL_S})

    def test_delay_is_positive(self):
        self.assertGreater(sleepwake_l2_next_retry_delay(), 0)


class TestSleepwakeL2StreamIsStale(unittest.TestCase):
    def test_none_timestamp_is_not_stale(self):
        # No callback yet -> nothing to declare stale (avoid false restart at startup).
        self.assertFalse(sleepwake_l2_stream_is_stale(None, now=100.0, timeout=1.0))

    def test_recent_callback_is_not_stale(self):
        self.assertFalse(sleepwake_l2_stream_is_stale(100.0, now=100.5, timeout=1.0))

    def test_old_callback_is_stale(self):
        self.assertTrue(sleepwake_l2_stream_is_stale(100.0, now=101.5, timeout=1.0))

    def test_exactly_at_timeout_is_not_stale(self):
        # Strictly greater-than -> exactly at the boundary is still OK.
        self.assertFalse(sleepwake_l2_stream_is_stale(100.0, now=101.0, timeout=1.0))

    def test_clock_anomaly_negative_elapsed_is_not_stale(self):
        # now < last (clock jumped back) -> do not declare stale.
        self.assertFalse(sleepwake_l2_stream_is_stale(100.0, now=99.0, timeout=1.0))

    def test_uses_default_timeout(self):
        self.assertTrue(sleepwake_l2_stream_is_stale(0.0, now=10.0))


if __name__ == '__main__':
    unittest.main(verbosity=2)
