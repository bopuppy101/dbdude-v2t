#!/usr/bin/env python3
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.
"""dbdude-v2t Configurator GUI for macOS - PySide6 version."""

import sys
import subprocess
import signal
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QCheckBox, QRadioButton, QPushButton,
    QGroupBox, QButtonGroup, QScrollArea, QWidget, QStyleFactory
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
import sounddevice as sd


def get_user_data_dir():
    """Get macOS user data directory."""
    data_dir = Path.home() / "Library" / "Application Support" / "dbdude-v2t"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def load_settings():
    """Load settings from file."""
    settings_file = get_user_data_dir() / "settings.json"
    defaults = {
        "model": "small",
        "language": "en",
        "log": False,
        "device": None
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


# Clean, minimal stylesheet - let Fusion style do the heavy lifting
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


# Available models for MLX Whisper
VALID_MODELS = ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']

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
    """Find the running dbdude-v2t process (Python script or bundled app)."""
    pids = []
    # Search for both bundled executable and Python script
    patterns = ['dbdude-v2t$', 'dbdude-v2t.py']
    for pattern in patterns:
        try:
            result = subprocess.run(
                ['pgrep', '-f', pattern],
                capture_output=True, text=True
            )
            if result.stdout.strip():
                for pid in result.stdout.strip().split('\n'):
                    if pid:
                        pids.append(int(pid))
        except Exception as e:
            print(f"Error finding v2t process with pattern {pattern}: {e}")
    return list(set(pids))  # Remove duplicates


def restart_v2t():
    """Restart the dbdude-v2t application with graceful shutdown."""
    import os
    import time
    from pathlib import Path

    # Find and gracefully stop existing process
    pids = find_v2t_process()
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)  # Graceful shutdown
            print(f"Sent SIGTERM to dbdude-v2t.py (PID {pid})")
        except ProcessLookupError:
            pass
        except Exception as e:
            print(f"Error signaling process {pid}: {e}")

    # Wait for graceful shutdown (up to 3 seconds)
    if pids:
        for _ in range(30):  # 30 x 100ms = 3 seconds
            time.sleep(0.1)
            remaining = find_v2t_process()
            if not remaining:
                print("dbdude-v2t.py shut down gracefully")
                break
        else:
            # Force kill if still running
            for pid in find_v2t_process():
                try:
                    os.kill(pid, signal.SIGKILL)
                    print(f"Force killed dbdude-v2t.py (PID {pid})")
                except:
                    pass

    # Brief pause before starting new instance
    time.sleep(0.2)

    # Start new instance
    # For --onefile mode, use sys.argv[0] to find original exe location
    # (sys.executable and __file__ point to temp extraction folder)
    # If logging is enabled, redirect stdout/stderr to log file instead of DEVNULL
    settings = load_settings()
    if settings.get('log', False):
        log_dir = Path.home() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_fh = open(log_dir / "dbdude-v2t.log", 'a', encoding='utf-8')
        out_target = log_fh
    else:
        log_fh = None
        out_target = subprocess.DEVNULL

    if getattr(sys, 'frozen', False):
        # Bundled app - find main executable in same directory
        exe_dir = Path(sys.argv[0]).resolve().parent
        v2t_path = exe_dir / "dbdude-v2t"
        if v2t_path.exists():
            subprocess.Popen(
                [str(v2t_path)],
                start_new_session=True,
                stdout=out_target,
                stderr=out_target
            )
            print(f"Started new dbdude-v2t instance from {v2t_path}")
            return True
        else:
            if log_fh:
                log_fh.close()
            print(f"dbdude-v2t executable not found at {v2t_path}")
            return False
    else:
        # Development mode - run Python script
        v2t_path = Path(__file__).parent / "dbdude-v2t.py"
        if v2t_path.exists():
            subprocess.Popen(
                [sys.executable, str(v2t_path)],
                start_new_session=True,
                stdout=out_target,
                stderr=out_target
            )
            print("Started new dbdude-v2t.py instance")
            return True
        else:
            if log_fh:
                log_fh.close()
            print(f"dbdude-v2t.py not found at {v2t_path}")
            return False


class ConfiguratorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = load_settings()
        self.input_devices = get_input_devices()
        self._loading = True  # Prevent saves during initial setup

        self.setWindowTitle("dbdude-v2t - Configurator")
        self.setFixedSize(580, 600)
        self.setStyleSheet(STYLESHEET)

        self.setup_ui()
        self.center_on_screen()
        self._loading = False  # Now allow saves

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

        # Settings group
        settings_group = QGroupBox("Settings")
        settings_layout = QGridLayout(settings_group)
        settings_layout.setSpacing(12)
        settings_layout.setContentsMargins(16, 20, 16, 16)

        # Model selection
        settings_layout.addWidget(QLabel("Model:"), 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItems(VALID_MODELS)
        self.model_combo.setCurrentText(self.settings.get("model", "small"))
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
        scroll_layout.setContentsMargins(8, 20, 8, 8)  # Extra top padding to center content

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
        self.settings = {
            'model': self.model_combo.currentText(),
            'language': self.get_language_code(),
            'log': self.log_checkbox.isChecked(),
            'device': self.get_selected_device_name(),
        }
        save_settings(self.settings)

    def on_restart(self):
        """Restart dbdude-v2t application."""
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtCore import QTimer

        # Show "restarting" message
        self.setCursor(Qt.WaitCursor)
        self.setEnabled(False)

        # Do the restart
        success = restart_v2t()

        self.unsetCursor()
        self.setEnabled(True)

        if success:
            # Brief delay to let the new process initialize
            QTimer.singleShot(500, lambda: QMessageBox.information(
                self, "Restart Complete",
                "dbdude-v2t has been restarted.\n\n"
                "New settings are now active."
            ))
        else:
            QMessageBox.warning(self, "Restart Failed",
                "Could not restart dbdude-v2t.\nPlease restart manually.")


def show_configurator():
    """Show the configurator GUI. Settings auto-save on change."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Use Fusion style for consistent, professional look with proper 3D effects
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setPalette(create_app_palette())

    dialog = ConfiguratorDialog()
    dialog.exec()


if __name__ == "__main__":
    show_configurator()
