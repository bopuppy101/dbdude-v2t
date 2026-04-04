#!/usr/bin/env python3
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.
"""dbdude-v2t for macOS - Hold Fn to record, release to transcribe."""

# Suppress semaphore cleanup warning from multiprocessing (mlx_whisper internal)
import os
os.environ["PYTHONWARNINGS"] = "ignore::UserWarning"

import sys
import sounddevice as sd
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
from Quartz import (
    CGEventSourceFlagsState, kCGEventSourceStateHIDSystemState,
    kCGEventFlagMaskSecondaryFn
)
import objc

# Load AVFoundation framework and get classes
objc.loadBundle('AVFoundation', globals(), '/System/Library/Frameworks/AVFoundation.framework')
AVCaptureDevice = objc.lookUpClass('AVCaptureDevice')

# Authorization status constants
AVAuthorizationStatusNotDetermined = 0
AVAuthorizationStatusRestricted = 1
AVAuthorizationStatusDenied = 2
AVAuthorizationStatusAuthorized = 3


def request_microphone_permission():
    """Request microphone permission explicitly at startup."""
    # AVMediaTypeAudio = "soun"
    auth_status = AVCaptureDevice.authorizationStatusForMediaType_("soun")

    if auth_status == AVAuthorizationStatusNotDetermined:
        # Request permission - this triggers the popup
        print("Requesting microphone permission...", flush=True)
        granted = [None]
        event = threading.Event()

        def callback(g):
            granted[0] = g
            event.set()

        try:
            callback.__block_signature__ = b'v@?B'
            AVCaptureDevice.requestAccessForMediaType_completionHandler_("soun", callback)
            event.wait(timeout=30)  # Wait up to 30 seconds for user response
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

# Keyboard controller for typing output
typer = KeyboardController()

SAMPLE_RATE = 16000


def _is_bundled_app():
    """Check if running as a bundled macOS app."""
    return '.app/Contents/MacOS' in str(Path(sys.executable))


def get_app_dir():
    """Get path to app's MacOS directory or script directory."""
    if _is_bundled_app():
        return Path(sys.executable).parent
    return Path(__file__).parent


def get_resources_dir():
    """Get path to app bundle Resources or script directory."""
    if _is_bundled_app():
        return Path(sys.executable).parent.parent / "Resources"
    return Path(__file__).parent


# Icon paths (in MacOS/ for compiled, script dir for dev)
ICONS_DIR = get_app_dir() / "icons"
ICON_READY = str(ICONS_DIR / "v2t_ready.png")
ICON_RECORDING = str(ICONS_DIR / "v2t_recording.png")
ICON_TRANSCRIBING = str(ICONS_DIR / "v2t_transcribing.png")

# Global state
recording = False
audio_data = []
stream = None
app = None  # rumps app instance
recording_start_time = None  # Track when recording started

# Non-blocking transcription queue
transcription_queue = queue.Queue()
shutdown_event = threading.Event()

# Thread-safe UI update queue (rumps/AppKit requires main thread for UI)
ui_status_queue = queue.Queue()

# Mappings
CUSTOM_MAP = {}
STRIP_PUNCT_VALUES = set()  # Values that should strip trailing punctuation
WHITESPACE_STRIP_MAP = {}  # Maps replacement value to (strip_before, strip_after) tuple
WILDCARD_MAP = {}  # Patterns containing % or _ wildcards
WILDCARD_MODE = "sql92"  # "none" or "sql92"
name_re = None  # Compiled regex for mappings

# Rules
RULES = []

# Settings (loaded from settings.json)
SETTINGS = {
    'model': 'small',
    'language': 'en',
    'log': False
}


def get_user_data_dir():
    """Get macOS user data directory."""
    data_dir = Path.home() / "Library" / "Application Support" / "dbdude-v2t"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def load_settings():
    """Load settings from settings.json."""
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
    """Load user-defined rules from rules.json."""
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
    """Evaluate a rule condition against the text. Returns True if condition matches."""
    cond_type = condition.get("type")
    operator = condition.get("operator")
    value = condition.get("value")

    if cond_type == "word_count":
        word_count = len(text.split())
        if operator == "<=":
            return word_count <= value
        elif operator == ">=":
            return word_count >= value
        elif operator == "=":
            return word_count == value
        elif operator == "<":
            return word_count < value
        elif operator == ">":
            return word_count > value
    elif cond_type == "starts_with":
        return text.lower().startswith(str(value).lower())
    elif cond_type == "ends_with":
        return text.lower().endswith(str(value).lower())
    elif cond_type == "contains":
        return str(value).lower() in text.lower()

    return False


def apply_action(text, action):
    """Apply a single action to the text and return the modified text."""
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
    """Apply user-defined rules to the text. Rules are evaluated in order."""
    if not RULES:
        return text

    for rule in RULES:
        condition = rule.get("condition", {})
        actions = rule.get("actions", [])

        if evaluate_condition(text, condition):
            for action in actions:
                text = apply_action(text, action)
            # First matching rule applies, then stop
            break

    return text


