#!/usr/bin/env python3
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.
# v6 - Ubuntu version - uses xdotool for text output, requires sudo for keyboard module
# v6 adds: dynamic mappings loaded from JSON files

import os
import json
from pathlib import Path
# Allow duplicate OpenMP runtimes (NumPy MKL + ONNX) to coexist
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
# Silence Qt DBus theme warnings (harmless when running with sudo)
os.environ["QT_LOGGING_RULES"] = "qt.qpa.theme.dbus=false;qt.qpa.theme.gnome=false"

import sys
import regex  # Use regex instead of re for possessive quantifiers (prevents catastrophic backtracking)
import time
import threading
import datetime
import queue
import subprocess
import argparse
import numpy as np
import sounddevice as sd
import keyboard
from scipy.signal import resample
from faster_whisper import WhisperModel
import ctranslate2
from PySide6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QMessageBox,
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel)
from PySide6.QtGui import QIcon, QAction, QFont
from PySide6.QtCore import QTimer, QFileSystemWatcher

# --- Command-line Arguments ---
VALID_MODELS = ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']
parser = argparse.ArgumentParser(description='Voice-to-text transcription with hotkeys')
parser.add_argument('--log', action='store_true', help='Enable logging transcriptions to ~/logs')
parser.add_argument('--no-log', action='store_true', help='Disable logging (overrides settings)')
parser.add_argument('--model', choices=VALID_MODELS, default=None, help='Whisper model size (default: from settings or base)')
args = parser.parse_args()

# Load settings from configurator
def _load_settings():
    """Load settings from settings.json."""
    sudo_user = os.environ.get('SUDO_USER')
    if sudo_user:
        settings_file = Path(f"/home/{sudo_user}/.voice2text/settings.json")
    else:
        settings_file = Path.home() / ".voice2text" / "settings.json"

    defaults = {"model": "base", "language": "en", "log": False, "device": None}
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                defaults.update(saved)
        except Exception as e:
            print(f"WARNING: Could not load settings: {e}", file=sys.stderr)
    return defaults

_settings = _load_settings()

# Command line overrides settings
if args.log:
    ENABLE_LOGGING = True
elif args.no_log:
    ENABLE_LOGGING = False
else:
    ENABLE_LOGGING = _settings.get('log', False)

MODEL_NAME = args.model if args.model else _settings.get('model', 'base')

# --- Configuration ---

VERSION = "2026.1"

# Handle sudo: use SUDO_USER's home instead of /root
_sudo_user = os.environ.get('SUDO_USER')
if _sudo_user:
    LOGS_DIR = f"/home/{_sudo_user}/logs"
else:
    LOGS_DIR = os.path.expanduser("~/logs")

# Icon paths
ICON_DIR = Path(__file__).parent / "icons"
ICON_IDLE = str(ICON_DIR / "v2t_preview.png")
ICON_RECORDING = str(ICON_DIR / "v2t_recording_preview.png")
ICON_TRANSCRIBING = str(ICON_DIR / "v2t_transcribing_preview.png")
if ENABLE_LOGGING and not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR, exist_ok=True)

DEVICE_SAMPLERATE = 48000  # Most USB mics native rate (Shure MV7+, Elgato, etc.)
WHISPER_SAMPLERATE = 16000  # Whisper expects 16kHz
CHANNELS = 1
AUDIO_DTYPE = 'float32'
AUDIO_BLOCKSIZE = 1024
MIN_AUDIO_DURATION_S = 0.5
MIN_AUDIO_AMPLITUDE = 0.02
MIN_AUDIO_RMS = 0.01
MIN_TRANSCRIPTION_LENGTH = 1
WHISPER_BEAM_SIZE = 2

# --- Helper Functions ---
def get_app_dir():
    """Get the directory containing the script."""
    return Path(__file__).parent


def get_user_data_dir():
    """Get path to user data directory (~/.voice2text).

    Handles sudo: uses SUDO_USER's home instead of /root.
    """
    # When running with sudo, get the real user's home
    sudo_user = os.environ.get('SUDO_USER')
    if sudo_user:
        return Path(f"/home/{sudo_user}/.voice2text")
    return Path.home() / ".voice2text"


