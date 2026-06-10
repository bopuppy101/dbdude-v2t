#!/usr/bin/env python3
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.
"""dbdude-v2t for macOS - Hold Fn to record, release to transcribe."""

# Suppress semaphore cleanup warning from multiprocessing (mlx_whisper internal)
import os
os.environ["PYTHONWARNINGS"] = "ignore::UserWarning"

import sys
import ctypes
import numpy as np
import mlx_whisper
from pynput.keyboard import Controller as KeyboardController
import threading
import queue
from pathlib import Path
import rumps
import json
import re
import time
import signal
from scipy.signal import resample_poly
from Cocoa import NSEvent, NSFlagsChanged, NSEventMaskFlagsChanged, NSFunctionKeyMask
import objc

# SLEEPWAKE: sleep/wake hardening helpers (see docs/sleep-wake-hardening-plan-windows.md
# for the layer design; macos/sleepwake.py for the macOS-specific notes)
from sleepwake import (
    SLEEPWAKE_L1_ENABLED,
    SLEEPWAKE_L1_DEBOUNCE_TICKS,
    sleepwake_l1_stuck_flags,
    sleepwake_l1_fn_physically_down,
    SLEEPWAKE_L2_ENABLED,
    sleepwake_l2_next_retry_delay,
    sleepwake_l2_stream_is_stale,
    sleepwake_l2_should_rebuild,
    SLEEPWAKE_L3_ENABLED,
    sleepwake_l3_detect_resume,
)

# SLEEPWAKE-TEST: opt-in hooks so sleep/wake behavior can be exercised without
# a human pressing FN. Enabled ONLY via V2T_TEST_HOOKS=1:
#   - SIGUSR1 toggles a fake "FN held" flag (drives record/stop)
#   - typing of transcriptions is DISABLED (console log only), so a test run
#     can never type into whatever window has focus
V2T_TEST_HOOKS = os.environ.get('V2T_TEST_HOOKS') == '1'
_test_fn_override = [False]

# Load AVFoundation framework and get classes
objc.loadBundle('AVFoundation', globals(), '/System/Library/Frameworks/AVFoundation.framework')
AVCaptureDevice = objc.lookUpClass('AVCaptureDevice')
AVAudioEngine = objc.lookUpClass('AVAudioEngine')
AVAudioFormat = objc.lookUpClass('AVAudioFormat')

# Register block signature for installTapOnBus:bufferSize:format:block:
# PyObjC's AVFoundation metadata doesn't cover this selector, so we describe
# the block shape manually. Block: void(^)(AVAudioPCMBuffer*, AVAudioTime*).
# Argument indices: 0=self, 1=_cmd, 2=bus, 3=bufferSize, 4=format, 5=block.
objc.registerMetaDataForSelector(
    b'AVAudioNode',
    b'installTapOnBus:bufferSize:format:block:',
    {
        'arguments': {
            5: {
                'callable': {
                    'retval': {'type': b'v'},
                    'arguments': {
                        0: {'type': b'^v'},  # block self
                        1: {'type': b'@'},   # AVAudioPCMBuffer*
                        2: {'type': b'@'},   # AVAudioTime*
                    },
                },
            },
        },
    },
)

# Authorization status constants
AVAuthorizationStatusNotDetermined = 0
AVAuthorizationStatusRestricted = 1
AVAuthorizationStatusDenied = 2
AVAuthorizationStatusAuthorized = 3


def request_microphone_permission():
    """Request microphone permission explicitly at startup."""
    auth_status = AVCaptureDevice.authorizationStatusForMediaType_("soun")

    if auth_status == AVAuthorizationStatusNotDetermined:
        print("Requesting microphone permission...", flush=True)
        granted = [None]
        event = threading.Event()

        def callback(g):
            granted[0] = g
            event.set()

        try:
            callback.__block_signature__ = b'v@?B'
            AVCaptureDevice.requestAccessForMediaType_completionHandler_("soun", callback)
            event.wait(timeout=30)
        except TypeError:
            print("Note: macOS will prompt for Microphone permission on first recording.", flush=True)
        if granted[0]:
            print("Microphone permission granted.", flush=True)
        else:
            print("WARNING: Microphone permission denied!", flush=True)
    elif auth_status == AVAuthorizationStatusDenied:
        print("WARNING: Microphone permission denied. Enable in System Settings.", flush=True)
    elif auth_status == AVAuthorizationStatusAuthorized:
        print("Microphone permission already granted.", flush=True)


typer = KeyboardController()

TARGET_SAMPLE_RATE = 16000  # mlx_whisper expects 16kHz


def _is_bundled_app():
    return '.app/Contents/MacOS' in str(Path(sys.executable))


