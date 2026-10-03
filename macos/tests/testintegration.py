"""Exercise actual application methods with fake macOS/audio/UI adapters."""
import contextlib
import importlib.util
import io
import itertools
from pathlib import Path
import sys
import types
import unittest
import numpy
import scipy.signal
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lifecycle import AudioLifecycle


def load_app():
    rumps = types.ModuleType('rumps')
    rumps.App = type('App', (), {})
    modules = {name: MagicMock() for name in ('mlx_whisper', 'pynput', 'pynput.keyboard', 'Cocoa', 'objc', 'powerstate')}
    modules['rumps'] = rumps
    spec = importlib.util.spec_from_file_location('v2t_test_app', Path(__file__).resolve().parents[1] / 'dbdude-v2t.py')
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.log = contextlib.redirect_stdout(io.StringIO())
        self.log.__enter__()
        self.m = load_app()
        self.app = object.__new__(self.m.V2TApp)
        self.m.app = self.app
        self.app._power_blockers = set()
        self.app._sleepwake_l1_stuck_streak = 0
        self.app.status_item = MagicMock()
        self.app.power_notifications = MagicMock()
        self.app.ui_timer = self.app.control_timer = self.app.sleepwake_timer = MagicMock()
        self.audio = MagicMock()
        self.audio.running.return_value = True
        self.m.lifecycle = AudioLifecycle(self.audio, self.m.reset_capture, self.app._lifecycle_status,
                                         prepare_input=self.m.sleepwake_l3_rearm_fn_monitor)
        self.m.sleepwake_l1_fn_physically_down = lambda: False
        self.m.session_awake.return_value = True
        self.app._sync_power()

    def tearDown(self):
        self.log.__exit__(None, None, None)

    def test_notification_orders_and_duplicates(self):
        for sleep_order in itertools.permutations(('NSWorkspaceScreensDidSleepNotification', 'NSWorkspaceWillSleepNotification')):
            for wake_order in itertools.permutations(('NSWorkspaceScreensDidWakeNotification', 'NSWorkspaceDidWakeNotification')):
                for event in sleep_order * 2:
                    self.app._power_event(event)
                self.assertFalse(self.m.lifecycle.desired)
                self.app._power_event(wake_order[0])
                self.assertFalse(self.m.lifecycle.desired)
                self.app._power_event(wake_order[1])
                self.assertTrue(self.m.lifecycle.desired)
                count = self.audio.open.call_count
                self.app._power_event(wake_order[1])
                self.assertEqual(self.audio.open.call_count, count)

    def test_maintenance_wake_keeps_audio_closed(self):
        self.app._power_event('NSWorkspaceWillSleepNotification')
        self.m.session_awake.return_value = False
        self.app._power_event('NSWorkspaceDidWakeNotification')
        for _ in range(50):
            self.app._sleepwake_watchdog(None)
        self.assertFalse(self.m.lifecycle.desired)

    def test_lock_and_inactive_session(self):
        for stop, start in (('com.apple.screenIsLocked', 'com.apple.screenIsUnlocked'),
                            ('NSWorkspaceSessionDidResignActiveNotification', 'NSWorkspaceSessionDidBecomeActiveNotification')):
            self.app._power_event(stop)
            self.assertFalse(self.m.lifecycle.desired)
            self.app._power_event(start)
            self.assertTrue(self.m.lifecycle.desired)

    def test_screen_wake_before_system_wake_waits(self):
        self.app._power_event('NSWorkspaceWillSleepNotification')
        self.app._power_event('NSWorkspaceScreensDidWakeNotification')
        self.assertFalse(self.m.lifecycle.desired)

    def test_suspend_clears_fn_and_audio(self):
        self.m._fn_held = True
        self.m.recording = True
        self.m.audio_chunks = [1, 2]
        self.m._test_fn_override[0] = True
        self.app._power_event('NSWorkspaceScreensDidSleepNotification')
        self.assertFalse(self.m._fn_held)
        self.assertFalse(self.m.recording)
        self.assertFalse(self.m._test_fn_override[0])
        self.assertEqual(self.m.audio_chunks, [])
        self.m.recording_control_tick()
        self.assertTrue(self.m.transcription_queue.empty())

    def test_fn_only_starts_after_ready(self):
        self.m._fn_held = True
        self.m.recording_control_tick()
        self.assertFalse(self.m.recording)
        self.m._fn_held = False
        self.m.recording_control_tick()
        self.m.lifecycle.callback(self.m.lifecycle.generation)
        self.m.lifecycle.tick()
        self.m._fn_held = True
        self.m.recording_control_tick()
        self.assertTrue(self.m.recording)

    def test_completed_output_after_sleep_held(self):
        epoch = self.m.lifecycle.epoch
        self.app._power_event('NSWorkspaceScreensDidSleepNotification')
        self.m.output_queue.put(('retained result', epoch))
        self.app._process_ui_queue(None)
        self.m.typer.type.assert_not_called()
        self.assertEqual(self.m.held_results, ['retained result'])

    def test_no_ready_ui_while_suspended(self):
        self.app._power_event('com.apple.screenIsLocked')
        self.app.set_ready()
        self.app._process_ui_queue(None)
        self.assertTrue(self.app.status_item.title.startswith('Status: Suspended'))

    def test_test_mode_never_types(self):
        self.m.V2T_TEST_HOOKS = True
        self.m.output_queue.put(('example', self.m.lifecycle.epoch))
        self.app._process_ui_queue(None)
        self.m.typer.type.assert_not_called()

    def test_teardown_stops_engine_even_if_remove_tap_fails(self):
        engine = self.m.audio_engine = MagicMock()
        node = self.m.audio_input_node = MagicMock()
        node.removeTapOnBus_.side_effect = RuntimeError('tap removed')
        self.m.AudioAdapter().close()
        engine.stop.assert_called_once()
        self.assertIsNone(self.m.audio_engine)

    def test_native_format_and_generation_callback(self):
        engine = MagicMock()
        self.m.AVAudioEngine.alloc.return_value.init.return_value = engine
        self.m.AVCaptureDevice.authorizationStatusForMediaType_.return_value = 3
        node = engine.inputNode.return_value
        fmt = node.inputFormatForBus_.return_value
        engine.startAndReturnError_.return_value = (True, None)
        for rate in (44100, 48000):
            fmt.sampleRate.return_value = rate
            fmt.channelCount.return_value = 1
            self.m.setup_audio_engine(self.m.lifecycle.generation)
            self.assertEqual(self.m.native_sample_rate, rate)
        fmt.sampleRate.return_value = 0
        with self.assertRaises(RuntimeError):
            self.m.setup_audio_engine(self.m.lifecycle.generation)

    def test_permission_denial(self):
        self.m.AVCaptureDevice.authorizationStatusForMediaType_.return_value = 2
        with self.assertRaisesRegex(RuntimeError, 'permission denied'):
            self.m.setup_audio_engine(1)

    def test_shutdown_drains_queue_without_hanging(self):
        self.m.transcription_queue.put(('pending', 0, 1))
        self.m.cleanup()
        self.assertEqual(self.m.transcription_queue.unfinished_tasks, 0)
        self.assertEqual(self.m.lifecycle.state, 'shutting-down')

    def test_transcription_completion_during_sleep_is_held(self):
        self.m.lifecycle.callback(self.m.lifecycle.generation)
        self.m.lifecycle.tick()
        self.m.transcription_queue.put(('fake audio', 1.0, self.m.lifecycle.epoch))
        def transcribe(*args, **kwargs):
            self.m.lifecycle.suspend('sleep during transcription')
            self.m.shutdown_event.set()
            return {'text': 'Completed dictation.'}
        self.m.mlx_whisper.transcribe.side_effect = transcribe
        self.m.transcription_worker()
        self.app._process_ui_queue(None)
        self.m.typer.type.assert_not_called()
        self.assertTrue(self.m.held_results)
        self.assertEqual(self.m.transcription_queue.unfinished_tasks, 0)

    def test_stop_failure_keeps_handle_for_retry(self):
        engine = self.m.audio_engine = MagicMock()
        self.m.audio_input_node = MagicMock()
        engine.stop.side_effect = RuntimeError('device busy')
        with self.assertRaises(RuntimeError):
            self.m.AudioAdapter().close()
        self.assertIs(self.m.audio_engine, engine)
        engine.stop.side_effect = None
        self.m.AudioAdapter().close()
        self.assertIsNone(self.m.audio_engine)

    def test_device_recovery_replaces_fn_listener(self):
        previous = self.m._fn_monitor
        installs = self.m.NSEvent.addGlobalMonitorForEventsMatchingMask_handler_.call_count
        self.m.lifecycle.callback(self.m.lifecycle.generation)
        self.m.lifecycle.tick()
        self.audio.running.return_value = False
        self.m.lifecycle.retry_at = 0
        self.app._sleepwake_watchdog(None)
        self.m.NSEvent.removeMonitor_.assert_called_with(previous)
        self.assertEqual(self.m.NSEvent.addGlobalMonitorForEventsMatchingMask_handler_.call_count, installs + 1)
        self.m._fn_held = False
        self.m.recording_control_tick()
        self.audio.running.return_value = True
        self.m.lifecycle.callback(self.m.lifecycle.generation)
        self.m.lifecycle.tick()
        event = MagicMock()
        event.modifierFlags.return_value = self.m.NSFunctionKeyMask
        self.m._fn_flags_changed(event)
        self.m.recording_control_tick()
        self.assertTrue(self.m.recording)

    def test_failed_fn_install_does_not_report_ready(self):
        self.m.NSEvent.addGlobalMonitorForEventsMatchingMask_handler_.return_value = None
        self.m.lifecycle.suspend()
        self.m.lifecycle.resume()
        self.assertEqual(self.m.lifecycle.state, 'recovering')
        self.assertIn('Fn listener unavailable', self.m.lifecycle.error)

    def test_clock_jumps_do_not_invalidate_recording(self):
        self.m.lifecycle.callback(self.m.lifecycle.generation)
        self.m.lifecycle.tick()
        self.m.lifecycle.release()
        self.m.lifecycle.press()
        epoch = self.m.lifecycle.epoch
        with patch.object(self.m.time, 'time', return_value=-999999):
            self.app._sleepwake_watchdog(None)
        self.assertEqual(self.m.lifecycle.epoch, epoch)



if __name__ == '__main__':
    unittest.main()
