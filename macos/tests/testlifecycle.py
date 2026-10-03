"""Deterministic lifecycle tests: no microphone, system sleep, typing or model."""
import pathlib
import random
import sys
import threading
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lifecycle import AudioLifecycle


class Audio:
    def __init__(self):
        self.opens = 0
        self.closes = 0
        self.live = False
        self.fail = False
        self.close_fail = False
        self.generation = None
    def open(self, generation):
        self.opens += 1
        self.generation = generation
        if self.fail:
            raise RuntimeError('permission denied or unavailable device')
        self.live = True
    def close(self):
        self.closes += 1
        self.live = False
        if self.close_fail:
            raise RuntimeError('cleanup failure')
    def running(self):
        return self.live


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.audio = Audio()
        self.events = []
        self.resets = []
        self.life = AudioLifecycle(self.audio, lambda: self.resets.append(True), self.events.append, lambda: self.now)
    def ready(self):
        self.life.resume()
        self.life.callback(self.life.generation)
        self.life.tick()
        self.life.release()
        self.assertEqual(self.life.state, 'ready')
    def test_startup_asleep_never_opens(self):
        for _ in range(100):
            self.life.tick()
        self.assertEqual(self.audio.opens, 0)
    def test_ready_requires_first_callback(self):
        self.life.resume()
        self.assertEqual(self.life.state, 'recovering')
        self.assertFalse(self.life.press())
        self.life.callback(self.life.generation)
        self.life.tick()
        self.assertEqual(self.life.state, 'ready')
    def test_normal_and_long_dictation(self):
        self.ready()
        for _ in range(10):
            self.assertTrue(self.life.press())
            self.now += 3600
            self.life.callback(self.life.generation)
            self.life.tick()
            self.assertEqual(self.life.state, 'recording')
            self.assertTrue(self.life.release())
        self.assertEqual(self.audio.opens, 1)
    def test_sleep_durations_watchdog_and_duplicate_notifications(self):
        for duration in (30, 300, 3600, 28800, 172800):
            with self.subTest(duration=duration):
                self.ready()
                self.life.suspend()
                count = self.audio.opens
                epoch = self.life.epoch
                self.now += duration
                for _ in range(30):
                    self.life.suspend()
                    self.life.tick()
                self.assertEqual(self.audio.opens, count)
                self.assertEqual(self.life.epoch, epoch)
                self.assertFalse(self.audio.live)
                self.ready()
                self.life.resume()
                self.assertEqual(self.audio.opens, count + 1)
    def test_old_callback_and_output_invalid_after_sleep(self):
        self.ready()
        generation, epoch = self.life.generation, self.life.epoch
        self.life.press()
        self.life.suspend()
        self.ready()
        consumed = []
        self.assertFalse(self.life.callback(generation, lambda: consumed.append(True)))
        self.assertFalse(self.life.can_deliver(epoch))
        self.assertEqual(consumed, [])
    def test_fn_held_across_wake_requires_release(self):
        self.ready()
        self.life.press()
        self.life.suspend()
        self.life.resume()
        self.life.callback(self.life.generation)
        self.life.tick()
        self.assertFalse(self.life.press())
        self.life.release()
        self.assertTrue(self.life.press())
    def test_start_failure_and_eventual_recovery(self):
        self.audio.fail = True
        self.life.resume()
        for _ in range(100):
            self.life.tick()
        self.assertEqual(self.audio.opens, 1)
        self.assertEqual(self.life.state, 'recovering')
        self.audio.fail = False
        self.now += 2
        self.life.tick()
        self.life.callback(self.life.generation)
        self.life.tick()
        self.assertEqual(self.life.state, 'ready')
    def test_missing_first_callback_retries(self):
        self.life.resume()
        self.now = 2
        self.life.tick()
        self.assertEqual(self.audio.opens, 2)
        self.assertEqual(self.life.state, 'recovering')
    def test_stopped_or_silent_device_rebuild(self):
        for stopped in (False, True):
            self.ready()
            self.now += 3
            if stopped:
                self.audio.live = False
            before = self.audio.opens
            self.life.tick()
            self.assertEqual(self.audio.opens, before + 1)
            self.assertEqual(self.life.state, 'recovering')
            self.life.suspend()
    def test_delayed_loop_with_live_audio_does_not_imply_sleep(self):
        self.ready()
        epoch = self.life.epoch
        self.now += 86400
        self.life.callback(self.life.generation)
        self.life.tick()
        self.assertEqual(self.life.epoch, epoch)
        self.assertEqual(self.audio.opens, 1)
    def test_cleanup_exception_stays_suspended(self):
        self.ready()
        self.audio.close_fail = True
        self.life.suspend()
        self.life.tick()
        self.assertFalse(self.life.desired)
        self.assertFalse(self.life.can_deliver(self.life.epoch))
        self.assertEqual(self.audio.opens, 1)
    def test_shutdown_from_all_states(self):
        for state in ('suspended', 'recovering', 'ready', 'recording'):
            self.setUp()
            if state != 'suspended':
                self.life.resume()
            if state in ('ready', 'recording'):
                self.ready()
            if state == 'recording':
                self.life.press()
            self.life.shutdown()
            count = self.audio.opens
            self.life.resume()
            self.life.tick()
            self.assertEqual(self.audio.opens, count)
            self.assertEqual(self.life.state, 'shutting-down')
    def test_callback_does_not_deadlock_teardown(self):
        self.ready()
        results = []
        with self.life.lock:
            worker = threading.Thread(target=lambda: results.append(self.life.callback(self.life.generation)))
            worker.start()
            worker.join(timeout=1)
            self.assertFalse(worker.is_alive())
        self.assertEqual(results, [False])
    def test_sleep_during_open_invalidates_completion(self):
        original = self.audio.open
        def opening(generation):
            original(generation)
            self.life.suspend('sleep during rebuild')
        self.audio.open = opening
        self.life.resume()
        self.assertEqual(self.life.state, 'suspended')
        self.assertFalse(self.audio.live)
        self.assertFalse(self.life.callback(self.audio.generation))
        self.life.tick()
        self.assertEqual(self.audio.opens, 1)

    def test_failed_teardown_does_not_open_second_engine(self):
        self.ready()
        self.audio.close_fail = True
        self.audio.live = False
        self.now += 3
        self.life.tick()
        self.assertEqual(self.audio.opens, 1)
        self.assertEqual(self.life.state, 'recovering')
        self.audio.close_fail = False
        self.now += 2
        self.life.tick()
        self.assertEqual(self.audio.opens, 2)

    def test_input_listener_rearmed_on_recovery_not_on_suspended_ticks(self):
        calls = []
        self.life.prepare_input = lambda: calls.append(True)
        self.ready()
        self.audio.live = False
        self.now += 3
        self.life.tick()
        self.assertEqual(len(calls), 2)
        self.life.suspend()
        for _ in range(20):
            self.life.tick()
        self.assertEqual(len(calls), 2)

    def test_randomized_invariants(self):
        randomizer = random.Random(935)
        for _ in range(10000):
            action = randomizer.choice(('resume', 'suspend', 'press', 'release', 'tick', 'callback'))
            self.now += randomizer.random()
            if action == 'callback':
                self.life.callback(randomizer.choice((self.life.generation, self.life.generation - 1)))
            else:
                getattr(self.life, action)()
            if not self.life.desired:
                self.assertFalse(self.audio.live)
                self.assertEqual(self.life.state, 'suspended')
            if self.life.state in ('ready', 'recording'):
                self.assertTrue(self.life.desired)

if __name__ == '__main__':
    unittest.main()
