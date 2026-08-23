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


def get_user_data_dir():
    """Get Linux user data directory (~/.dbdude-v2t)."""
    # Handle sudo: use SUDO_USER's home instead of /root
    sudo_user = os.environ.get('SUDO_USER')
    if sudo_user:
        data_dir = Path(f"/home/{sudo_user}/.dbdude-v2t")
    else:
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


# ALSA exposes a pile of software conversion plugins as "capture devices".
# They are not microphones and only confuse the picker.
_ALSA_PLUMBING = {
    'sysdefault', 'front', 'iec958', 'spdif', 'lavrate', 'samplerate',
    'speexrate', 'a52', 'speex', 'upmix', 'vdownmix', 'dmix', 'dsnoop',
    'null', 'oss', 'jack', 'hdmi', 'modem', 'phoneline',
}


def _is_plumbing(name):
    """True for ALSA software plugins (not real capture hardware)."""
    base = name.split(':')[0].split('(')[0].strip().lower()
    return base in _ALSA_PLUMBING or base.startswith('surround')


def _alsa_capture_cards():
    """Read real capture hardware straight from the kernel.

    /proc/asound is authoritative and readable even when the card is busy,
    which is exactly when PortAudio silently drops the device from its list.
    """
    cards = {}
    try:
        with open('/proc/asound/cards') as fh:
            text = fh.read()
    except OSError:
        return cards

    for line in text.splitlines():
        # e.g. " 1 [Microphones    ]: USB-Audio - Blue Microphones"
        if '[' not in line or ']' not in line or ':' not in line:
            continue
        num_part = line.split('[', 1)[0].strip()
        if not num_part.isdigit():
            continue
        card_id = line.split('[', 1)[1].split(']', 1)[0].strip()
        rest = line.split(']', 1)[1].lstrip(': ').strip()
        driver, _, pretty = rest.partition(' - ')
        if not os.path.isdir(f'/proc/asound/card{num_part}/pcm0c'):
            continue  # no capture stream on this card
        cards[int(num_part)] = {
            'card': int(num_part),
            'id': card_id,
            'name': pretty.strip() or card_id,
            'usb': 'USB' in driver.upper(),
        }
    return cards


def _default_source_description():
    """Human-readable name of the system default input, via PipeWire/Pulse."""
    try:
        name = subprocess.run(['pactl', 'get-default-source'], capture_output=True,
                              text=True, timeout=3).stdout.strip()
        if not name:
            return None
        out = subprocess.run(['pactl', 'list', 'sources'], capture_output=True,
                             text=True, timeout=3).stdout
        block, found = [], False
        for line in out.splitlines():
            if line.strip().startswith('Name:'):
                found = line.split('Name:', 1)[1].strip() == name
            elif found and line.strip().startswith('Description:'):
                return line.split('Description:', 1)[1].strip()
        return name
    except Exception:
        return None


def get_input_devices():
    """Real capture devices, human-labelled, with busy hardware still listed."""
    devices = []
    seen_cards = set()

    try:
        all_devices = sd.query_devices()
    except Exception as e:
        print(f"Error getting input devices: {e}")
        all_devices = []

    # 1. The system default, annotated with what it currently resolves to.
    desc = _default_source_description()
    devices.append({
        'index': -1,
        'name': None,
        'label': f"[--]  Follow system default"
                 f"{f'   (now: {desc})' if desc else ''}",
        'is_default': True,
    })

    # 2. Real hardware from PortAudio, skipping the ALSA plugin noise.
    for i, dev in enumerate(all_devices):
        if dev['max_input_channels'] <= 0 or _is_plumbing(dev['name']):
            continue
        name = dev['name']
        if '(hw:' in name:
            card_digits = name.split('(hw:', 1)[1].split(',', 1)[0]
            if card_digits.isdigit():
                seen_cards.add(int(card_digits))
        # Save the full PortAudio name: two devices on one card share a prefix,
        # so a shortened name would make them indistinguishable on load.
        devices.append({
            'index': i,
            'name': name,
            'label': f"[{i:2}]  {name}   ({dev['max_input_channels']}ch)"
                     f"{'  - always this mic' if '(hw:' in name else ''}",
            'is_default': False,
        })

    # 3. Hardware PortAudio could not probe because it is currently in use.
    #    Without this the mic you are actually recording with is invisible.
    for card in sorted(_alsa_capture_cards().values(), key=lambda c: c['card']):
        if card['card'] in seen_cards:
            continue
        devices.append({
            'index': 1000 + card['card'],
            'name': card['name'],
            'label': f"[c{card['card']}]  {card['name']}"
                     f"{'  (USB)' if card['usb'] else ''}"
                     f"   - always this mic  (busy now, works at startup)",
            'is_default': False,
        })

    return devices