def load_mappings():
    """Load custom mappings and enabled packs from user data directory."""
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

        # Get wildcard mode
        WILDCARD_MODE = data.get("wildcard_mode", "sql92")
        print(f"INFO: Wildcard mode: {WILDCARD_MODE}", flush=True)

        # Load enabled packs first (so custom mappings can override them)
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

        # Load custom mappings (these override pack mappings)
        # Supports both old format ("key": "value") and new format ("key": {"value": "x", "strip_punctuation": true})
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

        # Build regex for matching
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
    """Convert SQL-92 LIKE pattern to regex. Each word is matched separately."""
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
    """Apply SQL-92 wildcard pattern mappings to text. Called after literal mappings."""
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
    """Apply custom mappings to transcribed text."""
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

    # Strip trailing punctuation if text ends with a strip_punct value
    # or if any strip_punctuation mapping was used in the transcription
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
    """Get the model name based on settings."""
    model = SETTINGS.get('model', 'small')
    language = SETTINGS.get('language', 'en')

    # For English, use the .en variant (English-only, faster)
    if language == 'en':
        return f"mlx-community/whisper-{model}.en-mlx"
    else:
        # Multilingual model
        return f"mlx-community/whisper-{model}-mlx"


def transcription_worker():
    """Worker thread that processes transcription jobs from the queue."""
    while not shutdown_event.is_set():
        try:
            # Wait for work with timeout so we can check shutdown
            job = transcription_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        audio, recording_duration = job
        try:
            if app:
                app.set_transcribing()

            transcribe_start = time.time()

            # Get model from settings
            model_name = get_model_name()

            # Use bundled model if available, otherwise fall back to HuggingFace
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

            # Type the text into the active window
            typer.type(text)
        except Exception as e:
            print(f"ERROR in transcription worker: {e}", flush=True)
        finally:
            transcription_queue.task_done()
            # Only set ready if queue is empty
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
            None,  # separator
            rumps.MenuItem("Show Console", callback=self.on_show_console),
            rumps.MenuItem("Configurator...", callback=self.on_configurator),
            rumps.MenuItem("Mapping/Rules...", callback=self.on_mapping_rules),
            rumps.MenuItem("Reload Mappings", callback=self.on_reload_mappings),
            None,  # separator
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]
        # Timer to poll UI updates from background threads (runs on main thread)
        self.ui_timer = rumps.Timer(self._process_ui_queue, 0.05)  # 50ms
        self.ui_timer.start()

    def _process_ui_queue(self, _):
        """Process pending UI updates on main thread."""
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
                    # Bundled app - launch the standalone executable
                    exe_dir = Path(sys.executable).parent
                    configurator_path = exe_dir / "v2t-configurator" / "v2t-configurator.bin"
                    if configurator_path.exists():
                        subprocess.Popen([str(configurator_path)], start_new_session=True)
                    else:
                        print(f"ERROR: Configurator not found at {configurator_path}", flush=True)
                else:
                    # Development mode - run Python script
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
                    # Bundled app - launch the standalone executable
                    exe_dir = Path(sys.executable).parent
                    mapping_rules_path = exe_dir / "v2t-mapping-rules" / "v2t-mapping-rules.bin"
                    if mapping_rules_path.exists():
                        subprocess.Popen([str(mapping_rules_path)], start_new_session=True)
                    else:
                        print(f"ERROR: Mapping/Rules not found at {mapping_rules_path}", flush=True)
                else:
                    # Development mode - run Python script
                    subprocess.Popen([sys.executable, "mapping_rules_gui.py"], start_new_session=True)
            except Exception as e:
                print(f"ERROR launching mapping/rules: {e}", flush=True)
        threading.Thread(target=launch, daemon=True).start()

    def on_reload_mappings(self, _):
        """Reload custom mappings without restarting."""
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
        """Actually apply status update - MUST be called on main thread."""
        self.title = ""  # Keep title empty, just show icon
        self.icon = icon_path
        self.status_item.title = f"Status: {status}"

    def set_ready(self):
        """Queue a status update (thread-safe, can be called from any thread)."""
        ui_status_queue.put(("Ready", ICON_READY))

    def set_recording(self):
        """Queue a status update (thread-safe, can be called from any thread)."""
        ui_status_queue.put(("Recording...", ICON_RECORDING))

    def set_transcribing(self):
        """Queue a status update (thread-safe, can be called from any thread)."""
        ui_status_queue.put(("Transcribing...", ICON_TRANSCRIBING))

    def quit_app(self, _):
        print("\nQuitting from menu...", flush=True)
        self.ui_timer.stop()
        cleanup()
        rumps.quit_application()
        # Force exit if rumps.quit_application() doesn't work
        import os
        os._exit(0)


