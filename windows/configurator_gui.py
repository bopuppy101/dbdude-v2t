#!/usr/bin/env python3
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).
"""dbdude-v2t Configurator GUI for Ubuntu - PySide6 version."""

import sys
import os
import subprocess
import signal
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QCheckBox, QRadioButton, QPushButton,
    QGroupBox, QButtonGroup, QScrollArea, QWidget, QStyleFactory,
    QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPalette, QColor
import sounddevice as sd


def get_app_dir():
    """Get the directory containing the app (works for both Python and Nuitka exe)."""
    # For Nuitka onefile: use sys.argv[0] which has the original exe path
    if sys.argv and sys.argv[0]:
        argv0_path = Path(sys.argv[0]).resolve().parent
        if (argv0_path / 'models.json').exists():
            return argv0_path
    # Fallback for Nuitka standalone or PyInstaller
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    # For regular Python
    return Path(__file__).parent


def get_user_data_dir():
    """Get user data directory (~/.dbdude-v2t)."""
    data_dir = Path.home() / ".dbdude-v2t"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def load_settings():
    """Load settings from file."""
    settings_file = get_user_data_dir() / "settings.json"
    defaults = {
        "model": "base",
        "language": "en",
        "log": False,
        "debug": False,
        "device": None,
        "push_to_talk_keys": {
            "left_alt_shift": True,
            "right_alt": False,
            "left_ctrl_shift": False
        }
    }
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                defaults.update(saved)
        except Exception as e:
            print(f"Error loading settings: {e}")
    return defaults


def save_settings(settings):
    """Save settings to file."""
    settings_file = get_user_data_dir() / "settings.json"
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False