def find_v2t_process():
    """Find the running dbdude-v2t.py process."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'dbdude-v2t.py'],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            # Filter out our own process
            our_pid = os.getpid()
            return [int(pid) for pid in pids if pid and int(pid) != our_pid]
    except Exception as e:
        print(f"Error finding v2t process: {e}")
    return []


def restart_v2t():
    """Restart the dbdude-v2t.py application with graceful shutdown."""
    import time

    # Find and gracefully stop existing process
    pids = find_v2t_process()
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to dbdude-v2t.py (PID {pid})")
        except ProcessLookupError:
            pass
        except Exception as e:
            print(f"Error signaling process {pid}: {e}")

    # Wait for graceful shutdown (up to 3 seconds)
    if pids:
        for _ in range(30):
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

    # Start new instance using the run script
    v2t_dir = Path(__file__).parent
    run_script = v2t_dir / "run-dbdude-v2t.bash"

    if run_script.exists():
        subprocess.Popen(
            ['bash', str(run_script)],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(v2t_dir)
        )
        print("Started new dbdude-v2t.py instance via run script")
        return True
    else:
        # Fallback: try running directly
        v2t_path = v2t_dir / "dbdude-v2t.py"
        if v2t_path.exists():
            subprocess.Popen(
                ['sudo', sys.executable, str(v2t_path)],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("Started new dbdude-v2t.py instance")
            return True
        else:
            print(f"dbdude-v2t.py not found at {v2t_path}")
            return False


class ConfiguratorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = load_settings()
        self.input_devices = get_input_devices()
        self._loading = True

        self.setWindowTitle("dbdude-v2t - Configurator")
        self.setFixedSize(580, 600)
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

        # Settings group
        settings_group = QGroupBox("Settings")
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
        self._device_clicked = False
        self.device_group.buttonClicked.connect(self._on_device_clicked)

        saved_device = self.settings.get("device")
        default_idx = None
        for dev in self.input_devices:
            # Tolerant match: the same mic is named two ways depending on
            # whether it was free at scan time ("Blue Microphones" from the
            # kernel vs "Blue Microphones: USB Audio (hw:1,0)" from PortAudio).
            # The app resolves by substring too, so mirror that here.
            if saved_device and dev['name'] and (
                    saved_device == dev['name']
                    or saved_device.lower() in dev['name'].lower()
                    or dev['name'].lower() in saved_device.lower()):
                default_idx = dev['index']
                break
            if dev['is_default'] and default_idx is None:
                default_idx = dev['index']

        for dev in self.input_devices:
            radio = QRadioButton(dev.get('label') or dev['name'])
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

    def _on_device_clicked(self, *args):
        """Called when user clicks a microphone radio button."""
        self._device_clicked = True
        self._on_setting_changed()

    def _on_setting_changed(self, *args):
        """Auto-save when any setting changes."""
        if self._loading:
            return

        old_device = self.settings.get('device')
        old_model = self.settings.get('model')
        new_model = self.model_combo.currentText()

        # Only update device if user actually clicked a mic radio button
        if self._device_clicked:
            new_device = self.get_selected_device_name()
        else:
            new_device = old_device

        self.settings = {
            'model': new_model,
            'language': self.get_language_code(),
            'log': self.log_checkbox.isChecked(),
            'device': new_device,
        }
        save_settings(self.settings)

        # Show restart message if device or model changed
        changed = []
        if self._device_clicked and old_device != new_device:
            changed.append("Microphone")
        if old_model != new_model:
            changed.append("Model")
        if changed:
            what = " and ".join(changed)
            QMessageBox.information(self, "Restart Required",
                f"{what} change requires a restart.\n\n"
                "Please restart dbdude-v2t for the change to take effect.")

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
