"""Passive, bounded observation of V2T assertions and the current macOS session.

Set V2T_OBSERVE_PID to the running V2T process. This does not request sleep,
keep the machine awake, record audio, or change system settings.
"""
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from powerstate import session_awake

pid = int(os.environ['V2T_OBSERVE_PID'])
duration = max(1, min(int(os.environ.get("V2T_OBSERVE_SECONDS", "180")), 7200))
end = time.monotonic() + duration
while time.monotonic() < end:
    assertions = subprocess.check_output(['pmset', '-g', 'assertions'], text=True)
    print(json.dumps({'time': datetime.now().astimezone().isoformat(timespec='milliseconds'),
                      'pid': pid, 'session_awake': session_awake(),
                      'v2t_audio_assertion': f'Created for PID: {pid}.' in assertions,
                      'assertions': assertions}), flush=True)
    time.sleep(2)