def create_app_palette():
    """Create a refined color palette for the application."""
    palette = QPalette()

    # Window and base colors
    palette.setColor(QPalette.Window, QColor("#f0f0f0"))
    palette.setColor(QPalette.WindowText, QColor("#1a1a1a"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase, QColor("#f7f7f7"))
    palette.setColor(QPalette.Text, QColor("#1a1a1a"))

    # Button colors
    palette.setColor(QPalette.Button, QColor("#e0e0e0"))
    palette.setColor(QPalette.ButtonText, QColor("#1a1a1a"))

    # Highlight colors (selection)
    palette.setColor(QPalette.Highlight, QColor("#0078d4"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))

    # Other
    palette.setColor(QPalette.ToolTipBase, QColor("#ffffdc"))
    palette.setColor(QPalette.ToolTipText, QColor("#1a1a1a"))
    palette.setColor(QPalette.PlaceholderText, QColor("#808080"))

    return palette


STYLESHEET = """
QDialog {
    background-color: #f0f0f0;
}

QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #c0c0c0;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 10px;
    background-color: #fafafa;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #404040;
}

QLabel {
    font-size: 13px;
    color: #303030;
}

QComboBox {
    font-size: 13px;
    padding: 6px 10px;
    min-width: 200px;
}

QCheckBox, QRadioButton {
    font-size: 13px;
    color: #303030;
    spacing: 8px;
}

QPushButton {
    font-size: 13px;
    font-weight: 500;
    padding: 8px 20px;
    min-width: 90px;
}

QScrollArea {
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    background-color: white;
}

QScrollBar:vertical {
    width: 12px;
    background: #f0f0f0;
}

QScrollBar::handle:vertical {
    background: #c0c0c0;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #a0a0a0;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""


# Available models for faster-whisper
def load_valid_models():
    """Load valid models from models.json file in app directory."""
    path = get_app_dir() / "models.json"
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                models = data.get("models", [])
                if models:
                    print(f"INFO: Loaded {len(models)} models from {path}")
                    return models
        except Exception as e:
            print(f"WARNING: Could not load models from {path}: {e}")
    # Fallback if no file found
    print("INFO: No models.json found, using built-in defaults")
    return ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']

VALID_MODELS = load_valid_models()

# Available languages (subset of most common)
VALID_LANGUAGES = [
    ("English", "en"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Italian", "it"),
    ("Portuguese", "pt"),
    ("Dutch", "nl"),
    ("Russian", "ru"),
    ("Chinese", "zh"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
]


def get_input_devices():
    """Get list of available input devices."""
    devices = []
    try:
        all_devices = sd.query_devices()
        default_input = sd.query_devices(kind='input')
        default_name = default_input['name'] if default_input else None

        for i, dev in enumerate(all_devices):
            if dev['max_input_channels'] > 0:
                devices.append({
                    'index': i,
                    'name': dev['name'],
                    'is_default': dev['name'] == default_name
                })
    except Exception as e:
        print(f"Error getting input devices: {e}")
    return devices


def find_v2t_process():
    """Find the running dbdude-v2t process."""
    pids = []
    our_pid = os.getpid()

    if sys.platform == 'win32':
        try:
            # Use tasklist to find dbdude-v2t.exe
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq dbdude-v2t.exe', '/FO', 'CSV', '/NH'],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in result.stdout.strip().split('\n'):
                if line and 'dbdude-v2t.exe' in line.lower():
                    parts = line.replace('"', '').split(',')
                    if len(parts) >= 2:
                        try:
                            pid = int(parts[1])
                            if pid != our_pid:
                                pids.append(pid)
                        except ValueError:
                            pass
        except Exception as e:
            print(f"Error finding v2t process: {e}")
    else:
        # Linux/macOS: use pgrep
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'dbdude-v2t'],
                capture_output=True, text=True
            )
            if result.stdout.strip():
                for pid_str in result.stdout.strip().split('\n'):
                    if pid_str:
                        pid = int(pid_str)
                        if pid != our_pid:
                            pids.append(pid)
        except Exception as e:
            print(f"Error finding v2t process: {e}")

    return pids


def restart_v2t():
    """Restart the dbdude-v2t application with graceful shutdown."""
    import time

    # Find and stop existing process
    pids = find_v2t_process()

    if sys.platform == 'win32':
        # Windows: use taskkill
        for pid in pids:
            try:
                subprocess.run(
                    ['taskkill', '/PID', str(pid)],
                    capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
                print(f"Sent terminate to dbdude-v2t (PID {pid})")
            except Exception as e:
                print(f"Error terminating process {pid}: {e}")

        # Wait for graceful shutdown
        if pids:
            for _ in range(30):
                time.sleep(0.1)
                if not find_v2t_process():
                    print("dbdude-v2t shut down gracefully")
                    break
            else:
                # Force kill if still running
                for pid in find_v2t_process():
                    try:
                        subprocess.run(
                            ['taskkill', '/F', '/PID', str(pid)],
                            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        print(f"Force killed dbdude-v2t (PID {pid})")
                    except:
                        pass
    else:
        # Linux/macOS: use signals
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Sent SIGTERM to dbdude-v2t (PID {pid})")
            except ProcessLookupError:
                pass
            except Exception as e:
                print(f"Error signaling process {pid}: {e}")

        if pids:
            for _ in range(30):
                time.sleep(0.1)
                if not find_v2t_process():
                    print("dbdude-v2t shut down gracefully")
                    break
            else:
                for pid in find_v2t_process():
                    try:
                        os.kill(pid, signal.SIGKILL)
                        print(f"Force killed dbdude-v2t (PID {pid})")
                    except:
                        pass

    # Brief pause before starting new instance
    time.sleep(0.2)

    # Find and start dbdude-v2t
    v2t_dir = Path(__file__).parent

    if sys.platform == 'win32':
        # Windows: look for dbdude-v2t.exe
        v2t_exe = v2t_dir / "dbdude-v2t.exe"
        if not v2t_exe.exists():
            # Try parent directory (if running from source)
            v2t_exe = v2t_dir.parent.parent / "dist" / "windows" / "dbdude-v2t.dist" / "dbdude-v2t.exe"

        if v2t_exe.exists():
            subprocess.Popen(
                [str(v2t_exe)],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(v2t_exe.parent)
            )
            print(f"Started new dbdude-v2t instance")
            return True
        else:
            print(f"dbdude-v2t not found")
            return False
    else:
        # Linux/macOS: use run script or direct execution
        run_script = v2t_dir / "run-dbdude-v2t.bash"
        if run_script.exists():
            subprocess.Popen(
                ['bash', str(run_script)],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(v2t_dir)
            )
            print("Started new dbdude-v2t instance via run script")
            return True
        else:
            v2t_path = v2t_dir / "dbdude-v2t.py"
            if v2t_path.exists():
                subprocess.Popen(
                    ['sudo', sys.executable, str(v2t_path)],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("Started new dbdude-v2t instance")
                return True
            else:
                print(f"dbdude-v2t not found at {v2t_path}")
                return False


class ConfiguratorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = load_settings()
        self.input_devices = get_input_devices()
        self._loading = True

        self.setWindowTitle("dbdude-v2t - Configurator")
        self.setFixedSize(580, 780)
        self.setStyleSheet(STYLESHEET)

        self.setup_ui()
        self.center_on_screen()
        self._loading = False

    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("dbdude-v2t - Configurator")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a1a1a;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Settings group with file path
        settings_file = get_user_data_dir() / "settings.json"
        settings_group = QGroupBox(f"Settings    {settings_file}")
        settings_layout = QGridLayout(settings_group)
        settings_layout.setSpacing(12)
        settings_layout.setContentsMargins(16, 20, 16, 16)

        # Model selection
        settings_layout.addWidget(QLabel("Model:"), 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItems(VALID_MODELS)
        self.model_combo.setCurrentText(self.settings.get("model", "base"))
        self.model_combo.currentTextChanged.connect(self._on_setting_changed)
        settings_layout.addWidget(self.model_combo, 0, 1)

        # Language selection
        settings_layout.addWidget(QLabel("Language:"), 1, 0)
        self.lang_combo = QComboBox()
        lang_names = [name for name, code in VALID_LANGUAGES]
        self.lang_combo.addItems(lang_names)

        initial_lang = self.settings.get("language", "en")
        initial_lang_name = "English"
        for name, code in VALID_LANGUAGES:
            if code == initial_lang:
                initial_lang_name = name
                break
        self.lang_combo.setCurrentText(initial_lang_name)
        self.lang_combo.currentTextChanged.connect(self._on_setting_changed)
        settings_layout.addWidget(self.lang_combo, 1, 1)

        # Logging checkbox
        self.log_checkbox = QCheckBox("Enable logging to ~/logs")
        self.log_checkbox.setChecked(self.settings.get("log", False))
        self.log_checkbox.stateChanged.connect(self._on_setting_changed)
        settings_layout.addWidget(self.log_checkbox, 2, 0, 1, 2)

        # Debug checkbox
        self.debug_checkbox = QCheckBox("Show debug statements")
        self.debug_checkbox.setChecked(self.settings.get("debug", False))
        self.debug_checkbox.stateChanged.connect(self._on_setting_changed)
        settings_layout.addWidget(self.debug_checkbox, 3, 0, 1, 2)

        layout.addWidget(settings_group)

        # Microphone group
        mic_group = QGroupBox("Microphone")
        mic_layout = QVBoxLayout(mic_group)
        mic_layout.setContentsMargins(16, 20, 16, 16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(160)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(6)
        scroll_layout.setContentsMargins(8, 20, 8, 8)

        self.device_group = QButtonGroup(self)
        self.device_group.buttonClicked.connect(self._on_setting_changed)

        saved_device = self.settings.get("device")
        default_idx = None
        for dev in self.input_devices:
            if saved_device and saved_device.lower() in dev['name'].lower():
                default_idx = dev['index']
                break
            if dev['is_default'] and default_idx is None:
                default_idx = dev['index']

        for dev in self.input_devices:
            label = dev['name']
            if dev['is_default']:
                label += " (default)"

            radio = QRadioButton(label)
            radio.setProperty("device_index", dev['index'])
            radio.setProperty("is_default", dev['is_default'])

            if dev['index'] == default_idx:
                radio.setChecked(True)

            self.device_group.addButton(radio)
            scroll_layout.addWidget(radio)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        mic_layout.addWidget(scroll)

        layout.addWidget(mic_group)

        # Push to Talk Keys group
        ptt_group = QGroupBox("Push to Talk Keys")
        ptt_layout = QVBoxLayout(ptt_group)
        ptt_layout.setContentsMargins(16, 20, 16, 16)
        ptt_layout.setSpacing(8)

        ptt_note = QLabel("Select which keys can be used for push-to-talk recording:")
        ptt_note.setStyleSheet("font-size: 12px; color: #606060; font-style: italic;")
        ptt_note.setWordWrap(True)
        ptt_layout.addWidget(ptt_note)

        # Get current push_to_talk_keys settings
        ptt_keys = self.settings.get("push_to_talk_keys", {
            "left_alt_shift": True,
            "right_alt": False,
            "left_ctrl_shift": False
        })

        self.ptt_left_alt_shift = QCheckBox("Left Alt + Shift (recommended)")
        self.ptt_left_alt_shift.setChecked(ptt_keys.get("left_alt_shift", True))
        self.ptt_left_alt_shift.stateChanged.connect(self._on_setting_changed)
        ptt_layout.addWidget(self.ptt_left_alt_shift)

        self.ptt_right_alt = QCheckBox("Right Alt")
        self.ptt_right_alt.setChecked(ptt_keys.get("right_alt", False))
        self.ptt_right_alt.setToolTip("Note: On European keyboards, Right Alt is AltGr and may conflict with special characters")
        self.ptt_right_alt.stateChanged.connect(self._on_setting_changed)
        ptt_layout.addWidget(self.ptt_right_alt)

        self.ptt_left_ctrl_shift = QCheckBox("Left Ctrl + Shift")
        self.ptt_left_ctrl_shift.setChecked(ptt_keys.get("left_ctrl_shift", False))
        self.ptt_left_ctrl_shift.stateChanged.connect(self._on_setting_changed)
        ptt_layout.addWidget(self.ptt_left_ctrl_shift)

        ptt_warning = QLabel("At least one option must be selected.")
        ptt_warning.setStyleSheet("font-size: 11px; color: #808080;")
        ptt_layout.addWidget(ptt_warning)

        layout.addWidget(ptt_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        RESTART_STYLE = """
            QPushButton {
                background-color: #28a745;
                color: #ffffff;
                border: 1px solid #1e7e34;
                border-radius: 4px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #2fb553; }
            QPushButton:pressed { background-color: #1e7e34; }
        """

        restart_btn = QPushButton("  Restart dbdude-v2t  ")
        restart_btn.setStyleSheet(RESTART_STYLE)
        restart_btn.clicked.connect(self.on_restart)
        btn_layout.addWidget(restart_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def get_language_code(self):
        """Convert language name to code."""
        lang_name = self.lang_combo.currentText()
        for name, code in VALID_LANGUAGES:
            if name == lang_name:
                return code
        return "en"

    def get_selected_device_name(self):
        """Get selected device name, or None if default is selected."""
        checked = self.device_group.checkedButton()
        if checked:
            if checked.property("is_default"):
                return None
            for dev in self.input_devices:
                if dev['index'] == checked.property("device_index"):
                    return dev['name']
        return None

    def _on_setting_changed(self, *args):
        """Auto-save when any setting changes."""
        if self._loading:
            return

        old_device = self.settings.get('device')
        new_device = self.get_selected_device_name()

        # Build push_to_talk_keys dict
        ptt_keys = {
            "left_alt_shift": self.ptt_left_alt_shift.isChecked(),
            "right_alt": self.ptt_right_alt.isChecked(),
            "left_ctrl_shift": self.ptt_left_ctrl_shift.isChecked(),
        }

        # Validate at least one PTT key is selected
        if not any(ptt_keys.values()):
            QMessageBox.warning(self, "Invalid Selection",
                "At least one push-to-talk key must be selected.\n\n"
                "Reverting to Left Alt + Shift.")
            self.ptt_left_alt_shift.setChecked(True)
            ptt_keys["left_alt_shift"] = True

        self.settings = {
            'model': self.model_combo.currentText(),
            'language': self.get_language_code(),
            'log': self.log_checkbox.isChecked(),
            'debug': self.debug_checkbox.isChecked(),
            'device': new_device,
            'push_to_talk_keys': ptt_keys,
        }
        save_settings(self.settings)

        # Show restart message if microphone changed
        if old_device != new_device:
            QMessageBox.information(self, "Restart Required",
                "Microphone change requires a restart.\n\n"
                "Please restart dbdude-v2t for the new microphone to take effect.")

    def on_restart(self):
        """Restart dbdude-v2t application."""
        self.setCursor(Qt.WaitCursor)
        self.setEnabled(False)

        success = restart_v2t()

        self.unsetCursor()
        self.setEnabled(True)

        if success:
            QTimer.singleShot(500, lambda: QMessageBox.information(
                self, "Restart Complete",
                "dbdude-v2t has been restarted.\n\n"
                "New settings are now active."
            ))
        else:
            QMessageBox.warning(self, "Restart Failed",
                "Could not restart dbdude-v2t.\nPlease restart manually.")


def show_configurator():
    """Show the configurator GUI."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setStyle(QStyleFactory.create("Fusion"))
    app.setPalette(create_app_palette())

    dialog = ConfiguratorDialog()
    dialog.exec()


if __name__ == "__main__":
    show_configurator()