# --- Text Processing Logic ---
# Use possessive quantifiers (++) to prevent catastrophic backtracking
EMAIL_LITERAL_RE = regex.compile(r"\b(?P<user>[\w.+-]++)\s+at\s+(?P<domain>[\w.]++\.[A-Za-z]{2,})\b", flags=regex.IGNORECASE)
EMAIL_SPOKEN_RE = regex.compile(r"\b(?P<user>[\w.+-]++)\s+at\s+(?P<domain_words>(?:[\w]++\s*)+?)(?:\s+dot\s+|\.)(?P<tld>[A-Za-z]{2,})\b", flags=regex.IGNORECASE)

# Dynamic mapping dictionaries - populated by load_custom_mappings()
PUNCTUATION_MAP = {}  # From Punctuation pack
PROGRAMMER_MAP = {}   # From Programmer pack
CUSTOM_MAP = {}       # User custom mappings
CUSTOM_SYMBOL_MAP = {}  # User custom mappings with strip_punctuation=true
NAME_MAP = {}         # Combined map for regex building (all merged)

# Compiled regex - built after mappings are loaded
NAME_RE = None


def load_custom_mappings():
    """Load user custom mappings from ~/.voice2text and enabled map packs from app directory."""
    global NAME_RE

    user_data_dir = get_user_data_dir()
    maps_file = user_data_dir / "custom_mappings.json"
    packs_dir = get_app_dir() / "maps" / "packs"

    if not maps_file.exists():
        print(f"INFO: No custom mappings file found at {maps_file}", file=sys.stderr)
        return

    try:
        with open(maps_file, 'r', encoding='utf-8') as f:
            custom = json.load(f)

        # Load enabled map packs first (so custom mappings can override them)
        enabled_packs = custom.get("enabled_packs", [])
        if enabled_packs and packs_dir.exists():
            for pack_file in packs_dir.glob("*.json"):
                try:
                    with open(pack_file, 'r', encoding='utf-8') as pf:
                        pack_data = json.load(pf)
                        pack_name = pack_data.get("_name", pack_file.stem)

                        if pack_name in enabled_packs:
                            for key, value in pack_data.get("names", {}).items():
                                key_lower = key.lower()
                                if pack_name == "Punctuation":
                                    PUNCTUATION_MAP[key_lower] = value
                                elif pack_name == "Programmer":
                                    PROGRAMMER_MAP[key_lower] = value
                                NAME_MAP[key_lower] = value
                            print(f"INFO: Loaded map pack: {pack_name}", file=sys.stderr)
                except Exception as e:
                    print(f"WARNING: Could not load map pack {pack_file.name}: {e}", file=sys.stderr)

        # Load custom mappings
        for key, entry in custom.get("names", {}).items():
            try:
                key_lower = key.lower()

                # Handle both old (string) and new (dict) formats
                if isinstance(entry, dict):
                    actual_value = entry.get("value", "")
                    strip_punctuation = entry.get("strip_punctuation", False)
                    if not isinstance(actual_value, str):
                        print(f"WARNING: Invalid mapping entry for '{key}': 'value' must be a string, skipping", file=sys.stderr)
                        continue
                elif isinstance(entry, str):
                    actual_value = entry
                    strip_punctuation = False
                else:
                    print(f"WARNING: Invalid mapping entry for '{key}': expected string or dict, got {type(entry).__name__}, skipping", file=sys.stderr)
                    continue

                if strip_punctuation:
                    CUSTOM_SYMBOL_MAP[key_lower] = actual_value
                else:
                    CUSTOM_MAP[key_lower] = actual_value
                NAME_MAP[key_lower] = actual_value
            except Exception as e:
                print(f"WARNING: Error processing mapping '{key}': {e}, skipping", file=sys.stderr)
                continue

        print(f"INFO: Loaded custom mappings from {maps_file}", file=sys.stderr)
        print(f"INFO: Maps loaded - Punctuation: {len(PUNCTUATION_MAP)}, Programmer: {len(PROGRAMMER_MAP)}, Custom: {len(CUSTOM_MAP)}, Custom-Symbol: {len(CUSTOM_SYMBOL_MAP)}", file=sys.stderr)

    except json.JSONDecodeError as e:
        print(f"WARNING: Invalid JSON in {maps_file}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"WARNING: Could not load custom mappings: {e}", file=sys.stderr)

    # Build compiled regex after all mappings are loaded
    if NAME_MAP:
        NAME_RE = regex.compile(r"\b(" + "|".join(map(regex.escape, NAME_MAP.keys())) + r")\b", flags=regex.IGNORECASE)


def replace_misheard_names(text):
    """Apply name mappings to text."""
    if NAME_RE is None:
        return text
    return NAME_RE.sub(lambda m: NAME_MAP[m.group(1).lower()], text)


def strip_trailing_period_if_symbol_map(text):
    """Strip trailing period if text ends with a symbol map value."""
    if not text.endswith('.'):
        return text

    text_without_period = text[:-1].rstrip()

    # Check Punctuation map
    for value in PUNCTUATION_MAP.values():
        if text_without_period.endswith(value):
            return text_without_period

    # Check Programmer map
    for value in PROGRAMMER_MAP.values():
        if text_without_period.endswith(value):
            return text_without_period

    # Check Custom Symbol map
    for value in CUSTOM_SYMBOL_MAP.values():
        if text_without_period.endswith(value):
            return text_without_period

    return text

# Initialize Model
# Check for bundled model first, else download from HuggingFace
LOCAL_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", f"faster-whisper-{MODEL_NAME}")

# Detect GPU availability
if ctranslate2.get_cuda_device_count() > 0:
    DEVICE = "cuda"
    COMPUTE_TYPE = "float16"
    print("INFO: NVIDIA GPU detected, using CUDA acceleration", file=sys.stderr)
else:
    DEVICE = "cpu"
    COMPUTE_TYPE = "int8"
    print("INFO: No NVIDIA GPU detected, using CPU mode (slower)", file=sys.stderr)

print(f"INFO: Loading Whisper Model ({MODEL_NAME})...", file=sys.stderr)
try:
    if os.path.exists(LOCAL_MODEL_PATH):
        print(f"INFO: Using bundled model at {LOCAL_MODEL_PATH}", file=sys.stderr)
        model = WhisperModel(LOCAL_MODEL_PATH, device=DEVICE, compute_type=COMPUTE_TYPE)
    else:
        print(f"INFO: Bundled model not found, downloading {MODEL_NAME} from HuggingFace...", file=sys.stderr)
        model = WhisperModel(MODEL_NAME, device=DEVICE, compute_type=COMPUTE_TYPE)
    print("INFO: Model Loaded.", file=sys.stderr)
except Exception as e:
    print(f"ERROR: Could not load Whisper Model: {e}", file=sys.stderr)
    sys.exit(1)

# Verify xdotool is available
try:
    subprocess.run(['xdotool', '--version'], capture_output=True, check=True)
except (subprocess.CalledProcessError, FileNotFoundError):
    print("ERROR: xdotool not found. Install with: sudo apt install xdotool", file=sys.stderr)
    sys.exit(1)

def replace_spoken_email(text):
    try:
        text = EMAIL_LITERAL_RE.sub(lambda m: f"{m.group('user')}@{m.group('domain')}", text, timeout=1)
        def _format_spoken(m):
            domain = ''.join(m.group('domain_words').split())
            return f"{m.group('user')}@{domain}.{m.group('tld')}"
        return EMAIL_SPOKEN_RE.sub(_format_spoken, text, timeout=1)
    except TimeoutError:
        print(f"WARNING: Email regex timed out, skipping", file=sys.stderr)
        return text

def process_and_validate_text(raw_text):
    if not raw_text or len(raw_text.strip()) < MIN_TRANSCRIPTION_LENGTH:
        return None
    text = regex.sub(r"\s+", ' ', raw_text).strip()
    text = replace_spoken_email(text)
    text = replace_misheard_names(text)  # Applies all mappings (packs + custom)
    text = strip_trailing_period_if_symbol_map(text)  # Remove period if ends with symbol
    text = regex.sub(r"\s+([#?!])", r"\1", text)  # Remove space before punctuation
    # Count words - if 3 or fewer, strip trailing punctuation (likely an edit/insertion)
    word_count = len(text.split())
    if word_count <= 3:
        text = text.rstrip('.!?,;:')
    elif not text.endswith(('.', '!', '?')):
        text += '.'
    print(f"INFO: Final processed text: '{text}'")
    return text

def type_with_xdotool(text):
    """Use xdotool to type text."""
    try:
        result = subprocess.run(
            ['xdotool', 'type', '--clearmodifiers', '--', text],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print(f"ERROR: xdotool returned {result.returncode}: {result.stderr}", file=sys.stderr)
            return False
        return True
    except subprocess.TimeoutExpired:
        print("ERROR: xdotool timed out", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("ERROR: xdotool not found", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ERROR: xdotool failed: {e}", file=sys.stderr)
        return False

def process_and_output(buffer_list):
    if not buffer_list:
        print("INFO: No audio captured; skipping transcription.")
        return

    try:
        audio_np = np.concatenate(buffer_list, axis=0).flatten()
    except ValueError as e:
        print(f"ERROR: Audio buffer malformed: {e}")
        return

    # Resample from device rate (48kHz) to Whisper rate (16kHz)
    audio_np = resample(audio_np, int(len(audio_np) * WHISPER_SAMPLERATE / DEVICE_SAMPLERATE))

    duration = len(audio_np) / WHISPER_SAMPLERATE
    if duration < MIN_AUDIO_DURATION_S:
        return

    rms = np.sqrt(np.mean(np.square(audio_np)))
    peak = np.max(np.abs(audio_np))

    if rms < MIN_AUDIO_RMS and peak < MIN_AUDIO_AMPLITUDE:
        print(f"INFO: Low energy (rms={rms:.4f}, peak={peak:.4f}); skipping transcription.")
        return

    print(f"INFO: Transcribing ({duration:.2f}s)...")
    try:
        segments, info = model.transcribe(audio_np, beam_size=WHISPER_BEAM_SIZE, language=None, task='transcribe')
        raw = ' '.join(seg.text for seg in segments)
        final = process_and_validate_text(raw)

        if final:
            type_with_xdotool(final + ' ')
            if ENABLE_LOGGING:
                ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                with open(os.path.join(LOGS_DIR, f"snippet_{ts}.txt"), 'w', encoding='utf-8') as f:
                    f.write(final + '\n')
    except Exception as e:
        print(f"ERROR during transcription/write: {e}")

# --- Thread-Safe Audio Architecture ---

recording_event = threading.Event()   # Set when we should capture audio
shutdown_event = threading.Event()    # Set when we want to exit the app
audio_queue = queue.Queue()           # Thread-safe data transfer

def audio_callback(indata, frames, time_info, status):
    """Called by sounddevice in a background thread."""
    if status:
        print(f"Audio Status: {status}", file=sys.stderr)
    if recording_event.is_set():
        audio_queue.put(indata.copy())

def audio_stream_worker():
    """Runs in a separate thread. Opens the stream and keeps it alive."""
    # Get device from settings, default to device 3 if not set
    device_name = _settings.get('device')
    audio_device = 3  # fallback default

    if device_name:
        # Find device by name
        try:
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if device_name.lower() in dev['name'].lower():
                    audio_device = i
                    break
        except Exception as e:
            print(f"WARNING: Could not lookup device '{device_name}': {e}", file=sys.stderr)

    try:
        print(f">> Opening audio device: {audio_device}")
        with sd.InputStream(device=audio_device, samplerate=DEVICE_SAMPLERATE,
                            channels=CHANNELS,
                            dtype=AUDIO_DTYPE,
                            blocksize=AUDIO_BLOCKSIZE,
                            callback=audio_callback):
            print(">> Audio Stream Active. Ready to record.")
            while not shutdown_event.is_set():
                time.sleep(0.1)
    except Exception as e:
        print(f"CRITICAL AUDIO FAILURE in worker thread: {e}", file=sys.stderr)

def drain_queue():
    """Safely drains the queue into a list."""
    data = []
    while True:
        try:
            data.append(audio_queue.get_nowait())
        except queue.Empty:
            break
    return data

# --- Hotkey helpers ---
def exit_hotkey_pressed():
    """Check if Ctrl+Shift+Q is pressed."""
    return keyboard.is_pressed('ctrl') and keyboard.is_pressed('shift') and keyboard.is_pressed('q')

def continuous_toggle_pressed():
    """Check if Ctrl+Shift+Space is pressed."""
    return keyboard.is_pressed('ctrl') and keyboard.is_pressed('shift') and keyboard.is_pressed('space')

# --- System Tray Application ---

class Voice2TextApp:
    """Main application with system tray icon."""

    def __init__(self):
        self.continuous_mode = False
        self.toggle_prev = False
        self.status_text = "Idle"
        self.audio_thread = None

        # Create Qt application
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Create system tray icon
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon(ICON_IDLE))
        self.tray.setToolTip(f"Voice2Text v{VERSION} - Idle")

        # Create context menu
        self._create_menu()

        # Show tray icon
        self.tray.show()

        # Setup keyboard polling timer (20ms interval, same as original)
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._poll_keyboard)
        self.poll_timer.start(20)

    def _create_menu(self):
        """Create the right-click context menu."""
        menu = QMenu()

        # Version header
        version_action = QAction(f"Voice2Text v{VERSION}", menu)
        version_action.setEnabled(False)
        menu.addAction(version_action)

        menu.addSeparator()

        # Status display (we'll update this dynamically)
        self.status_action = QAction(f"Status: {self.status_text}", menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)

        menu.addSeparator()

        # Main actions
        menu.addAction("Show Configurator", self._show_configurator)
        menu.addAction("Reload Mapping Files", self._reload_mappings)

        menu.addSeparator()

        menu.addAction("Show Log Window", self._show_log_window)
        menu.addAction("Open Mapping/Rules", self._open_mapping_rules)
        menu.addAction("Open Logs Folder", self._open_logs)

        menu.addSeparator()

        menu.addAction("Show Help", self._show_help)
        menu.addAction("Show Shortcuts", self._show_shortcuts)
        menu.addAction("Help: System Tray", self._show_systray_help)

        menu.addSeparator()

        menu.addAction("Exit", self._exit_app)

        self.tray.setContextMenu(menu)

    def _update_status(self, status):
        """Update status text and icon."""
        self.status_text = status
        self.status_action.setText(f"Status: {status}")

        if status == "Recording":
            self.tray.setIcon(QIcon(ICON_RECORDING))
            self.tray.setToolTip(f"Voice2Text v{VERSION} - Recording")
        elif status == "Transcribing":
            self.tray.setIcon(QIcon(ICON_TRANSCRIBING))
            self.tray.setToolTip(f"Voice2Text v{VERSION} - Transcribing")
        else:
            self.tray.setIcon(QIcon(ICON_IDLE))
            self.tray.setToolTip(f"Voice2Text v{VERSION} - Idle")

    def _poll_keyboard(self):
        """Poll keyboard state (called every 20ms by QTimer)."""
        # Exit if audio worker died
        if self.audio_thread and not self.audio_thread.is_alive():
            print("CRITICAL: Audio thread died unexpectedly. Exiting.")
            self._exit_app()
            return

        # Ctrl+Shift+Space toggle (edge-detected)
        toggle_now = continuous_toggle_pressed()
        if toggle_now and not self.toggle_prev:
            self.continuous_mode = not self.continuous_mode
            if self.continuous_mode:
                print("INFO: Continuous mode ON")
                self._update_status("Recording (Continuous)")
                drain_queue()
                recording_event.set()
            else:
                print("INFO: Continuous mode OFF")
                recording_event.clear()
                self._update_status("Transcribing")
                QTimer.singleShot(50, self._process_continuous_audio)
        self.toggle_prev = toggle_now

        # If continuous mode is ON, check for exit only
        if self.continuous_mode:
            if exit_hotkey_pressed():
                print("Exiting...")
                self._exit_app()
            return

        # Alt+Shift press/release behavior when not in continuous mode
        pressed = keyboard.is_pressed('alt') and keyboard.is_pressed('shift')

        if pressed and not recording_event.is_set():
            print("Started recording...")
            self._update_status("Recording")
            drain_queue()
            recording_event.set()
        elif not pressed and recording_event.is_set():
            print("Stopping & processing...")
            recording_event.clear()
            self._update_status("Transcribing")
            # Use singleShot to process after a small delay
            QTimer.singleShot(50, self._process_audio)

        if exit_hotkey_pressed():
            print("Exiting...")
            self._exit_app()

    def _process_audio(self):
        """Process captured audio after recording stops."""
        captured_audio = drain_queue()
        process_and_output(captured_audio)
        self._update_status("Idle")

    def _process_continuous_audio(self):
        """Process audio when continuous mode turns off."""
        captured_audio = drain_queue()
        process_and_output(captured_audio)
        self._update_status("Idle")

    # --- Menu Actions ---

    def _show_configurator(self):
        """Launch the configurator GUI."""
        configurator_path = get_app_dir() / "configurator_gui.py"
        if configurator_path.exists():
            subprocess.Popen([sys.executable, str(configurator_path)])
        else:
            QMessageBox.warning(None, "Not Found",
                f"Configurator not found at:\n{configurator_path}")

    def _reload_mappings(self, silent=False):
        """Reload mapping files without restarting."""
        global NAME_MAP, NAME_RE, PUNCTUATION_MAP, PROGRAMMER_MAP, CUSTOM_MAP, CUSTOM_SYMBOL_MAP

        # Clear existing mappings
        NAME_MAP.clear()
        PUNCTUATION_MAP.clear()
        PROGRAMMER_MAP.clear()
        CUSTOM_MAP.clear()
        CUSTOM_SYMBOL_MAP.clear()

        # Reload
        load_custom_mappings()

        count = len(NAME_MAP)
        if silent:
            # Auto-reload: just print to console
            print(f"INFO: Mappings auto-reloaded ({count} active)")
        else:
            # Manual reload: show dialog
            QMessageBox.information(None, "Mappings Reloaded",
                f"Mapping files reloaded.\n\n{count} mappings active.")

    def _on_file_changed(self, path):
        """Called when a watched file changes on disk."""
        global ENABLE_LOGGING

        print(f"INFO: Detected change in {path}")

        if "custom_mappings.json" in path:
            self._reload_mappings(silent=True)
        elif "settings.json" in path:
            # Reload settings (for logging toggle, etc.)
            new_settings = _load_settings()
            old_logging = ENABLE_LOGGING
            ENABLE_LOGGING = new_settings.get('log', False)
            if ENABLE_LOGGING != old_logging:
                status = "ENABLED" if ENABLE_LOGGING else "DISABLED"
                print(f"INFO: Logging {status}")

        # Re-add the watch (some systems remove it after file is modified)
        if hasattr(self, 'file_watcher'):
            self.file_watcher.addPath(path)

    def _show_log_window(self):
        """Show a window with recent transcription logs."""
        logs_path = Path(LOGS_DIR)

        # Create dialog
        dialog = QDialog()
        dialog.setWindowTitle("Voice2Text - Recent Transcriptions")
        dialog.setMinimumSize(600, 400)
        dialog.resize(600, 400)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QLabel("Recent Transcriptions")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        # Text area
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("monospace", 10))
        layout.addWidget(text_edit)

        def load_logs():
            """Load recent log files."""
            if not logs_path.exists():
                text_edit.setPlainText(
                    "No logs directory found.\n\n"
                    "Run Voice2Text with --log to enable logging:\n"
                    "  ./run-voice2text.bash --log"
                )
                return

            # Get recent log files (last 50), sorted by modification time
            all_logs = list(logs_path.glob("snippet_*.txt"))
            log_files = sorted(all_logs, key=lambda f: f.stat().st_mtime, reverse=True)[:50]

            if not log_files:
                text_edit.setPlainText(
                    "No transcription logs found.\n\n"
                    "Logs will appear here after you make transcriptions\n"
                    "with the --log option enabled."
                )
                return

            # Read and display logs (newest first)
            lines = []
            for log_file in log_files:  # Already sorted newest first
                try:
                    # Parse timestamp from filename: snippet_YYYYMMDD_HHMMSS_ffffff.txt
                    name = log_file.stem  # snippet_20251223_143022_123456
                    parts = name.split('_')
                    if len(parts) >= 3:
                        date_str = parts[1]  # 20251223
                        time_str = parts[2]  # 143022
                        formatted_time = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
                    else:
                        formatted_time = log_file.name

                    content = log_file.read_text(encoding='utf-8').strip()
                    lines.append(f"[{formatted_time}] {content}")
                except Exception as e:
                    lines.append(f"[Error reading {log_file.name}: {e}]")

            text_edit.setPlainText('\n'.join(lines))
            # Scroll to top (newest entries are first)
            text_edit.verticalScrollBar().setValue(0)

        # Load initial content
        load_logs()

        # Buttons
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(load_logs)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        dialog.exec()

    def _open_mapping_rules(self):
        """Launch the mapping/rules editor."""
        editor_path = get_app_dir() / "mapping_rules_gui.py"
        if editor_path.exists():
            subprocess.Popen([sys.executable, str(editor_path)])
        else:
            QMessageBox.warning(None, "Not Found",
                f"Mapping editor not found at:\n{editor_path}")

    def _open_logs(self):
        """Open the logs folder in file manager."""
        logs_path = Path(LOGS_DIR)
        if logs_path.exists():
            subprocess.run(['xdg-open', str(logs_path)])
        else:
            QMessageBox.warning(None, "Not Found",
                f"Logs folder not found:\n{logs_path}\n\nRun with --log to enable logging.")

    def _show_help(self):
        """Show general help."""
        help_text = """Voice2Text for Ubuntu

RECORDING:
• Hold Alt+Shift to record
• Release to stop and transcribe
• Text is typed at cursor position

CONTINUOUS MODE:
• Ctrl+Shift+Space toggles continuous recording
• Keeps recording until toggled off

EXIT:
• Ctrl+Shift+Q to quit
• Or use Exit from tray menu"""
        QMessageBox.information(None, "Voice2Text Help", help_text)

    def _show_shortcuts(self):
        """Show keyboard shortcuts."""
        shortcuts = """Keyboard Shortcuts

Alt+Shift (hold)     Record audio
Alt+Shift (release)  Stop & transcribe

Ctrl+Shift+Space     Toggle continuous mode
Ctrl+Shift+Q         Exit application"""
        QMessageBox.information(None, "Keyboard Shortcuts", shortcuts)

    def _show_systray_help(self):
        """Show system tray help."""
        help_text = """System Tray Icon

The tray icon shows the current state:
• Gray: Idle, ready to record
• Red: Recording audio
• Blue: Transcribing

Right-click the icon for options.
The icon appears in your top panel."""
        QMessageBox.information(None, "System Tray Help", help_text)

    def _exit_app(self):
        """Exit the application."""
        shutdown_event.set()
        self.poll_timer.stop()
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=1.0)
        self.app.quit()

    def run(self):
        """Start the application."""
        # Load custom mappings
        load_custom_mappings()

        # Watch for changes to mappings and settings files
        user_data_dir = get_user_data_dir()
        mappings_file = user_data_dir / "custom_mappings.json"
        settings_file = user_data_dir / "settings.json"

        watch_files = []
        if mappings_file.exists():
            watch_files.append(str(mappings_file))
        if settings_file.exists():
            watch_files.append(str(settings_file))

        if watch_files:
            self.file_watcher = QFileSystemWatcher(watch_files)
            self.file_watcher.fileChanged.connect(self._on_file_changed)
            print(f"INFO: Watching for changes: {', '.join(watch_files)}")

        print(">> Voice2Text with System Tray")
        print(">> Hold Alt+Shift to RECORD; release to STOP & TRANSCRIBE.")
        print(">> Press Ctrl+Shift+Q to exit. Press Ctrl+Shift+Space to toggle continuous mode.")
        print(">> NOTE: Requires sudo on Linux (keyboard module needs root)")
        print(f">> Logging: {'ENABLED (~/logs)' if ENABLE_LOGGING else 'DISABLED (use --log to enable)'}")

        # Start audio thread
        self.audio_thread = threading.Thread(target=audio_stream_worker, daemon=True)
        self.audio_thread.start()
        time.sleep(0.5)

        if not self.audio_thread.is_alive():
            print("ERROR: Audio thread failed to start. Exiting.")
            sys.exit(1)

        # Run Qt event loop
        try:
            sys.exit(self.app.exec())
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
        finally:
            shutdown_event.set()
            if self.audio_thread.is_alive():
                self.audio_thread.join(timeout=1.0)
            print("Done.")


# --- Main Entry Point ---

if __name__ == '__main__':
    app = Voice2TextApp()
    app.run()
