#!/usr/bin/env python3
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.
"""Unit tests for sleep/wake hardening pure helpers (macOS).

Run from the macos/ dir (or anywhere):  python3 tests/test_sleepwake.py
These tests cover ONLY the platform-agnostic pure helpers — no hardware,
no NSEvent monitor, no AVAudioEngine. They run entirely on macOS against
macos/sleepwake.py; the test scenarios mirror the Windows suite (same pure
logic), with macOS flag names and the macOS-only rebuild-decision helper.
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
    sleepwake_l2_should_rebuild,
    SLEEPWAKE_L2_RETRY_INTERVAL_S,
    sleepwake_l3_detect_resume,
    SLEEPWAKE_L3_RESUME_GAP_S,
)


# ----------------------------------------------------------------------------
# SLEEPWAKE-L1: key-state watchdog pure helper
# ----------------------------------------------------------------------------
class TestSleepwakeL1StuckFlags(unittest.TestCase):
    def test_no_flags_held_returns_empty(self):
        held = {'fn_held': False}
        pressed = {'fn_held': False}
        self.assertEqual(sleepwake_l1_stuck_flags(held, pressed), [])

    def test_genuinely_held_is_not_stuck(self):
        # The key exit-criterion: a key the user is really holding must NEVER
        # be cleared (would cut off dictation mid-sentence).
        held = {'fn_held': True}
        pressed = {'fn_held': True}
        self.assertEqual(sleepwake_l1_stuck_flags(held, pressed), [])

    def test_missed_release_is_stuck(self):
        # Our flag says held, but the key is physically up -> stuck.
        held = {'fn_held': True}
        pressed = {'fn_held': False}
        self.assertEqual(sleepwake_l1_stuck_flags(held, pressed), ['fn_held'])

    def test_multiple_stuck(self):
        held = {'fn_held': True, 'other_held': True, 'third_held': False}
        pressed = {'fn_held': False, 'other_held': False, 'third_held': False}
        self.assertEqual(sorted(sleepwake_l1_stuck_flags(held, pressed)),
                         ['fn_held', 'other_held'])

    def test_partial_stuck_preserves_genuinely_held(self):
        # fn really held, other stuck -> clear ONLY other, keep fn.
        held = {'fn_held': True, 'other_held': True}
        pressed = {'fn_held': True, 'other_held': False}
        self.assertEqual(sleepwake_l1_stuck_flags(held, pressed), ['other_held'])

    def test_missing_physical_entry_treated_as_not_pressed(self):
        held = {'fn_held': True}
        pressed = {}  # no info -> treat as not pressed -> stuck
        self.assertEqual(sleepwake_l1_stuck_flags(held, pressed), ['fn_held'])

    def test_unset_flag_never_cleared_even_if_pressed(self):
        # Flag not set; key physically down -> not "stuck", nothing to clear.
        held = {'fn_held': False}
        pressed = {'fn_held': True}
        self.assertEqual(sleepwake_l1_stuck_flags(held, pressed), [])

    def test_empty_inputs(self):
        self.assertEqual(sleepwake_l1_stuck_flags({}, {}), [])


# ----------------------------------------------------------------------------
# SLEEPWAKE-L2: self-healing audio engine pure helpers
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
        # No callback yet -> nothing to declare stale (avoid false restart at
        # startup and right after a rebuild resets the heartbeat).
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


class TestSleepwakeL2ShouldRebuild(unittest.TestCase):
    # macOS-only helper: rebuild decision from engine state + tap heartbeat.
    def test_healthy_engine_no_rebuild(self):
        self.assertFalse(sleepwake_l2_should_rebuild(engine_running=True,
                                                     heartbeat_stale=False))

    def test_engine_not_running_rebuilds(self):
        # Post-wake: macOS stopped the engine (isRunning() False).
        self.assertTrue(sleepwake_l2_should_rebuild(engine_running=False,
                                                    heartbeat_stale=False))

    def test_running_but_deaf_rebuilds(self):
        # Post-wake: engine claims running but the tap went silently deaf.
        self.assertTrue(sleepwake_l2_should_rebuild(engine_running=True,
                                                    heartbeat_stale=True))

    def test_not_running_and_stale_rebuilds(self):
        self.assertTrue(sleepwake_l2_should_rebuild(engine_running=False,
                                                    heartbeat_stale=True))


# ----------------------------------------------------------------------------
# SLEEPWAKE-L3: resume detection pure helper
# ----------------------------------------------------------------------------
class TestSleepwakeL3DetectResume(unittest.TestCase):
    def test_normal_tick_is_not_resume(self):
        # ~2s between watchdog ticks -> definitely not a sleep.
        self.assertFalse(sleepwake_l3_detect_resume(2.0))

    def test_long_dictation_gap_is_not_resume(self):
        # The watchdog timer keeps firing during recording/transcribing, so
        # per-tick gaps stay ~2s even across a 60s dictation. A sub-threshold
        # gap must NOT trip resume.
        self.assertFalse(sleepwake_l3_detect_resume(3.5))

    def test_exactly_threshold_is_not_resume(self):
        self.assertFalse(sleepwake_l3_detect_resume(SLEEPWAKE_L3_RESUME_GAP_S))

    def test_just_over_threshold_is_resume(self):
        self.assertTrue(sleepwake_l3_detect_resume(SLEEPWAKE_L3_RESUME_GAP_S + 0.01))

    def test_long_sleep_is_resume(self):
        self.assertTrue(sleepwake_l3_detect_resume(60.0))

    def test_zero_and_negative_not_resume(self):
        self.assertFalse(sleepwake_l3_detect_resume(0.0))
        self.assertFalse(sleepwake_l3_detect_resume(-3.0))

    def test_custom_threshold(self):
        self.assertTrue(sleepwake_l3_detect_resume(2.0, threshold=1.0))
        self.assertFalse(sleepwake_l3_detect_resume(0.5, threshold=1.0))


if __name__ == '__main__':
    unittest.main(verbosity=2)
