"""Native state adapter tests without accessing the real desktop."""
import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class PowerStateTests(unittest.TestCase):
    def setUp(self):
        self.quartz = MagicMock()
        cocoa = types.ModuleType('Cocoa')
        cocoa.NSObject = type('NSObject', (), {})
        cocoa.NSWorkspace = MagicMock()
        cocoa.NSDistributedNotificationCenter = MagicMock()
        spec = importlib.util.spec_from_file_location('test_powerstate_adapter', Path(__file__).resolve().parents[1] / 'powerstate.py')
        self.m = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'Quartz': self.quartz, 'Cocoa': cocoa}):
            spec.loader.exec_module(self.m)
        self.session = {'kCGSSessionOnConsoleKey': True, 'kCGSSessionUserIDKey': os.getuid(), 'kCGSessionLoginDoneKey': True}
        self.quartz.CGSessionCopyCurrentDictionary.return_value = self.session
        self.quartz.CGGetOnlineDisplayList.return_value = (0, (1,), 1)
        self.quartz.CGDisplayIsAsleep.return_value = False

    def test_awake_console(self):
        self.assertTrue(self.m.session_awake())
    def test_locked(self):
        self.session['CGSSessionScreenIsLocked'] = True
        self.assertFalse(self.m.session_awake())
    def test_other_console_user(self):
        self.session['kCGSSessionUserIDKey'] = os.getuid() + 1
        self.assertFalse(self.m.session_awake())
    def test_login_incomplete(self):
        self.session['kCGSessionLoginDoneKey'] = False
        self.assertFalse(self.m.session_awake())
    def test_inactive_session(self):
        self.session['kCGSSessionOnConsoleKey'] = False
        self.assertFalse(self.m.session_awake())
    def test_no_session(self):
        self.quartz.CGSessionCopyCurrentDictionary.return_value = None
        self.assertFalse(self.m.session_awake())
    def test_display_asleep(self):
        self.quartz.CGDisplayIsAsleep.return_value = True
        self.assertFalse(self.m.session_awake())
    def test_clamshell_with_external_display_awake(self):
        self.quartz.CGGetOnlineDisplayList.return_value = (0, (1, 2), 2)
        self.quartz.CGDisplayIsAsleep.side_effect = lambda display: display == 1
        self.assertTrue(self.m.session_awake())
    def test_no_displays(self):
        self.quartz.CGGetOnlineDisplayList.return_value = (0, (), 0)
        self.assertFalse(self.m.session_awake())
    def test_api_failure(self):
        self.quartz.CGGetOnlineDisplayList.side_effect = RuntimeError('unavailable')
        self.assertFalse(self.m.session_awake())

if __name__ == '__main__':
    unittest.main()
