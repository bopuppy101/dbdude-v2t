"""Real AVAudioEngine with locally injected notifications; does NOT sleep the Mac.

Run from macos: V2T_TEST_HOOKS=1 venv/bin/python tests/hardwareprobe.py
Results identify each probe process; all transcription/typing is suppressed.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ['V2T_TEST_HOOKS'] = '1'
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location('v2t_probe', root / 'dbdude-v2t.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
from Cocoa import NSWorkspace

m.app = m.V2TApp()
if not m.session_awake():
    center = NSWorkspace.sharedWorkspace().notificationCenter()
    center.postNotificationName_object_('NSWorkspaceScreensDidSleepNotification', None)
    center.postNotificationName_object_('NSWorkspaceScreensDidWakeNotification', None)
    assert m.lifecycle.state == 'suspended' and m.audio_engine is None
    print('LOCKED_STARTUP PASS: observers dispatch; microphone remains closed', flush=True)
phase = 0
cycles = 0
started = time.monotonic()
results = []


def probe_tick(_):
    global phase, cycles, started
    elapsed = time.monotonic() - started
    if elapsed > 10:
        results.append({'result': 'BLOCKED' if not m.session_awake() else 'FAIL', 'reason': 'session inactive' if not m.session_awake() else 'phase timeout', 'phase': phase})
        finish(1)
    if phase == 0 and m.lifecycle.state == 'ready':
        results.append({'phase': 'ready', 'cycle': cycles, 'elapsed': elapsed})
        NSWorkspace.sharedWorkspace().notificationCenter().postNotificationName_object_('NSWorkspaceScreensDidSleepNotification', None)
        started = time.monotonic()
        phase = 1
    elif phase == 1 and elapsed > 2.2:
        assert m.lifecycle.state == 'suspended'
        assert m.audio_engine is None
        assertions = subprocess.check_output(['pmset', '-g', 'assertions'], text=True)
        assert f'Created for PID: {os.getpid()}.' not in assertions, assertions
        results.append({'phase': 'suspended', 'cycle': cycles, 'v2t_assertion_absent': True})
        NSWorkspace.sharedWorkspace().notificationCenter().postNotificationName_object_('NSWorkspaceScreensDidWakeNotification', None)
        started = time.monotonic()
        cycles += 1
        phase = 0
        if cycles == 20:
            phase = 2
    elif phase == 2 and m.lifecycle.state == 'ready':
        finish(0)


def finish(code):
    print('PROBE_RESULT ' + json.dumps({'pid': os.getpid(), 'kind': 'real-audio-simulated-notifications', 'cycles': cycles, 'exit': code, 'results': results}), flush=True)
    m.cleanup()
    os._exit(code)

print(f'PROBE pid={os.getpid()} real_audio=true actual_sleep=false', flush=True)
def tick(timer):
    try:
        probe_tick(timer)
    except Exception as exc:
        results.append({'result': 'FAIL', 'reason': repr(exc), 'phase': phase})
        finish(1)


timer = m.rumps.Timer(tick, 0.1)
timer.start()
m.app.run()