def get_app_dir():
    if _is_bundled_app():
        return Path(sys.executable).parent
    return Path(__file__).parent


def get_resources_dir():
    if _is_bundled_app():
        return Path(sys.executable).parent.parent / "Resources"
    return Path(__file__).parent


ICONS_DIR = get_app_dir() / "icons"
ICON_READY = str(ICONS_DIR / "v2t_ready.png")
ICON_RECORDING = str(ICONS_DIR / "v2t_recording.png")
ICON_TRANSCRIBING = str(ICONS_DIR / "v2t_transcribing.png")

# Global state
recording = False
audio_chunks = []  # list of numpy arrays at native rate; resampled on stop
app = None
recording_start_time = None

# AVAudioEngine state
audio_engine = None
audio_input_node = None
native_sample_rate = None  # set at engine startup, used for resampling

# FN key state (set by NSEvent monitor, read by polling loop)
_fn_state_lock = threading.Lock()
_fn_held = False
_fn_monitor = None  # NSEvent monitor handle (kept so SLEEPWAKE-L3 can re-arm it)

# SLEEPWAKE-L2: heartbeat — timestamp of the last tap callback (deaf-engine detector).
# One-element list so the audio-thread callback can stamp it without `global`.
_sleepwake_l2_last_tap_ts = [None]

transcription_queue = queue.Queue()
shutdown_event = threading.Event()
ui_status_queue = queue.Queue()

CUSTOM_MAP = {}
STRIP_PUNCT_VALUES = set()
WHITESPACE_STRIP_MAP = {}
WILDCARD_MAP = {}
WILDCARD_MODE = "sql92"
name_re = None

RULES = []

SETTINGS = {
    'model': 'small',
    'language': 'en',
    'log': False
}


def get_user_data_dir():
    data_dir = Path.home() / "Library" / "Application Support" / "dbdude-v2t"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def load_settings():
    global SETTINGS
    settings_file = get_user_data_dir() / "settings.json"
    if not settings_file.exists():
        print(f"INFO: No settings file found at {settings_file}, using defaults", flush=True)
        return
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            saved = json.load(f)
            SETTINGS.update(saved)
        print(f"INFO: Loaded settings from {settings_file}", flush=True)
    except Exception as e:
        print(f"WARNING: Could not load settings: {e}", flush=True)