def cleanup():
    """Clean up resources before exit."""
    global stream, recording
    shutdown_event.set()  # Signal worker thread to stop
    recording = False
    if stream:
        try:
            stream.stop()  # Use stop() on clean exit - we have time
            stream.close()
            stream = None
        except:
            pass
    # Wait for pending transcriptions
    if not transcription_queue.empty():
        print("Waiting for pending transcriptions...", flush=True)
        transcription_queue.join()


def handle_sigterm(signum, frame):
    """Handle SIGTERM for graceful shutdown."""
    print("\nReceived SIGTERM, shutting down gracefully...", flush=True)
    cleanup()
    if app:
        rumps.quit_application()
    os._exit(0)


def audio_callback(indata, frames, time, status):
    if recording:
        audio_data.append(indata.copy())


def start_recording():
    """Start audio recording. Called from recording_control_worker thread."""
    global audio_data, stream, recording_start_time
    audio_data = []
    recording_start_time = time.time()

    # Reuse existing stream if available, otherwise create new one
    if stream is None:
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32', callback=audio_callback)
        stream.start()

    if app:
        app.set_recording()
    print("Recording...", flush=True)


def stop_recording():
    """Stop audio recording. Called from recording_control_worker thread."""
    global recording_start_time, stream
    recording_duration = time.time() - recording_start_time if recording_start_time else 0

    # Always close the stream after each recording to prevent stale audio.
    # Previously the stream was kept open between recordings for reuse, but
    # macOS suspends idle CoreAudio streams after a few seconds, causing them
    # to deliver near-silence on the next capture. Creating a fresh stream per
    # recording adds negligible latency and guarantees live audio every time.
    if stream:
        try:
            stream.stop()
            stream.close()
        except:
            pass
        stream = None

    if audio_data:
        audio = np.concatenate(audio_data).flatten()
        rms = np.sqrt(np.mean(audio**2))
        if rms < 0.005:
            # RMS below threshold means the mic captured near-silence.
            # This can happen if the Fn key was tapped without speaking,
            # or (before the stream-per-recording fix) from a stale stream.
            print(f"Audio too quiet (RMS={rms:.4f}), skipping", flush=True)
            if app:
                app.set_ready()
                print("Ready. Hold Fn to record.", flush=True)
            return
        transcription_queue.put((audio, recording_duration))
        print(f"Recorded {recording_duration:.2f}s", flush=True)
    else:
        if app:
            app.set_ready()


def recording_control_worker():
    """Poll key state directly and handle recording start/stop.

    Uses CGEventSourceFlagsState to directly read current modifier state.
    No event tap needed - just polls every 20ms.
    """
    global recording

    while not shutdown_event.is_set():
        # Poll modifier state DIRECTLY - no event tap needed
        flags = CGEventSourceFlagsState(kCGEventSourceStateHIDSystemState)
        fn_held = bool(flags & kCGEventFlagMaskSecondaryFn)

        # Act on state
        if fn_held and not recording:
            recording = True
            start_recording()
        elif not fn_held and recording:
            recording = False
            stop_recording()

        time.sleep(0.02)  # Poll every 20ms


if __name__ == "__main__":
    from datetime import datetime

    print("=" * 50, flush=True)
    print("dbdude-v2t for macOS", flush=True)
    print("=" * 50, flush=True)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(flush=True)

    # File locations
    user_data_dir = get_user_data_dir()
    print(f"User data dir: {user_data_dir}", flush=True)
    print(f"Settings file: {user_data_dir / 'settings.json'}", flush=True)
    print(f"Mappings file: {user_data_dir / 'custom_mappings.json'}", flush=True)
    print(f"Rules file: {user_data_dir / 'rules.json'}", flush=True)
    print(f"Packs dir: {user_data_dir / 'packs'}", flush=True)
    print(flush=True)

    # Load settings first
    load_settings()

    # Model info (from settings)
    model_name = get_model_name()
    print(f"Model: {model_name}", flush=True)
    print(f"Language: {SETTINGS.get('language', 'en')}", flush=True)
    print(f"Quantization: MLX native (Metal GPU)", flush=True)
    print(flush=True)

    # Load custom mappings and packs
    load_mappings()

    # Load rules
    load_rules()
    print(flush=True)

    # Request microphone permission explicitly (triggers popup on first launch)
    request_microphone_permission()
    print(flush=True)

    print("Ready. Hold Fn to record, release to transcribe.", flush=True)
    print("Click menu bar icon to quit.", flush=True)
    print("=" * 50, flush=True)
    print(flush=True)

    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGTERM, handle_sigterm)

    # Start transcription worker thread (non-blocking transcription)
    transcription_thread = threading.Thread(target=transcription_worker, daemon=True)
    transcription_thread.start()

    # Start recording control worker thread (polls key state directly via CGEventSourceFlagsState)
    recording_control_thread = threading.Thread(target=recording_control_worker, daemon=True)
    recording_control_thread.start()

    # Run rumps app on main thread (required for macOS)
    app = V2TApp()
    app.run()
