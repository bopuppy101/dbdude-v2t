#!/usr/bin/env python3
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.
# dbdude-v2t - Speech to text with GUI configurator
# Uses AutoHotkey for text output instead of keyboard.write()

VERSION = "2026"

import os
# Allow duplicate OpenMP runtimes (NumPy MKL + ONNX) to coexist
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Add NVIDIA CUDA DLL paths when running from a venv with pip-installed CUDA packages
import sys
_site_packages = os.path.join(sys.prefix, "Lib", "site-packages")
for _nvidia_lib in ["nvidia/cublas/bin", "nvidia/cudnn/bin"]:
    _dll_path = os.path.join(_site_packages, _nvidia_lib)
    if os.path.isdir(_dll_path):
        os.add_dll_directory(_dll_path)
        os.environ["PATH"] = _dll_path + os.pathsep + os.environ.get("PATH", "")
import regex  # Use regex instead of re for possessive quantifiers (prevents catastrophic backtracking)
import time
import json
import threading
import queue
import subprocess
import argparse
import webbrowser
import atexit
import signal
import ctypes
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import sounddevice as sd
import keyboard
from faster_whisper import WhisperModel
import ctranslate2
import pystray
from PIL import Image

ERROR_LOG_FILE = Path.home() / "logs" / "v2t-error.log"