def load_rules():
    global RULES
    rules_file = get_user_data_dir() / "rules.json"
    if not rules_file.exists():
        print(f"INFO: No rules file found at {rules_file}", flush=True)
        return
    try:
        with open(rules_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        RULES = [r for r in data.get("rules", []) if r.get("enabled", True)]
        print(f"INFO: Loaded {len(RULES)} rule(s)", flush=True)
    except Exception as e:
        print(f"WARNING: Could not load rules: {e}", flush=True)


def evaluate_condition(text, condition):
    cond_type = condition.get("type")
    operator = condition.get("operator")
    value = condition.get("value")
    if cond_type == "word_count":
        word_count = len(text.split())
        if operator == "<=": return word_count <= value
        elif operator == ">=": return word_count >= value
        elif operator == "=": return word_count == value
        elif operator == "<": return word_count < value
        elif operator == ">": return word_count > value
    elif cond_type == "starts_with":
        return text.lower().startswith(str(value).lower())
    elif cond_type == "ends_with":
        return text.lower().endswith(str(value).lower())
    elif cond_type == "contains":
        return str(value).lower() in text.lower()
    return False


def apply_action(text, action):
    if action == "strip_punctuation":
        return text.rstrip('.!?,;:')
    elif action == "add_period":
        text = text.rstrip('.!?,;:')
        return text + '.'
    elif action == "add_question":
        text = text.rstrip('.!?,;:')
        return text + '?'
    elif action == "lowercase_first":
        if text and text[0].isupper():
            return text[0].lower() + text[1:]
    elif action == "uppercase_first":
        if text and text[0].islower():
            return text[0].upper() + text[1:]
    return text


def apply_rules(text):
    if not RULES:
        return text
    for rule in RULES:
        condition = rule.get("condition", {})
        actions = rule.get("actions", [])
        if evaluate_condition(text, condition):
            for action in actions:
                text = apply_action(text, action)
            break
    return text


def load_mappings():
    global CUSTOM_MAP, STRIP_PUNCT_VALUES, WHITESPACE_STRIP_MAP, WILDCARD_MODE, name_re
    user_data_dir = get_user_data_dir()
    maps_file = user_data_dir / "custom_mappings.json"
    packs_dir = user_data_dir / "packs"
    if not maps_file.exists():
        print(f"INFO: No custom mappings file found at {maps_file}", flush=True)
        return
    try:
        with open(maps_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        WILDCARD_MODE = data.get("wildcard_mode", "sql92")
        print(f"INFO: Wildcard mode: {WILDCARD_MODE}", flush=True)
        enabled_packs = data.get("enabled_packs", [])
        if enabled_packs and packs_dir.exists():
            for pack_file in packs_dir.glob("*.json"):
                try:
                    with open(pack_file, 'r', encoding='utf-8') as pf:
                        pack_data = json.load(pf)
                        pack_name = pack_data.get("_name", pack_file.stem)
                        if pack_name in enabled_packs:
                            for key, value in pack_data.get("names", {}).items():
                                CUSTOM_MAP[key.lower()] = value
                            print(f"INFO: Loaded map pack: {pack_name}", flush=True)
                except Exception as e:
                    print(f"WARNING: Could not load map pack {pack_file.name}: {e}", flush=True)
        for key, entry in data.get("names", {}).items():
            key_lower = key.lower()
            if isinstance(entry, dict):
                actual_value = entry.get("value", "")
                strip_punctuation = entry.get("strip_punctuation", False)
                strip_ws_before = entry.get("strip_whitespace_before", False)
                strip_ws_after = entry.get("strip_whitespace_after", False)
            else:
                actual_value = entry
                strip_punctuation = False
                strip_ws_before = False
                strip_ws_after = False
            if WILDCARD_MODE == "sql92" and ('%' in key_lower or '_' in key_lower):
                WILDCARD_MAP[key_lower] = actual_value
            else:
                CUSTOM_MAP[key_lower] = actual_value
                if strip_punctuation:
                    STRIP_PUNCT_VALUES.add(actual_value)
                if strip_ws_before or strip_ws_after:
                    WHITESPACE_STRIP_MAP[actual_value] = (strip_ws_before, strip_ws_after)
        if WILDCARD_MAP:
            print(f"INFO: Loaded {len(WILDCARD_MAP)} wildcard pattern(s)", flush=True)
        if CUSTOM_MAP:
            name_re = re.compile(
                r"\b(" + "|".join(map(re.escape, CUSTOM_MAP.keys())) + r")\b",
                flags=re.IGNORECASE
            )
            print(f"INFO: Loaded {len(CUSTOM_MAP)} total mapping(s)", flush=True)
        else:
            name_re = None
    except Exception as e:
        print(f"WARNING: Could not load mappings: {e}", flush=True)


def sql92_pattern_to_regex(pattern):
    pattern_words = pattern.split()
    regex_parts = []
    for word in pattern_words:
        regex_word = ""
        for char in word:
            if char == '%':
                regex_word += '.*'
            elif char == '_':
                regex_word += '.'
            elif char in r'\.^$+?{}[]|()':
                regex_word += '\\' + char
            else:
                regex_word += char
        regex_parts.append(regex_word)
    return r'\s+'.join(regex_parts)


def apply_wildcard_mappings(text):
    if not WILDCARD_MAP or WILDCARD_MODE != "sql92":
        return text
    text_lower = text.lower()
    for pattern, replacement in WILDCARD_MAP.items():
        regex_pattern = sql92_pattern_to_regex(pattern)
        try:
            full_pattern = r'\b' + regex_pattern + r'\b'
            compiled = re.compile(full_pattern, re.IGNORECASE)
            match = compiled.search(text_lower)
            if match:
                text = compiled.sub(replacement, text, count=1)
                text_lower = text.lower()
        except re.error as e:
            print(f"WARNING: Invalid wildcard pattern '{pattern}': {e}", flush=True)
    return text


def apply_mappings(text):
    if not name_re or not CUSTOM_MAP:
        return text
    STRIP_BEFORE = '\x01'
    STRIP_AFTER = '\x02'
    strip_punct_used = False

    def _replace(m):
        nonlocal strip_punct_used
        to_text = CUSTOM_MAP[m.group(1).lower()]
        if to_text in STRIP_PUNCT_VALUES:
            strip_punct_used = True
        strip_before, strip_after = WHITESPACE_STRIP_MAP.get(to_text, (False, False))
        prefix = STRIP_BEFORE if strip_before else ''
        suffix = STRIP_AFTER if strip_after else ''
        return prefix + to_text + suffix

    text = name_re.sub(_replace, text)
    text = re.sub(r'\s*\x01', '', text)
    text = re.sub(r'\x02\s*', '', text)
    if text.endswith('.') or text.endswith('!') or text.endswith('?') or text.endswith(',') or text.endswith(';') or text.endswith(':'):
        stripped = text.rstrip('.!?,;:')
        if STRIP_PUNCT_VALUES:
            for value in STRIP_PUNCT_VALUES:
                if stripped.endswith(value):
                    text = stripped
                    break
        if strip_punct_used and text != stripped:
            text = stripped
    return text


def get_model_name():
    model = SETTINGS.get('model', 'small')
    language = SETTINGS.get('language', 'en')
    if language == 'en':
        return f"mlx-community/whisper-{model}.en-mlx"
    else:
        return f"mlx-community/whisper-{model}-mlx"


def transcription_worker():
    while not shutdown_event.is_set():
        try:
            job = transcription_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        audio, recording_duration = job
        try:
            if app:
                app.set_transcribing()
            transcribe_start = time.time()
            model_name = get_model_name()
            model = SETTINGS.get('model', 'small')
            language = SETTINGS.get('language', 'en')
            if language == 'en':
                bundled_name = f"whisper-{model}.en-mlx"
            else:
                bundled_name = f"whisper-{model}-mlx"
            model_path = get_resources_dir() / "models" / bundled_name
            if model_path.exists():
                result = mlx_whisper.transcribe(audio, path_or_hf_repo=str(model_path), condition_on_previous_text=False)
            else:
                result = mlx_whisper.transcribe(audio, path_or_hf_repo=model_name, condition_on_previous_text=False)
            transcribe_time = time.time() - transcribe_start
            raw = result['text'].strip()
            print(f"Transcribed {recording_duration:.2f}s audio in {transcribe_time:.2f}s", flush=True)
            print(f"Transcribed: {raw}", flush=True)
            text = apply_mappings(raw)
            text = apply_wildcard_mappings(text)
            text = apply_rules(text)
            print(f"Mapped to:   {text}", flush=True)
            if V2T_TEST_HOOKS:
                # SLEEPWAKE-TEST: never type into the focused window during a test run
                print("TEST MODE: typing suppressed", flush=True)
            else:
                time.sleep(0.05)
                typer.type(text)
        except Exception as e:
            print(f"ERROR in transcription worker: {e}", flush=True)
        finally:
            transcription_queue.task_done()
            if transcription_queue.empty() and app:
                app.set_ready()
                print("Ready. Hold Fn to record.", flush=True)


class V2TApp(rumps.App):
    def __init__(self):
        super().__init__("V2T", icon=ICON_READY, quit_button=None)
        self.status_item = rumps.MenuItem("Status: Ready", callback=None)
        self.status_item.set_callback(None)
        self.menu = [
            self.status_item,
            None,
            rumps.MenuItem("Show Console", callback=self.on_show_console),
            rumps.MenuItem("Configurator...", callback=self.on_configurator),
            rumps.MenuItem("Mapping/Rules...", callback=self.on_mapping_rules),
            rumps.MenuItem("Reload Mappings", callback=self.on_reload_mappings),
            None,
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]
        self.ui_timer = rumps.Timer(self._process_ui_queue, 0.05)
        self.ui_timer.start()
        setup_fn_monitor()
        setup_audio_engine()
        # === SLEEPWAKE: watchdog timer ====================================
        # Runs on the main thread (AppKit/AVFoundation calls are safe here).
        # Its interval doubles as the L2 fixed retry cadence: one rebuild
        # attempt per tick until healthy — flat interval, never backs off.
        self._sleepwake_last_tick_ts = time.time()   # L3 resume detector
        self._sleepwake_l1_stuck_streak = 0          # L1 debounce counter
        self._sleepwake_l2_failures = 0              # L2 consecutive-failure count
        self.sleepwake_timer = rumps.Timer(self._sleepwake_watchdog, sleepwake_l2_next_retry_delay())
        self.sleepwake_timer.start()
        # === END SLEEPWAKE ================================================

    # ========================================================================
    # SLEEPWAKE: watchdog (L3 resume re-arm, L1 stuck-FN check, L2 audio heal)
    # ========================================================================
    def _sleepwake_watchdog(self, _):
        global recording, _fn_held
        if shutdown_event.is_set():
            return
        now = time.time()
        elapsed = now - self._sleepwake_last_tick_ts
        self._sleepwake_last_tick_ts = now

        # === SLEEPWAKE-L3: resume re-arm (detect sleep via tick gap) =======
        # The timer can't fire mid-sleep (process frozen), so a gap far beyond
        # the ~2s interval means the machine slept. Full re-arm on resume.
        if SLEEPWAKE_L3_ENABLED and sleepwake_l3_detect_resume(elapsed):
            print(f"WARNING: SLEEPWAKE-L3 RESUME DETECTED — {elapsed:.1f}s gap since "
                  f"last tick; re-arming FN monitor + audio engine, clearing key state", flush=True)
            self._sleepwake_rearm(reason="sleepwake_l3_resume")
            return  # next tick re-checks L2 health with a fresh heartbeat

        # === SLEEPWAKE-L1: stuck-FN watchdog (only while recording) ========
        # Low-frequency ground-truth check via +[NSEvent modifierFlags] —
        # deliberately NOT 50Hz polling (see sleepwake.py: CGEventSourceFlagsState
        # permanent-block bug). Debounced so one misread can't cut off dictation.
        # Skipped while the test hook fakes FN (physical key is up by design).
        if SLEEPWAKE_L1_ENABLED and recording and not _test_fn_override[0]:
            with _fn_state_lock:
                held_now = {'fn_held': _fn_held}
            phys = {'fn_held': sleepwake_l1_fn_physically_down()}
            if sleepwake_l1_stuck_flags(held_now, phys):
                self._sleepwake_l1_stuck_streak += 1
                if self._sleepwake_l1_stuck_streak >= SLEEPWAKE_L1_DEBOUNCE_TICKS:
                    print("WARNING: SLEEPWAKE-L1 cleared stuck fn_held flag — "
                          "no key physically held; stopping phantom recording", flush=True)
                    self._sleepwake_rearm(reason="sleepwake_l1_stuck", rearm_audio=False,
                                          rearm_monitor=False)
            else:
                self._sleepwake_l1_stuck_streak = 0
        else:
            self._sleepwake_l1_stuck_streak = 0

        # === SLEEPWAKE-L2: self-healing audio engine =======================
        if SLEEPWAKE_L2_ENABLED:
            try:
                engine_running = bool(audio_engine is not None and audio_engine.isRunning())
            except Exception:
                engine_running = False
            stale = sleepwake_l2_stream_is_stale(_sleepwake_l2_last_tap_ts[0], now)
            if sleepwake_l2_should_rebuild(engine_running, stale):
                self._sleepwake_l2_failures += 1
                why = "engine not running" if not engine_running else "tap went silent"
                print(f"WARNING: SLEEPWAKE-L2 {why} (#{self._sleepwake_l2_failures}); "
                      f"rebuilding (next retry in {sleepwake_l2_next_retry_delay(self._sleepwake_l2_failures)}s if it fails)", flush=True)
                if sleepwake_l2_rebuild_audio_engine():
                    print("WARNING: SLEEPWAKE-L2 audio engine recovered", flush=True)
                    self._sleepwake_l2_failures = 0
            elif self._sleepwake_l2_failures:
                # Engine became healthy again (first callbacks arrived).
                self._sleepwake_l2_failures = 0

    def _sleepwake_rearm(self, reason, rearm_audio=True, rearm_monitor=True):
        """Clear FN/recording state, DISCARD phantom audio, optionally re-arm
        the NSEvent monitor and rebuild the audio engine. Main thread only.

        Ordering matters vs. the 20ms recording_control_worker: clear _fn_held
        first, then empty the chunk buffer, then drop `recording` — if the
        worker fires in between, stop_recording() sees no chunks and returns
        without transcribing, so phantom audio can never be typed.
        """
        global recording, _fn_held, audio_chunks
        with _fn_state_lock:
            _fn_held = False
        _test_fn_override[0] = False
        was_recording = recording
        discarded = len(audio_chunks)
        audio_chunks = []
        recording = False
        self._sleepwake_l1_stuck_streak = 0
        if was_recording:
            print(f"WARNING: {reason} stopped phantom recording, "
                  f"discarded {discarded} audio chunk(s)", flush=True)
        if rearm_monitor:
            try:
                sleepwake_l3_rearm_fn_monitor()
                print("WARNING: SLEEPWAKE-L3 FN monitor re-armed", flush=True)
            except Exception as e:
                print(f"ERROR: SLEEPWAKE-L3 FN monitor re-arm failed: {e}", flush=True)
        if rearm_audio:
            if sleepwake_l2_rebuild_audio_engine():
                print("WARNING: SLEEPWAKE-L3 audio engine rebuilt on resume", flush=True)
            # on failure the L2 check retries every tick (fixed interval)
        self.set_ready()
    # ========================================================================
    # END SLEEPWAKE watchdog
    # ========================================================================

    def _process_ui_queue(self, _):
        while not ui_status_queue.empty():
            try:
                status, icon_path = ui_status_queue.get_nowait()
                self._apply_status(status, icon_path)
            except queue.Empty:
                break

    def on_show_console(self, _):
        import subprocess
        subprocess.run(['open', '-a', 'Terminal'])

    def on_configurator(self, _):
        def launch():
            try:
                print("Opening Configurator...", flush=True)
                import subprocess
                if getattr(sys, 'frozen', False):
                    exe_dir = Path(sys.executable).parent
                    configurator_path = exe_dir / "v2t-configurator" / "v2t-configurator.bin"
                    if configurator_path.exists():
                        subprocess.Popen([str(configurator_path)], start_new_session=True)
                    else:
                        print(f"ERROR: Configurator not found at {configurator_path}", flush=True)
                else:
                    subprocess.Popen([sys.executable, "configurator_gui.py"], start_new_session=True)
            except Exception as e:
                print(f"ERROR launching configurator: {e}", flush=True)
        threading.Thread(target=launch, daemon=True).start()

    def on_mapping_rules(self, _):
        def launch():
            try:
                print("Opening Mapping/Rules...", flush=True)
                import subprocess
                if getattr(sys, 'frozen', False):
                    exe_dir = Path(sys.executable).parent
                    mapping_rules_path = exe_dir / "v2t-mapping-rules" / "v2t-mapping-rules.bin"
                    if mapping_rules_path.exists():
                        subprocess.Popen([str(mapping_rules_path)], start_new_session=True)
                    else:
                        print(f"ERROR: Mapping/Rules not found at {mapping_rules_path}", flush=True)
                else:
                    subprocess.Popen([sys.executable, "mapping_rules_gui.py"], start_new_session=True)
            except Exception as e:
                print(f"ERROR launching mapping/rules: {e}", flush=True)
        threading.Thread(target=launch, daemon=True).start()

    def on_reload_mappings(self, _):
        global CUSTOM_MAP, STRIP_PUNCT_VALUES, WILDCARD_MAP, name_re
        CUSTOM_MAP.clear()
        STRIP_PUNCT_VALUES.clear()
        WHITESPACE_STRIP_MAP.clear()
        WILDCARD_MAP.clear()
        name_re = None
        load_mappings()
        count = len(CUSTOM_MAP) + len(WILDCARD_MAP)
        print(f"INFO: Mappings reloaded ({count} active)", flush=True)

    def _apply_status(self, status, icon_path):
        self.title = ""
        self.icon = icon_path
        self.status_item.title = f"Status: {status}"

    def set_ready(self):
        ui_status_queue.put(("Ready", ICON_READY))

    def set_recording(self):
        ui_status_queue.put(("Recording...", ICON_RECORDING))

    def set_transcribing(self):
        ui_status_queue.put(("Transcribing...", ICON_TRANSCRIBING))

    def quit_app(self, _):
        print("\nQuitting from menu...", flush=True)
        self.ui_timer.stop()
        self.sleepwake_timer.stop()
        cleanup()
        rumps.quit_application()
        os._exit(0)


def cleanup():
    """Stop engine, drain transcription queue."""
    global audio_engine, audio_input_node, recording
    shutdown_event.set()
    recording = False
    if audio_engine is not None:
        try:
            if audio_input_node is not None:
                audio_input_node.removeTapOnBus_(0)
            audio_engine.stop()
        except Exception as e:
            print(f"WARNING during engine cleanup: {e}", flush=True)
        audio_engine = None
        audio_input_node = None
    if not transcription_queue.empty():
        print("Waiting for pending transcriptions...", flush=True)
        transcription_queue.join()


def handle_sigterm(signum, frame):
    print("\nReceived SIGTERM, shutting down gracefully...", flush=True)
    cleanup()
    if app:
        rumps.quit_application()
    os._exit(0)


_tap_diag_printed = False


def _audio_tap_callback(buffer, when):
    """AVAudioEngine tap callback — fires on the audio thread.

    Keep it short: only extract samples and append if recording. Resampling
    and transcription happen in stop_recording.
    """
    global _tap_diag_printed
    try:
        # SLEEPWAKE-L2 heartbeat: stamp EVERY callback, before the recording
        # check — a healthy engine fires this continuously, so silence here
        # is how the watchdog detects a deaf engine after sleep/wake.
        _sleepwake_l2_last_tap_ts[0] = time.time()
        if not recording:
            return
        frame_length = int(buffer.frameLength())
        if frame_length <= 0:
            return

        fcd = buffer.floatChannelData()
        if fcd is None:
            return

        # PyObjCPointer exposes the raw C pointer via pointerAsInteger.
        # fcd is float** — an array of channel pointers. Channel 0 is at [0].
        addr = fcd.pointerAsInteger
        float_ptr_ptr = ctypes.cast(addr, ctypes.POINTER(ctypes.POINTER(ctypes.c_float)))
        chan0_ptr = float_ptr_ptr[0]
        samples = np.ctypeslib.as_array(chan0_ptr, shape=(frame_length,)).copy()
        audio_chunks.append(samples)

        if not _tap_diag_printed:
            _tap_diag_printed = True
            print(f"Audio tap extracting OK: first buffer {frame_length} frames, addr=0x{addr:x}", flush=True)
    except Exception as e:
        print(f"ERROR in audio tap: {type(e).__name__}: {e}", flush=True)


_audio_tap_callback.__block_signature__ = b'v@?@@'


def setup_audio_engine():
    """Create AVAudioEngine, install input tap, start engine.

    Engine runs continuously from app start until quit. The tap callback
    only appends to audio_chunks when recording=True.
    """
    global audio_engine, audio_input_node, native_sample_rate

    # SLEEPWAKE-L2: reset the heartbeat so a just-(re)built engine isn't
    # immediately declared stale before its first callback fires.
    _sleepwake_l2_last_tap_ts[0] = None

    audio_engine = AVAudioEngine.alloc().init()
    audio_input_node = audio_engine.inputNode()

    input_format = audio_input_node.inputFormatForBus_(0)
    native_sample_rate = float(input_format.sampleRate())
    native_channels = int(input_format.channelCount())
    print(f"AVAudioEngine input: {native_sample_rate}Hz, {native_channels} channel(s)", flush=True)

    # Install tap at native format; we resample to 16kHz in stop_recording.
    audio_input_node.installTapOnBus_bufferSize_format_block_(
        0, 4096, input_format, _audio_tap_callback
    )

    audio_engine.prepare()
    result = audio_engine.startAndReturnError_(None)
    if isinstance(result, tuple):
        success, error = result
    else:
        success, error = result, None
    if not success:
        print(f"ERROR starting AVAudioEngine: {error}", flush=True)
        raise RuntimeError(f"AVAudioEngine failed to start: {error}")
    print("AVAudioEngine started.", flush=True)


# ============================================================================
# SLEEPWAKE-L2: self-healing AVAudioEngine
# ============================================================================
def sleepwake_l2_rebuild_audio_engine():
    """Tear down the (dead/deaf) engine and build a fresh one.

    A full rebuild — not a restart of the old engine — because after a wake or
    device switch the old engine/tap can hold stale device state, and the input
    format may have changed. setup_audio_engine() re-reads the native format,
    so native_sample_rate stays correct after a device/rate change.

    Returns True on success, False on failure (caller retries on a fixed
    interval — never unbounded backoff, never gives up).
    """
    global audio_engine, audio_input_node
    if audio_engine is not None:
        try:
            if audio_input_node is not None:
                audio_input_node.removeTapOnBus_(0)
        except Exception:
            pass
        try:
            audio_engine.stop()
        except Exception:
            pass
        audio_engine = None
        audio_input_node = None
    try:
        setup_audio_engine()
        return True
    except Exception as e:
        print(f"WARNING: SLEEPWAKE-L2 engine rebuild failed: {e}", flush=True)
        return False
# ============================================================================
# END SLEEPWAKE-L2
# ============================================================================


def start_recording():
    """Begin capturing samples. Engine is already running — just flip the flag."""
    global audio_chunks, recording_start_time
    audio_chunks = []
    recording_start_time = time.time()
    if app:
        app.set_recording()
    print("Recording...", flush=True)


def stop_recording():
    """Stop capturing, resample to 16kHz, queue for transcription."""
    global recording_start_time
    recording_duration = time.time() - recording_start_time if recording_start_time else 0

    if not audio_chunks:
        if app:
            app.set_ready()
        return

    audio_native = np.concatenate(audio_chunks).flatten().astype(np.float32)

    # Resample to 16kHz if the native rate isn't already 16kHz.
    if int(native_sample_rate) == TARGET_SAMPLE_RATE:
        audio = audio_native
    else:
        # resample_poly uses integer up/down factors. Reduce the ratio.
        from math import gcd
        up = TARGET_SAMPLE_RATE
        down = int(native_sample_rate)
        g = gcd(up, down)
        audio = resample_poly(audio_native, up // g, down // g).astype(np.float32)

    rms = np.sqrt(np.mean(audio ** 2))
    if rms < 0.003:
        print(f"Audio too quiet (RMS={rms:.4f}), skipping", flush=True)
        if app:
            app.set_ready()
            print("Ready. Hold Fn to record.", flush=True)
        return

    transcription_queue.put((audio, recording_duration))
    print(f"Recorded {recording_duration:.2f}s (native {len(audio_native)} samples → {len(audio)} @ 16kHz)", flush=True)


def _fn_flags_changed(event):
    """NSEvent callback — only flips the _fn_held flag (thread-safe)."""
    global _fn_held
    fn_down = bool(event.modifierFlags() & NSFunctionKeyMask)
    with _fn_state_lock:
        _fn_held = fn_down


def setup_fn_monitor():
    """Install NSEvent global monitor for Fn key flag changes."""
    global _fn_monitor
    _fn_monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
        NSEventMaskFlagsChanged, _fn_flags_changed
    )
    print("NSEvent Fn monitor installed.", flush=True)


# ============================================================================
# SLEEPWAKE-L3: NSEvent monitor re-arm (a sleep can leave the monitor dead)
# ============================================================================
def sleepwake_l3_rearm_fn_monitor():
    """Remove and re-install the global FN monitor. Main thread only."""
    global _fn_monitor
    try:
        if _fn_monitor is not None:
            NSEvent.removeMonitor_(_fn_monitor)
    except Exception as e:
        print(f"WARNING: SLEEPWAKE-L3 removeMonitor failed (continuing): {e}", flush=True)
    _fn_monitor = None
    setup_fn_monitor()
# ============================================================================
# END SLEEPWAKE-L3
# ============================================================================


def recording_control_worker():
    """Poll FN key state and drive start/stop recording.

    Reads the _fn_held flag set by the NSEvent monitor callback.
    """
    global recording
    while not shutdown_event.is_set():
        with _fn_state_lock:
            fn_held = _fn_held
        if V2T_TEST_HOOKS and _test_fn_override[0]:  # SLEEPWAKE-TEST fake FN
            fn_held = True
        if fn_held and not recording:
            recording = True
            start_recording()
        elif not fn_held and recording:
            recording = False
            stop_recording()
        time.sleep(0.02)


if __name__ == "__main__":
    from datetime import datetime

    print("=" * 50, flush=True)
    print("dbdude-v2t for macOS", flush=True)
    print("=" * 50, flush=True)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(flush=True)

    user_data_dir = get_user_data_dir()
    print(f"User data dir: {user_data_dir}", flush=True)
    print(f"Settings file: {user_data_dir / 'settings.json'}", flush=True)
    print(f"Mappings file: {user_data_dir / 'custom_mappings.json'}", flush=True)
    print(f"Rules file: {user_data_dir / 'rules.json'}", flush=True)
    print(f"Packs dir: {user_data_dir / 'packs'}", flush=True)
    print(flush=True)

    load_settings()

    model_name = get_model_name()
    print(f"Model: {model_name}", flush=True)
    print(f"Language: {SETTINGS.get('language', 'en')}", flush=True)
    print(f"Quantization: MLX native (Metal GPU)", flush=True)
    print(flush=True)

    load_mappings()
    load_rules()
    print(flush=True)

    # Check Globe/FN key setting — emoji mode intercepts FN events
    try:
        import subprocess
        result = subprocess.run(
            ['defaults', 'read', 'com.apple.HIToolbox', 'AppleFnUsageType'],
            capture_output=True, text=True, timeout=5
        )
        fn_usage = result.stdout.strip()
        fn_labels = {'0': 'Change Input Source', '1': 'Show Emoji & Symbols', '2': 'Start Dictation', '3': 'Do Nothing'}
        fn_label = fn_labels.get(fn_usage, f'Unknown ({fn_usage})')
        if fn_usage == '3':
            print(f"INFO: Globe/FN key set to: {fn_label}", flush=True)
        else:
            print(f"WARNING: Globe/FN key may not be set to 'Do Nothing' (detected: {fn_label}).", flush=True)
            print("         If FN key is unreliable, check:", flush=True)
            print("         System Settings > Keyboard > Press Globe key to > Do Nothing", flush=True)
        print(flush=True)
    except Exception:
        pass

    request_microphone_permission()
    print(flush=True)

    print("Ready. Hold Fn to record, release to transcribe.", flush=True)
    print("Click menu bar icon to quit.", flush=True)
    print("=" * 50, flush=True)
    print(flush=True)

    signal.signal(signal.SIGTERM, handle_sigterm)

    # SLEEPWAKE-TEST: SIGUSR1 toggles fake FN (record/stop) — V2T_TEST_HOOKS=1 only
    if V2T_TEST_HOOKS:
        def _handle_sigusr1(signum, frame):
            _test_fn_override[0] = not _test_fn_override[0]
            print(f"TEST MODE: fake FN -> {'HELD' if _test_fn_override[0] else 'RELEASED'}", flush=True)
        signal.signal(signal.SIGUSR1, _handle_sigusr1)
        print("*** TEST MODE (V2T_TEST_HOOKS=1): SIGUSR1 toggles recording; typing DISABLED ***", flush=True)

    transcription_thread = threading.Thread(target=transcription_worker, daemon=True)
    transcription_thread.start()

    recording_control_thread = threading.Thread(target=recording_control_worker, daemon=True)
    recording_control_thread.start()

    app = V2TApp()
    app.run()