def log_error(message: str):
    """Write error to both stderr and persistent log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line, file=sys.stderr)
    try:
        ERROR_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line + "\n")
    except Exception:
        pass  # If we can't write to file, at least stderr got it


# Global Tk root - initialized once at startup before threads start
# All dialogs use Toplevel on this root to avoid Tk() creation issues in compiled code
_tk_root = None


def init_tk_root():
    """Initialize the global Tk root. Must be called from main thread before any threads start."""
    global _tk_root
    if _tk_root is None:
        _tk_root = tk.Tk()
        _tk_root.withdraw()  # Hide the root window


def get_tk_root():
    """Get the global Tk root, initializing if needed."""
    global _tk_root
    if _tk_root is None:
        init_tk_root()
    return _tk_root


def show_error_dialog(title: str, message: str):
    """Show error dialog that requires deliberate dismissal (not just Enter key)."""
    dialog = tk.Toplevel(get_tk_root())
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.attributes('-topmost', True)
    dialog.grab_set()  # Make modal

    # Message frame with padding
    msg_frame = ttk.Frame(dialog, padding=20)
    msg_frame.pack(fill=tk.BOTH, expand=True)

    # Error icon and message
    ttk.Label(msg_frame, text="⚠", font=("Segoe UI", 32)).pack(pady=(0, 10))
    ttk.Label(msg_frame, text=message, wraplength=350, justify=tk.LEFT,
              font=("Segoe UI", 10)).pack(pady=(0, 20))

    # Close button - NOT focused by default
    btn = ttk.Button(msg_frame, text="Close", command=dialog.destroy, width=15)
    btn.pack()

    # Prevent Enter key from dismissing - must Tab to button first or use mouse
    dialog.bind('<Return>', lambda e: None)  # Disable Enter

    # Center on screen
    dialog.update_idletasks()
    w, h = dialog.winfo_width(), dialog.winfo_height()
    x = (dialog.winfo_screenwidth() - w) // 2
    y = (dialog.winfo_screenheight() - h) // 2
    dialog.geometry(f"+{x}+{y}")

    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.wait_window()


# --- Configuration Constants ---
# Default model to fall back to if settings.json has invalid model
# "base" is bundled with the installer and always available
DEFAULT_MODEL = "base"
VALID_LANGUAGES = [
    ('English', 'en'), ('Spanish', 'es'), ('French', 'fr'), ('German', 'de'),
    ('Italian', 'it'), ('Portuguese', 'pt'), ('Dutch', 'nl'), ('Russian', 'ru'),
    ('Chinese', 'zh'), ('Japanese', 'ja'), ('Korean', 'ko'), ('Arabic', 'ar'),
    ('Hindi', 'hi'), ('Polish', 'pl'), ('Turkish', 'tr'), ('Vietnamese', 'vi'),
    ('Thai', 'th'), ('Ukrainian', 'uk'), ('Czech', 'cs'), ('Swedish', 'sv')
]
VALID_LANGUAGE_CODES = [code for name, code in VALID_LANGUAGES]

SAMPLERATE = 16000
CHANNELS = 1
AUDIO_DTYPE = 'float32'
AUDIO_BLOCKSIZE = 1024
MIN_AUDIO_DURATION_S = 0.5
MIN_AUDIO_AMPLITUDE = 0.02
MIN_AUDIO_RMS = 0.01
MIN_TRANSCRIPTION_LENGTH = 1
WHISPER_BEAM_SIZE = 2

# App data directory name
# Module-level debug flag (set by run_voice2text)
_DEBUG_MODE = False


# --- Helper Functions ---
def get_app_dir():
    """Get the directory containing the app (works for both Python and Nuitka exe)."""
    # For Nuitka onefile: use sys.argv[0] which has the original exe path
    # (sys.executable and __nuitka_binary_dir point to temp extraction folder)
    if sys.argv and sys.argv[0]:
        argv0_path = Path(sys.argv[0]).resolve().parent
        if (argv0_path / 'maps').exists():
            return argv0_path
    # Fallback for Nuitka standalone or PyInstaller
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    # For regular Python
    return Path(__file__).parent


def get_user_data_dir():
    """Get path to user data directory (~/.dbdude-v2t)."""
    return Path.home() / ".dbdude-v2t"


def is_nuitka_exe():
    """Check if running as a Nuitka-compiled executable."""
    exe_name = Path(sys.executable).name.lower()
    return (
        "__compiled__" in globals() or
        getattr(sys, 'frozen', False) or
        (exe_name.endswith('.exe') and not exe_name.startswith('python'))
    )


def get_mapping_rules_path():
    """Get path to v2t-mapping-rules executable/script."""
    if is_nuitka_exe():
        return Path(sys.executable).parent / "v2t-mapping-rules.exe"
    else:
        return Path(__file__).parent / "mapping_rules_gui.py"


def get_help_dir():
    """Get path to help files directory."""
    return get_app_dir() / "help"


def open_help_file(filename):
    """Open a help file in the default browser."""
    import webbrowser
    help_path = get_help_dir() / filename
    if help_path.exists():
        webbrowser.open(f"file://{help_path}")
    else:
        print(f"ERROR: Help file not found: {help_path}", file=sys.stderr)


# --- Settings Persistence ---
def get_settings_path():
    """Get path to settings file (stored in ~/.dbdude-v2t)."""
    return get_user_data_dir() / "settings.json"


def load_saved_settings():
    """Load settings from config file, return defaults if not found."""
    defaults = {
        'model': 'base',
        'language': 'en',
        'log': False,
        'device': None,
        'debug': False,
        'push_to_talk_keys': {
            'left_alt_shift': True,
            'caps_lock': True,
            'right_alt': False,
            'left_ctrl_shift': False
        }
    }
    path = get_settings_path()
    if path.exists():
        try:
            with open(path, 'r') as f:
                saved = json.load(f)
                defaults.update(saved)
            print(f"INFO: Loaded settings from {path}", file=sys.stderr)
        except Exception as e:
            print(f"WARNING: Could not load settings: {e}", file=sys.stderr)
    return defaults


def save_settings(settings):
    """Save settings to config file."""
    path = get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, 'w') as f:
            json.dump(settings, f, indent=2)
        print(f"INFO: Saved settings to {path}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Could not save settings: {e}", file=sys.stderr)


def get_input_devices():
    """Get list of available input (microphone) devices."""
    devices = sd.query_devices()
    default_input = sd.default.device[0]
    input_devices = []
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            is_default = (i == default_input)
            input_devices.append({
                'index': i,
                'name': d['name'],
                'is_default': is_default
            })
    return input_devices


def find_device_by_name(device_name):
    """Find device index by name. Returns None if not found."""
    if device_name is None:
        return None
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0 and device_name.lower() in d['name'].lower():
            return i
    print(f"WARNING: Device '{device_name}' not found, using system default", file=sys.stderr)
    return None


def get_icon_path(icon_name="v2t.ico"):
    """Get path to icon file."""
    return get_app_dir() / "icons" / icon_name


def load_icon(icon_name="v2t.ico"):
    """Load icon as PIL Image for pystray."""
    icon_path = get_icon_path(icon_name)
    if icon_path.exists():
        return Image.open(icon_path)
    # Fallback: create a simple colored square if icon not found
    img = Image.new('RGBA', (64, 64), (74, 144, 217, 255))
    return img


# --- Console Window Management (Windows) ---
def get_console_window():
    """Get handle to console window."""
    if sys.platform == 'win32':
        return ctypes.windll.kernel32.GetConsoleWindow()
    return None


def show_console():
    """Show the console window."""
    hwnd = get_console_window()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW = 5


def hide_console():
    """Hide the console window."""
    hwnd = get_console_window()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0


def is_console_visible():
    """Check if console window is visible."""
    hwnd = get_console_window()
    if hwnd:
        return ctypes.windll.user32.IsWindowVisible(hwnd)
    return False


# --- Text Processing ---
# Use possessive quantifiers (++) to prevent catastrophic backtracking
EMAIL_LITERAL_RE = regex.compile(r"\b(?P<user>[\w.+-]++)\s+at\s+(?P<domain>[\w.]++\.[A-Za-z]{2,})\b", flags=regex.IGNORECASE)
EMAIL_SPOKEN_RE = regex.compile(r"\b(?P<user>[\w.+-]++)\s+at\s+(?P<domain_words>(?:[\w]++\s*)+?)(?:\s+dot\s+|\.)(?P<tld>[A-Za-z]{2,})\b", flags=regex.IGNORECASE)

# Separate maps for each source - allows tracking which map made a substitution
PUNCTUATION_MAP = {}  # From Punctuation pack (strip trailing punctuation)
PROGRAMMER_MAP = {}   # From Programmer pack (strip trailing punctuation)
CUSTOM_MAP = {}       # User custom mappings (keep trailing punctuation)
CUSTOM_SYMBOL_MAP = {}  # User custom mappings marked as "strip trailing punctuation"
NAME_MAP = {}         # Combined map for regex building (all merged)

WILDCARD_MAP = {}  # Patterns containing % or _ wildcards
WILDCARD_MODE = "sql92"  # "none" or "sql92"
RULES = []  # List of user-defined formatting rules
WHITESPACE_STRIP_MAP = {}  # Maps replacement value to (strip_before, strip_after) tuple
name_re = None  # Compiled regex for name/mapping matching


def build_pattern(key):
    """Build a regex pattern for a mapping key, using lookarounds for keys with non-word chars."""
    escaped = regex.escape(key)
    if regex.search(r'[^\w\s]', key):
        return f"(?<!\\w){escaped}(?!\\w)"
    else:
        return f"\\b{escaped}\\b"


def build_name_re():
    """Compile the name mapping regex from current NAME_MAP keys."""
    global name_re
    if NAME_MAP:
        name_re = regex.compile("(" + "|".join(build_pattern(k) for k in NAME_MAP.keys()) + ")", flags=regex.IGNORECASE)
    else:
        name_re = None


def load_custom_mappings():
    """Load user custom mappings from ~/.dbdude-v2t and enabled map packs from app directory."""
    global WILDCARD_MODE

    # User data in ~/.dbdude-v2t
    user_data_dir = get_user_data_dir()
    maps_file = user_data_dir / "custom_mappings.json"

    # Map packs ship with the app
    packs_dir = get_app_dir() / "maps" / "packs"

    if not maps_file.exists():
        print(f"INFO: No custom mappings file found at {maps_file}", file=sys.stderr)
        return

    try:
        with open(maps_file, 'r', encoding='utf-8') as f:
            custom = json.load(f)

        # Get wildcard mode
        WILDCARD_MODE = custom.get("wildcard_mode", "sql92")
        print(f"INFO: Wildcard mode: {WILDCARD_MODE}", file=sys.stderr)

        # Load enabled map packs first (so custom mappings can override them)
        enabled_packs = custom.get("enabled_packs", [])
        if enabled_packs and packs_dir.exists():
            for pack_file in packs_dir.glob("*.json"):
                try:
                    with open(pack_file, 'r', encoding='utf-8') as pf:
                        pack_data = json.load(pf)
                        pack_name = pack_data.get("_name", pack_file.stem)

                        if pack_name in enabled_packs:
                            for key, entry in pack_data.get("names", {}).items():
                                key_lower = key.lower()
                                # Handle both string and dict formats
                                if isinstance(entry, dict):
                                    actual_value = entry.get("value", "")
                                    strip_ws_before = entry.get("strip_whitespace_before", False)
                                    strip_ws_after = entry.get("strip_whitespace_after", False)
                                    if strip_ws_before or strip_ws_after:
                                        WHITESPACE_STRIP_MAP[actual_value] = (strip_ws_before, strip_ws_after)
                                else:
                                    actual_value = entry
                                # Store in the appropriate map based on pack name
                                if pack_name == "Punctuation":
                                    PUNCTUATION_MAP[key_lower] = actual_value
                                elif pack_name == "Programmer":
                                    PROGRAMMER_MAP[key_lower] = actual_value
                                # Also add to combined NAME_MAP for regex building
                                NAME_MAP[key_lower] = actual_value
                            print(f"INFO: Loaded map pack: {pack_name}", file=sys.stderr)
                except Exception as e:
                    print(f"WARNING: Could not load map pack {pack_file.name}: {e}", file=sys.stderr)

        # Load custom mappings - separate wildcards from literals
        # Supports both old format ("key": "value") and new format ("key": {"value": "x", "strip_punctuation": true})
        for key, entry in custom.get("names", {}).items():
            try:
                key_lower = key.lower()

                # Handle both old (string) and new (dict) formats
                if isinstance(entry, dict):
                    actual_value = entry.get("value", "")
                    strip_punctuation = entry.get("strip_punctuation", False)
                    strip_ws_before = entry.get("strip_whitespace_before", False)
                    strip_ws_after = entry.get("strip_whitespace_after", False)
                    if not isinstance(actual_value, str):
                        print(f"WARNING: Invalid mapping entry for '{key}': 'value' must be a string, skipping", file=sys.stderr)
                        continue
                    # Add to whitespace strip map if either flag is set
                    if strip_ws_before or strip_ws_after:
                        WHITESPACE_STRIP_MAP[actual_value] = (strip_ws_before, strip_ws_after)
                elif isinstance(entry, str):
                    # Old format - just a string
                    actual_value = entry
                    strip_punctuation = False
                else:
                    print(f"WARNING: Invalid mapping entry for '{key}': expected string or dict, got {type(entry).__name__}, skipping", file=sys.stderr)
                    continue

                if WILDCARD_MODE == "sql92" and ('%' in key_lower or '_' in key_lower):
                    WILDCARD_MAP[key_lower] = actual_value
                else:
                    if strip_punctuation:
                        CUSTOM_SYMBOL_MAP[key_lower] = actual_value
                    else:
                        CUSTOM_MAP[key_lower] = actual_value
                    NAME_MAP[key_lower] = actual_value
            except Exception as e:
                print(f"WARNING: Error processing mapping '{key}': {e}, skipping", file=sys.stderr)
                continue

        if WILDCARD_MAP:
            print(f"INFO: Loaded {len(WILDCARD_MAP)} wildcard pattern(s)", file=sys.stderr)

        print(f"INFO: Loaded custom mappings from {maps_file.resolve()}", file=sys.stderr)
        print(f"INFO: Maps loaded - Punctuation: {len(PUNCTUATION_MAP)}, Programmer: {len(PROGRAMMER_MAP)}, Custom: {len(CUSTOM_MAP)}, Custom-Symbol: {len(CUSTOM_SYMBOL_MAP)}, WS-Strip: {len(WHITESPACE_STRIP_MAP)}", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"WARNING: Invalid JSON in {maps_file}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"WARNING: Could not load custom mappings: {e}", file=sys.stderr)


def load_rules():
    """Load user-defined rules from ~/.dbdude-v2t/rules.json."""
    global RULES

    rules_file = get_user_data_dir() / "rules.json"

    if not rules_file.exists():
        print(f"INFO: No rules file found at {rules_file}", file=sys.stderr)
        return

    try:
        with open(rules_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        RULES = [r for r in data.get("rules", []) if r.get("enabled", True)]
        print(f"INFO: Loaded {len(RULES)} rule(s) from {rules_file.resolve()}", file=sys.stderr)

    except json.JSONDecodeError as e:
        print(f"WARNING: Invalid JSON in {rules_file}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"WARNING: Could not load rules: {e}", file=sys.stderr)


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
        # Strip existing punctuation first, then add period
        text = text.rstrip('.!?,;:')
        return text + '.'
    elif action == "add_question":
        # Strip existing punctuation first, then add question mark
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
            rule_name = rule.get("name", "Unnamed")
            if _DEBUG_MODE:
                print(f"DEBUG: Rule '{rule_name}' matched", file=sys.stderr)
            for action in actions:
                text = apply_action(text, action)
            # First matching rule applies, then stop
            break

    return text


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


def replace_misheard_names(text, name_re):
    """Apply name mappings to text with marker-based whitespace stripping."""
    if name_re is None:
        return text

    # Markers for whitespace stripping (processed after all replacements)
    STRIP_BEFORE = '\x01'
    STRIP_AFTER = '\x02'

    def replace_and_log(m):
        from_text = m.group(1)
        to_text = NAME_MAP[from_text.lower()]

        # Check if this replacement has whitespace strip flags
        strip_before, strip_after = WHITESPACE_STRIP_MAP.get(to_text, (False, False))

        # Add markers for later whitespace stripping
        prefix = STRIP_BEFORE if strip_before else ''
        suffix = STRIP_AFTER if strip_after else ''

        if _DEBUG_MODE:
            print(f"DEBUG: Mapping '{from_text}' → '{to_text}'", file=sys.stderr)
        return prefix + to_text + suffix

    try:
        text = name_re.sub(replace_and_log, text, timeout=0.5)
        # Strip whitespace around markers, then remove markers
        text = regex.sub(r'\s*\x01', '', text)  # Strip space before + remove marker
        text = regex.sub(r'\x02\s*', '', text)  # Remove marker + strip space after
    except TimeoutError:
        print(f"WARNING: Name mapping regex timed out, skipping", file=sys.stderr)

    # Safety: always remove any remaining markers (guaranteed cleanup)
    text = text.replace(STRIP_BEFORE, '').replace(STRIP_AFTER, '')
    return text


def strip_trailing_period_if_symbol_map(text):
    """Strip trailing period if text ENDS with a symbol map value.

    Symbol maps include: Punctuation pack, Programmer pack, and Custom mappings with strip_punctuation=true.
    Only strips period when the LAST thing in the text is from one of these maps.
    Does NOT strip if text ends with a regular word (even if maps were used earlier).

    Examples:
    - '!.' → '!' (ends with Punctuation map value '!')
    - 'hello!.' → 'hello!' (ends with Punctuation map value '!')
    - '==.' → '==' (ends with Programmer map value '==')
    - 'hello.' → 'hello.' (ends with regular word, keep period)
    - '! hello.' → '! hello.' (ends with regular word, keep period)
    """
    if not text.endswith('.'):
        return text

    text_without_period = text[:-1].rstrip()

    # Check if text ends with any Punctuation map value
    for value in PUNCTUATION_MAP.values():
        if text_without_period.endswith(value):
            if _DEBUG_MODE:
                print(f"DEBUG: Stripped trailing period - text ends with Punctuation map value '{value}'", file=sys.stderr)
            return text_without_period

    # Check if text ends with any Programmer map value
    for value in PROGRAMMER_MAP.values():
        if text_without_period.endswith(value):
            if _DEBUG_MODE:
                print(f"DEBUG: Stripped trailing period - text ends with Programmer map value '{value}'", file=sys.stderr)
            return text_without_period

    # Check if text ends with any Custom Symbol map value (user mappings with strip_punctuation=true)
    for value in CUSTOM_SYMBOL_MAP.values():
        if text_without_period.endswith(value):
            if _DEBUG_MODE:
                print(f"DEBUG: Stripped trailing period - text ends with Custom Symbol map value '{value}'", file=sys.stderr)
            return text_without_period

    return text


def sql92_pattern_to_regex(pattern):
    """Convert SQL-92 LIKE pattern to regex. Each word is matched separately."""
    # Split pattern into words
    pattern_words = pattern.split()
    regex_parts = []
    for word in pattern_words:
        # Escape regex metacharacters except our wildcards
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
    # Join with whitespace pattern (one or more spaces)
    return r'\s+'.join(regex_parts)


def apply_wildcard_mappings(text):
    """Apply SQL-92 wildcard pattern mappings to text. Called after literal mappings."""
    if not WILDCARD_MAP or WILDCARD_MODE != "sql92":
        return text

    text_lower = text.lower()

    for pattern, replacement in WILDCARD_MAP.items():
        regex_pattern = sql92_pattern_to_regex(pattern)

        try:
            # Use word boundaries to match whole phrases
            full_pattern = r'\b' + regex_pattern + r'\b'
            compiled = regex.compile(full_pattern, regex.IGNORECASE)

            # Check if pattern matches
            match = compiled.search(text_lower)
            if match:
                # Replace in original text (preserving case of replacement)
                text = compiled.sub(replacement, text, count=1)
                text_lower = text.lower()  # Update for next iteration
                if _DEBUG_MODE:
                    print(f"DEBUG: Wildcard '{pattern}' matched, replaced with '{replacement}'", file=sys.stderr)
        except regex.error as e:
            print(f"WARNING: Invalid wildcard pattern '{pattern}': {e}", file=sys.stderr)

    return text


def deduplicate_spaces(text):
    """Collapse runs of 2+ spaces to a single space."""
    return regex.sub(r' {2,}', ' ', text)


# Whisper hallucination patterns - exact match only (O(1) set lookup)
# These appear when Whisper hallucinates during silence/noise
# Only filters when this is the ENTIRE transcription, not part of a sentence
WHISPER_HALLUCINATIONS = {
    "thank you.", "thank you",
    "thanks.", "thanks",
    "thank you for watching.", "thank you for watching",
    "thanks for watching.", "thanks for watching",
    "thank you for listening.", "thank you for listening",
    "thanks for listening.", "thanks for listening",
    "bye.", "bye", "goodbye.", "goodbye",
    "you.", "you",
}


def is_whisper_hallucination(text):
    """Check if entire text is a known Whisper hallucination. O(1) set lookup."""
    if not text:
        return True
    normalized = text.strip().lower()
    return normalized in WHISPER_HALLUCINATIONS


def process_and_validate_text(raw_text):
    if not raw_text or len(raw_text.strip()) < MIN_TRANSCRIPTION_LENGTH:
        return None
    if is_whisper_hallucination(raw_text):
        if _DEBUG_MODE:
            print(f"DEBUG: Filtered hallucination: '{raw_text.strip()}'", file=sys.stderr)
        return None
    text = raw_text.strip()
    text = deduplicate_spaces(text)
    if _DEBUG_MODE:
        print(f"DEBUG: After dedupe_spaces: '{text}'", file=sys.stderr)
    text = replace_spoken_email(text)
    if _DEBUG_MODE:
        print(f"DEBUG: After email: '{text}'", file=sys.stderr)
    text = replace_misheard_names(text, name_re)
    if _DEBUG_MODE:
        print(f"DEBUG: After names: '{text}'", file=sys.stderr)
    text = apply_wildcard_mappings(text)
    if _DEBUG_MODE:
        print(f"DEBUG: After wildcards: '{text}'", file=sys.stderr)
    text = strip_trailing_period_if_symbol_map(text)
    if _DEBUG_MODE:
        print(f"DEBUG: After strip_period: '{text}'", file=sys.stderr)
    text = apply_rules(text)
    return text


def type_with_ahk(text, type_text_exe):
    """Use AutoHotkey to type text via SendInput."""
    try:
        result = subprocess.run(
            [type_text_exe, text],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print(f"ERROR: AutoHotkey returned {result.returncode}: {result.stderr}", file=sys.stderr)
            return False
        return True
    except subprocess.TimeoutExpired:
        print("ERROR: AutoHotkey timed out", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(f"ERROR: type_text.exe not found at {type_text_exe}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ERROR: AutoHotkey failed: {e}", file=sys.stderr)
        return False


# --- Systray Manager ---
class SystrayManager:
    """Manages the system tray icon and menu."""

    def __init__(self, on_exit_callback=None, on_open_mapping_rules=None, on_open_logs=None):
        self.icon = None
        self.on_exit_callback = on_exit_callback
        self.on_open_mapping_rules = on_open_mapping_rules
        self.on_open_logs = on_open_logs
        self.console_visible = True
        self.status_text = "Ready"
        self._icon_thread = None

        # State tracking for icon updates
        self._current_state = "normal"  # "normal", "recording", "transcribing"

        # Load icons
        self._icons = {
            "normal": load_icon("v2t.ico"),
            "recording": load_icon("v2t_recording.ico"),
            "transcribing": load_icon("v2t_transcribing.ico"),
        }

    def _create_menu(self):
        """Create the context menu (responds to both left and right click)."""
        return pystray.Menu(
            pystray.MenuItem(f"dbdude-v2t v{VERSION}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: f"Status: {self.status_text}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Show Configurator", self._show_configurator),
            pystray.MenuItem("Reload Mapping Files", self._reload_mappings),
            pystray.MenuItem("Restart", self._restart),
            pystray.MenuItem("Factory Restart", self._factory_restart),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: "Hide Console" if self.console_visible else "Show Console",
                self._toggle_console
            ),
            pystray.MenuItem("Open Mapping/Rules", self._open_mapping_rules),
            pystray.MenuItem("Open Logs Folder", self._open_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Show Help", self._show_help),
            pystray.MenuItem("Show Shortcuts", self._show_shortcuts),
            pystray.MenuItem("Help: System Tray", self._show_systray_help),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._exit_app),
        )

    def _toggle_console(self, icon=None, item=None):
        """Toggle console window visibility."""
        try:
            if self.console_visible:
                hide_console()
                self.console_visible = False
            else:
                show_console()
                self.console_visible = True
            # Update menu
            if self.icon:
                self.icon.update_menu()
        except Exception as e:
            log_error(f"ERROR: Failed to toggle console: {e}")

    def _show_configurator(self, icon=None, item=None):
        """Show the configurator window."""
        # Run in a separate thread to avoid blocking the systray
        def show_gui():
            try:
                current = get_current_settings()
                show_configurator_gui(
                    initial_model=current.get('model', 'base'),
                    initial_lang=current.get('language', 'en'),
                    initial_log=current.get('log', False),
                    initial_device=current.get('device'),
                    initial_debug=current.get('debug', False)
                )
            except Exception as e:
                log_error(f"ERROR: Configurator failed: {e}")
        threading.Thread(target=show_gui, daemon=True).start()

    def _reload_mappings(self, icon=None, item=None):
        """Reload mapping files without restarting."""
        global PUNCTUATION_MAP, PROGRAMMER_MAP, CUSTOM_MAP, CUSTOM_SYMBOL_MAP, NAME_MAP, WILDCARD_MAP
        PUNCTUATION_MAP.clear()
        PROGRAMMER_MAP.clear()
        CUSTOM_MAP.clear()
        CUSTOM_SYMBOL_MAP.clear()
        NAME_MAP.clear()
        WILDCARD_MAP.clear()
        load_custom_mappings()
        build_name_re()
        count = len(NAME_MAP)
        print(f"INFO: Mappings reloaded ({count} active)")

    def _restart(self, icon=None, item=None):
        """Restart with current settings."""
        current = get_current_settings()
        print("INFO: Restart requested with current settings", file=sys.stderr)
        request_restart(current)

    def _factory_restart(self, icon=None, item=None):
        """Delete settings and restart with factory defaults."""
        # Delete the settings file
        settings_path = get_settings_path()
        if settings_path.exists():
            try:
                settings_path.unlink()
                print(f"INFO: Deleted settings file: {settings_path}", file=sys.stderr)
            except Exception as e:
                print(f"ERROR: Could not delete settings file: {e}", file=sys.stderr)

        # Get factory default settings
        factory_defaults = {
            'model': 'base',
            'language': 'en',
            'log': False,
            'device': None,
            'debug': False
        }

        # Request restart with factory defaults
        print("INFO: Factory restart requested", file=sys.stderr)
        request_restart(factory_defaults)

    def _open_mapping_rules(self, icon=None, item=None):
        """Launch the Mapping/Rules editor."""
        if self.on_open_mapping_rules:
            self.on_open_mapping_rules()
        else:
            editor_path = get_mapping_rules_path()
            if editor_path.exists():
                try:
                    if is_nuitka_exe():
                        subprocess.Popen([str(editor_path)])
                    else:
                        subprocess.Popen([sys.executable, str(editor_path)])
                    print(f"INFO: Launched Mapping/Rules editor: {editor_path}", file=sys.stderr)
                except Exception as e:
                    print(f"ERROR: Failed to open Mapping/Rules editor: {e}", file=sys.stderr)
            else:
                print(f"ERROR: Mapping/Rules editor not found at: {editor_path}", file=sys.stderr)

    def _open_logs(self, icon=None, item=None):
        """Open the logs folder in Explorer."""
        try:
            if self.on_open_logs:
                self.on_open_logs()
            else:
                logs_dir = os.path.expanduser("~/logs")
                if os.path.exists(logs_dir):
                    if sys.platform == 'win32':
                        os.startfile(logs_dir)
                    else:
                        subprocess.Popen(['xdg-open', logs_dir])
                else:
                    print(f"INFO: Logs folder does not exist: {logs_dir}", file=sys.stderr)
        except Exception as e:
            log_error(f"ERROR: Failed to open logs folder: {e}")

    def _show_help(self, icon=None, item=None):
        """Open the help documentation in the default browser."""
        try:
            open_help_file("help.html")
        except Exception as e:
            log_error(f"ERROR: Failed to open help: {e}")

    def _show_shortcuts(self, icon=None, item=None):
        """Open the shortcuts quick reference in the default browser."""
        try:
            open_help_file("shortcuts.html")
        except Exception as e:
            log_error(f"ERROR: Failed to open shortcuts: {e}")

    def _show_systray_help(self, icon=None, item=None):
        """Open the system tray setup help in the default browser."""
        try:
            open_help_file("v2t-systray-help.html")
        except Exception as e:
            log_error(f"ERROR: Failed to open systray help: {e}")

    def _exit_app(self, icon=None, item=None):
        """Exit the application."""
        if self.on_exit_callback:
            self.on_exit_callback()
        self.stop()

    def start(self):
        """Start the systray icon in a background thread."""
        self.icon = pystray.Icon(
            "dbdude-v2t",
            self._icons["normal"],
            "dbdude-v2t - Ready",
            menu=self._create_menu()
        )

        # Run icon in background thread
        self._icon_thread = threading.Thread(target=self.icon.run, daemon=True)
        self._icon_thread.start()

    def stop(self):
        """Stop and remove the systray icon."""
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None

    def set_state(self, state, status_text=None):
        """Update icon state and tooltip.

        Args:
            state: One of "normal", "recording", "transcribing"
            status_text: Optional status text for menu
        """
        if state not in self._icons:
            state = "normal"

        self._current_state = state

        if status_text:
            self.status_text = status_text

        if self.icon:
            # Update icon
            self.icon.icon = self._icons[state]

            # Update tooltip
            tooltip_map = {
                "normal": "dbdude-v2t - Ready",
                "recording": "dbdude-v2t - Recording...",
                "transcribing": "dbdude-v2t - Transcribing...",
            }
            self.icon.title = tooltip_map.get(state, "dbdude-v2t")

    def set_recording(self):
        """Set icon to recording state."""
        self.set_state("recording", "Recording...")

    def set_transcribing(self):
        """Set icon to transcribing state."""
        self.set_state("transcribing", "Transcribing...")

    def set_ready(self):
        """Set icon to ready state."""
        self.set_state("normal", "Ready")


# Global systray manager instance
_systray_manager = None

# Global restart mechanism
_current_settings = {}
_restart_requested = False
_new_settings = None


def request_restart(new_settings):
    """Request engine restart with new settings."""
    global _restart_requested, _new_settings
    _restart_requested = True
    _new_settings = new_settings
    save_settings(new_settings)
    print("INFO: Restart requested with new settings", file=sys.stderr)


def clear_restart_request():
    """Clear the restart request flag."""
    global _restart_requested, _new_settings
    _restart_requested = False
    _new_settings = None


def is_restart_requested():
    """Check if restart has been requested."""
    return _restart_requested


def get_new_settings():
    """Get the new settings for restart."""
    return _new_settings


# Thread-safe systray state updates (avoid cross-thread pystray access)
_pending_systray_state = None
_systray_state_lock = threading.Lock()


def request_systray_state(state, status_text=None):
    """Thread-safe request to change systray state. Called from any thread."""
    global _pending_systray_state
    with _systray_state_lock:
        _pending_systray_state = (state, status_text)


def apply_pending_systray_state():
    """Apply pending systray state. Must be called from main loop only."""
    global _pending_systray_state
    with _systray_state_lock:
        pending = _pending_systray_state
        _pending_systray_state = None
    if pending:
        state, status_text = pending
        systray = get_systray_manager()
        if systray:
            systray.set_state(state, status_text)


def clear_pending_systray_state():
    """Clear any pending systray state to prevent race conditions."""
    global _pending_systray_state
    with _systray_state_lock:
        _pending_systray_state = None


def set_current_settings(settings):
    """Set the currently running settings."""
    global _current_settings
    _current_settings = settings.copy()


def get_current_settings():
    """Get the currently running settings."""
    return _current_settings.copy()


def get_systray_manager():
    """Get the global systray manager instance."""
    global _systray_manager
    return _systray_manager


def init_systray(on_exit_callback=None):
    """Initialize and start the systray manager."""
    global _systray_manager
    _systray_manager = SystrayManager(on_exit_callback=on_exit_callback)
    _systray_manager.start()
    return _systray_manager


def cleanup_systray():
    """Clean up systray on exit."""
    global _systray_manager
    if _systray_manager:
        _systray_manager.stop()
        _systray_manager = None


def get_configurator_path():
    """Get path to the configurator executable."""
    app_dir = get_app_dir()
    if is_nuitka_exe():
        return app_dir / "v2t-configurator.exe"
    else:
        return app_dir / "configurator_gui.py"


def show_configurator_gui(initial_model='base', initial_lang='en', initial_log=False, initial_device=None, initial_debug=False):
    """Launch the external configurator GUI."""
    configurator_path = get_configurator_path()

    if not configurator_path.exists():
        print(f"ERROR: Configurator not found at {configurator_path}", file=sys.stderr)
        messagebox.showerror("Error", f"Configurator not found:\n{configurator_path}")
        return None

    try:
        if is_nuitka_exe():
            subprocess.Popen(
                [str(configurator_path)],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
        else:
            subprocess.Popen([sys.executable, str(configurator_path)])
        print(f"INFO: Launched configurator: {configurator_path}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Failed to launch configurator: {e}", file=sys.stderr)
        messagebox.showerror("Error", f"Failed to launch configurator:\n{e}")

    return None


def show_settings_gui(initial_model='medium', initial_lang='en', initial_log=False, initial_device=None, initial_debug=False):
    """Show the settings GUI at startup (launches external configurator)."""
    # For startup, we launch configurator and wait for it
    # User must save settings and close configurator before engine starts
    configurator_path = get_configurator_path()

    if not configurator_path.exists():
        print(f"ERROR: Configurator not found at {configurator_path}", file=sys.stderr)
        return None

    try:
        if is_nuitka_exe():
            proc = subprocess.Popen([str(configurator_path)])
        else:
            proc = subprocess.Popen([sys.executable, str(configurator_path)])
        proc.wait()  # Wait for configurator to close
    except Exception as e:
        print(f"ERROR: Failed to launch configurator: {e}", file=sys.stderr)
        return None

    # Load settings that configurator saved
    return load_settings()


# --- Main dbdude-v2t Engine ---
def run_voice2text(model_name, language, enable_logging, device_name, debug_mode=False, push_to_talk_keys=None):
    """Run the dbdude-v2t engine with given settings."""
    global _DEBUG_MODE
    _DEBUG_MODE = debug_mode

    # Default push_to_talk_keys if not provided (backwards compatibility)
    if push_to_talk_keys is None:
        push_to_talk_keys = {
            'left_alt_shift': True,
            'caps_lock': True,
            'right_alt': False,
            'left_ctrl_shift': False
        }

    # Track current settings for the configurator
    set_current_settings({
        'model': model_name,
        'language': language,
        'log': enable_logging,
        'device': device_name,
        'debug': debug_mode,
        'push_to_talk_keys': push_to_talk_keys
    })

    # Setup logging directory
    logs_dir = os.path.expanduser("~/logs")
    if enable_logging and not os.path.exists(logs_dir):
        os.makedirs(logs_dir, exist_ok=True)

    # Load custom mappings and rules
    load_custom_mappings()
    load_rules()

    # Compile regex after mappings are loaded
    build_name_re()

    # AutoHotkey path
    type_text_exe = os.path.realpath(os.path.join(str(get_app_dir()), "type_text.exe"))

    # Find audio device
    audio_device = find_device_by_name(device_name)

    # Detect GPU availability
    if ctranslate2.get_cuda_device_count() > 0:
        device = "cuda"
        compute_type = "float16"
        print("INFO: NVIDIA GPU detected, using CUDA acceleration", file=sys.stderr)
    else:
        device = "cpu"
        compute_type = "int8"
        print("INFO: No NVIDIA GPU detected, using CPU mode (slower)", file=sys.stderr)

    # Load model (with fallback to DEFAULT_MODEL if requested model fails)
    def try_load_model(name):
        """Attempt to load a Whisper model by name. Returns model or None."""
        local_path = os.path.realpath(os.path.join(str(get_app_dir()), "models", f"faster-whisper-{name}"))
        try:
            if os.path.exists(local_path):
                print(f"INFO: Using bundled model at {local_path}", file=sys.stderr)
                return WhisperModel(local_path, device=device, compute_type=compute_type)
            else:
                print(f"INFO: Bundled model not found, downloading {name} from HuggingFace...", file=sys.stderr)
                return WhisperModel(name, device=device, compute_type=compute_type)
        except Exception as e:
            print(f"ERROR: Could not load model '{name}': {e}", file=sys.stderr)
            return None

    print(f"INFO: Loading Whisper Model ({model_name})...", file=sys.stderr)
    model = try_load_model(model_name)

    # Fallback to DEFAULT_MODEL if requested model failed
    if model is None and model_name != DEFAULT_MODEL:
        print(f"WARNING: Falling back to default model '{DEFAULT_MODEL}'...", file=sys.stderr)
        model = try_load_model(DEFAULT_MODEL)
        if model is not None:
            model_name = DEFAULT_MODEL  # Update for display purposes

    if model is None:
        messagebox.showerror("Error", f"Could not load Whisper Model.\nTried: {model_name}, {DEFAULT_MODEL}")
        return

    print(f"INFO: Model Loaded. (quantization: {compute_type})", file=sys.stderr)

    # Verify AutoHotkey setup
    if not os.path.exists(type_text_exe):
        print(f"WARNING: type_text.exe not found at {type_text_exe}", file=sys.stderr)
        print("         Place type_text.exe in the same directory as this script", file=sys.stderr)

    # Thread-safe audio architecture
    recording_event = threading.Event()
    shutdown_event = threading.Event()
    audio_queue = queue.Queue()
    transcription_queue = queue.Queue()  # Completed recordings waiting to be transcribed

    # Debug counter for audio callback (only used in debug mode)
    callback_debug_counter = [0]  # Use list to allow modification in nested function

    def audio_callback(indata, frames, time_info, status):
        if status:
            print(f"Audio Status: {status}", file=sys.stderr)
        if recording_event.is_set():
            audio_queue.put(indata.copy())
            if debug_mode:
                callback_debug_counter[0] += 1
                # Print every 100 chunks to avoid flooding console
                if callback_debug_counter[0] % 100 == 0:
                    print(f"DEBUG: audio_callback queued chunk #{callback_debug_counter[0]}, queue size ~{audio_queue.qsize()}")

    def audio_stream_worker():
        try:
            with sd.InputStream(samplerate=SAMPLERATE,
                                channels=CHANNELS,
                                dtype=AUDIO_DTYPE,
                                blocksize=AUDIO_BLOCKSIZE,
                                device=audio_device,
                                callback=audio_callback):
                print(">> Audio Stream Active. Ready to record.")
                while not shutdown_event.is_set():
                    time.sleep(0.1)
        except Exception as e:
            print(f"CRITICAL AUDIO FAILURE in worker thread: {e}", file=sys.stderr)

    def drain_queue(context=""):
        data = []
        while True:
            try:
                data.append(audio_queue.get_nowait())
            except queue.Empty:
                break
        if debug_mode and data:
            duration = len(data) * AUDIO_BLOCKSIZE / SAMPLERATE
            print(f"DEBUG [{context}]: drain_queue() pulled {len(data)} chunks ({duration:.2f}s of audio)")
        elif debug_mode:
            print(f"DEBUG [{context}]: drain_queue() - queue was empty")
        return data

    def process_and_output(buffer_list):
        if not buffer_list:
            print("INFO: No audio captured; skipping transcription.")
            return

        try:
            audio_np = np.concatenate(buffer_list, axis=0).flatten()
        except ValueError as e:
            print(f"ERROR: Audio buffer malformed: {e}")
            return

        duration = len(audio_np) / SAMPLERATE
        if duration < MIN_AUDIO_DURATION_S:
            return

        rms = np.sqrt(np.mean(np.square(audio_np)))
        peak = np.max(np.abs(audio_np))

        if rms < MIN_AUDIO_RMS and peak < MIN_AUDIO_AMPLITUDE:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] INFO: Low energy (rms={rms:.4f}, peak={peak:.4f}); skipping transcription.")
            return

        try:
            transcribe_start = time.time()
            segments, info = model.transcribe(audio_np, beam_size=WHISPER_BEAM_SIZE, language=language, task='transcribe')
            raw = ' '.join(seg.text for seg in segments)  # Transcription happens here (generator)
            transcribe_elapsed = time.time() - transcribe_start
            print(f"[{datetime.now().strftime('%H:%M:%S')}] INFO: {duration:.2f}s of audio transcribed in {transcribe_elapsed:.3f}s")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Transcribed: {raw.strip()}")
            final = process_and_validate_text(raw)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Mapped to:   {final}")

            if final:
                type_with_ahk(final + ' ', type_text_exe)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] INFO: Text output complete")
                if enable_logging:
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    with open(os.path.join(logs_dir, f"snippet_{ts}_raw.txt"), 'w', encoding='utf-8') as f:
                        f.write(raw + '\n')
                    with open(os.path.join(logs_dir, f"snippet_{ts}.txt"), 'w', encoding='utf-8') as f:
                        f.write(final + '\n')
        except Exception as e:
            print(f"ERROR during transcription/write: {e}")

    def transcription_worker():
        """Worker thread that processes transcription jobs from the queue."""
        while not shutdown_event.is_set():
            try:
                # Wait for work with timeout so we can check shutdown
                audio_data = transcription_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                request_systray_state("transcribing", "Transcribing...")
                process_and_output(audio_data)
            except Exception as e:
                print(f"ERROR in transcription worker: {e}", file=sys.stderr)
            finally:
                transcription_queue.task_done()
                # Only set ready if queue is empty
                if transcription_queue.empty():
                    request_systray_state("normal", "Ready")

    # Get device name for display
    if audio_device is not None:
        display_device_name = sd.query_devices(audio_device)['name']
    else:
        display_device_name = sd.query_devices(sd.default.device[0])['name'] + " (default)"

    # Get executable path for display
    if getattr(sys, 'frozen', False) or "__compiled__" in globals():
        # Nuitka: sys.executable points to python.exe, use sys.argv[0] for actual exe
        exe_path = os.path.realpath(sys.argv[0])
    else:
        exe_path = os.path.realpath(__file__)

    # Build enabled hotkeys message for startup display
    enabled_keys_display = []
    if push_to_talk_keys.get('left_alt_shift', True):
        enabled_keys_display.append("Left Alt+Shift")
    if push_to_talk_keys.get('caps_lock', True):
        enabled_keys_display.append("Caps Lock")
    if push_to_talk_keys.get('right_alt', False):
        enabled_keys_display.append("Right Alt")
    if push_to_talk_keys.get('left_ctrl_shift', False):
        enabled_keys_display.append("Left Ctrl+Shift")
    ptt_keys_display = " or ".join(enabled_keys_display) if enabled_keys_display else "Left Alt+Shift"

    print(f">> dbdude-v2t v{VERSION}")
    print(f">> Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f">> Hold [{ptt_keys_display}] to RECORD; release to STOP & TRANSCRIBE.")
    print(">> Press Ctrl+Shift+Q to exit. Press Ctrl+Alt+R to toggle Hands-Free recording.")
    print(f">> Running: {exe_path}")
    print(f">> Using type_text.exe: {type_text_exe}")
    print(f">> Model: {model_name} | Language: {language}")
    print(f">> Microphone: {display_device_name}")
    print(f">> Logging: {'ENABLED (~/logs)' if enable_logging else 'DISABLED (use --log to enable)'}")
    if debug_mode:
        print(">> DEBUG MODE: ENABLED - verbose audio buffer diagnostics active")

    # Initialize systray
    systray = init_systray(on_exit_callback=lambda: shutdown_event.set())

    # Hide console by default (user can show via systray menu)
    hide_console()
    systray.console_visible = False

    # Register cleanup handlers
    def cleanup():
        cleanup_systray()

    atexit.register(cleanup)

    # Handle SIGINT/SIGTERM for graceful shutdown
    def signal_handler(signum, frame):
        print("\nReceived shutdown signal.")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    audio_thread = threading.Thread(target=audio_stream_worker, daemon=True)
    audio_thread.start()
    time.sleep(0.5)

    transcription_thread = threading.Thread(target=transcription_worker, daemon=True)
    transcription_thread.start()

    if not audio_thread.is_alive():
        print("ERROR: Audio thread failed to start. Exiting.")
        cleanup_systray()
        return

    # --- HYBRID KEYBOARD HANDLING (v2.3.0 fix for lockup issue) ---
    # Callbacks ONLY update state flags - no blocking operations
    # Main loop reads state and does all actual work

    # Thread-safe state using a lock
    state_lock = threading.Lock()
    state = {
        'left_alt_held': False,
        'right_alt_held': False,
        'shift_held': False,
        'caps_lock_held': False,
        'left_ctrl_held': False,
        'toggle_requested': False
    }

    # Callbacks do NOTHING except flip flags - no sleeps, no queue ops, no prints
    def on_left_alt_press(event):
        with state_lock:
            state['left_alt_held'] = True

    def on_left_alt_release(event):
        with state_lock:
            state['left_alt_held'] = False

    def on_right_alt_press(event):
        with state_lock:
            state['right_alt_held'] = True

    def on_right_alt_release(event):
        with state_lock:
            state['right_alt_held'] = False

    def on_shift_press(event):
        with state_lock:
            state['shift_held'] = True

    def on_shift_release(event):
        with state_lock:
            state['shift_held'] = False

    def on_caps_lock_press(event):
        with state_lock:
            state['caps_lock_held'] = True

    def on_caps_lock_release(event):
        with state_lock:
            state['caps_lock_held'] = False

    def on_left_ctrl_press(event):
        with state_lock:
            state['left_ctrl_held'] = True

    def on_left_ctrl_release(event):
        with state_lock:
            state['left_ctrl_held'] = False

    def on_toggle_continuous():
        with state_lock:
            state['toggle_requested'] = True

    def on_exit_hotkey():
        shutdown_event.set()

    # Register callbacks based on push_to_talk_keys settings
    # Always register shift since it's used by multiple combos
    keyboard.on_press_key('shift', on_shift_press, suppress=False)
    keyboard.on_release_key('shift', on_shift_release, suppress=False)

    # Left Alt + Shift combo
    if push_to_talk_keys.get('left_alt_shift', True):
        keyboard.on_press_key('left alt', on_left_alt_press, suppress=False)
        keyboard.on_release_key('left alt', on_left_alt_release, suppress=False)

    # Caps Lock (Shift Lock)
    if push_to_talk_keys.get('caps_lock', True):
        keyboard.on_press_key('caps lock', on_caps_lock_press, suppress=True)  # suppress=True prevents caps toggle
        keyboard.on_release_key('caps lock', on_caps_lock_release, suppress=True)

    # Right Alt (solo or with shift)
    if push_to_talk_keys.get('right_alt', False) or push_to_talk_keys.get('right_alt_shift', False):
        keyboard.on_press_key('right alt', on_right_alt_press, suppress=False)
        keyboard.on_release_key('right alt', on_right_alt_release, suppress=False)

    # Left Ctrl + Shift combo
    if push_to_talk_keys.get('left_ctrl_shift', False):
        keyboard.on_press_key('left ctrl', on_left_ctrl_press, suppress=False)
        keyboard.on_release_key('left ctrl', on_left_ctrl_release, suppress=False)

    keyboard.add_hotkey('ctrl+alt+r', on_toggle_continuous, suppress=False)
    keyboard.add_hotkey('ctrl+shift+q', on_exit_hotkey, suppress=False)

    # Main loop state
    recording = False
    continuous_mode = False

    # Main loop does all actual work based on state flags
    try:
        while not shutdown_event.is_set():
            if not audio_thread.is_alive():
                print("CRITICAL: Audio thread died unexpectedly. Exiting.")
                break

            # Read state snapshot
            with state_lock:
                left_alt_held = state['left_alt_held']
                right_alt_held = state['right_alt_held']
                shift_held = state['shift_held']
                caps_held = state['caps_lock_held']
                left_ctrl_held = state['left_ctrl_held']
                toggle_req = state['toggle_requested']
                state['toggle_requested'] = False

            # Build record_key_held based on enabled push-to-talk keys
            record_key_held = False
            if push_to_talk_keys.get('left_alt_shift', True) and left_alt_held and shift_held:
                record_key_held = True
            if push_to_talk_keys.get('caps_lock', True) and caps_held:
                record_key_held = True
            if push_to_talk_keys.get('right_alt', False) and right_alt_held:
                record_key_held = True
            if push_to_talk_keys.get('left_ctrl_shift', False) and left_ctrl_held and shift_held:
                record_key_held = True

            # Handle Hands-Free recording toggle request
            if toggle_req:
                continuous_mode = not continuous_mode
                if continuous_mode:
                    print("INFO: Hands-Free recording ON")
                    drain_queue("continuous_on_clear")
                    recording_event.set()
                    clear_pending_systray_state()
                    systray.set_recording()
                    if debug_mode:
                        print("DEBUG: recording_event.set() called for Hands-Free recording")
                else:
                    print("INFO: Hands-Free recording OFF")
                    recording_event.clear()
                    if debug_mode:
                        print("DEBUG: recording_event.clear() called for Hands-Free recording")
                    time.sleep(0.05)
                    captured_audio = drain_queue("continuous_off_capture")
                    if captured_audio:
                        transcription_queue.put(captured_audio)

            # Handle hold-to-record: Alt+Shift OR Caps Lock (only if not in Hands-Free mode)
            if not continuous_mode:
                if record_key_held and not recording:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Started recording...")
                    drain_queue("recording_start_clear")
                    recording_event.set()
                    clear_pending_systray_state()
                    systray.set_recording()
                    if debug_mode:
                        print("DEBUG: recording_event.set() called - now recording")
                    recording = True
                elif not record_key_held and recording:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Stopping & queuing for transcription...")
                    recording_event.clear()
                    if debug_mode:
                        print("DEBUG: recording_event.clear() called - stopped recording")
                    recording = False
                    time.sleep(0.05)
                    captured_audio = drain_queue("recording_stop_capture")
                    if captured_audio:
                        transcription_queue.put(captured_audio)

            # Check if restart was requested from configurator
            if is_restart_requested():
                print("INFO: Restart requested, shutting down engine...", file=sys.stderr)
                shutdown_event.set()
                break

            # Apply any pending systray state changes (thread-safe)
            apply_pending_systray_state()

            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        shutdown_event.set()
        keyboard.unhook_all()
        # Wait for pending transcriptions to complete
        if not transcription_queue.empty():
            pending = transcription_queue.qsize()
            print(f"INFO: Waiting for {pending} pending transcription(s)...")
            transcription_queue.join()
        cleanup_systray()
        if audio_thread.is_alive():
            audio_thread.join(timeout=1.0)
        print(f">> Session ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Done.")


# --- Main Entry Point ---
def main():
    try:
        log_error("INFO: dbdude-v2t starting...")

        # Initialize Tk root before anything else (must happen before threads start)
        # This allows all dialogs to use Toplevel without Tk initialization issues in compiled code
        log_error("INFO: Calling init_tk_root()...")
        init_tk_root()
        log_error("INFO: init_tk_root() completed")

        # Hide console immediately on startup (user can show via systray menu later)
        hide_console()
    except Exception as e:
        import traceback
        log_error(f"FATAL: Startup failed: {e}")
        log_error(traceback.format_exc())
        raise

    # Parse command-line arguments (can override saved settings)
    parser = argparse.ArgumentParser(description='Voice-to-text transcription with hotkeys')
    parser.add_argument('--log', action='store_true', help='Enable logging transcriptions to ~/logs')
    parser.add_argument('--model', type=str, default=None, help='Whisper model size (overrides saved setting)')
    parser.add_argument('--language', choices=VALID_LANGUAGE_CODES, default=None, help='Transcription language (overrides saved setting)')
    parser.add_argument('--device', type=str, default=None, help='Audio input device name (overrides saved setting)')
    parser.add_argument('--configurator', action='store_true', help='Show configurator at startup (legacy mode)')
    args = parser.parse_args()

    # Load saved settings (or defaults if none saved)
    settings = load_saved_settings()

    # Command-line args override saved settings
    if args.model:
        settings['model'] = args.model
    if args.language:
        settings['language'] = args.language
    if args.device:
        settings['device'] = args.device
    if args.log:
        settings['log'] = True

    # Legacy mode: show configurator at startup if --configurator flag is provided
    if args.configurator:
        gui_settings = show_settings_gui(
            initial_model=settings['model'],
            initial_lang=settings['language'],
            initial_log=settings['log'],
            initial_device=settings['device'],
            initial_debug=settings.get('debug', False)
        )
        if gui_settings is None:
            # User cancelled
            sys.exit(0)
        settings = gui_settings
        save_settings(settings)

    # Main loop - supports restart
    while True:
        clear_restart_request()

        # Run voice2text with current settings
        run_voice2text(
            model_name=settings['model'],
            language=settings['language'],
            enable_logging=settings['log'],
            device_name=settings['device'],
            debug_mode=settings.get('debug', False),
            push_to_talk_keys=settings.get('push_to_talk_keys')
        )

        # Check if restart was requested
        if is_restart_requested():
            settings = get_new_settings()
            print("INFO: Restarting with new settings...", file=sys.stderr)
            continue
        else:
            # Normal exit
            break


if __name__ == '__main__':
    main()
