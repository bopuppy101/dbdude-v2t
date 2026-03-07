#!/usr/bin/env python3
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.
"""Voice2Text Mapping/Rules Editor - PySide6 version."""

import sys
import os
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QMessageBox, QHeaderView, QStyleFactory, QCheckBox,
    QGroupBox, QListWidget, QListWidgetItem, QComboBox, QFrame,
    QSplitter, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor


# Rule condition types and operators
CONDITION_TYPES = ["Word count", "Starts with", "Ends with", "Contains"]
OPERATORS = {
    "Word count": ["<=", ">=", "=", "<", ">"],
    "Starts with": ["equals"],
    "Ends with": ["equals"],
    "Contains": ["equals"],
}

# Rule actions
ACTIONS = [
    ("strip_punctuation", "Remove trailing punctuation"),
    ("add_period", "Add period at end"),
    ("add_question", "Add question mark at end"),
    ("lowercase_first", "Lowercase first letter"),
    ("uppercase_first", "Uppercase first letter"),
]


def create_app_palette():
    """Create a refined color palette for the application."""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#f0f0f0"))
    palette.setColor(QPalette.WindowText, QColor("#1a1a1a"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase, QColor("#f7f7f7"))
    palette.setColor(QPalette.Text, QColor("#1a1a1a"))
    palette.setColor(QPalette.Button, QColor("#e0e0e0"))
    palette.setColor(QPalette.ButtonText, QColor("#1a1a1a"))
    palette.setColor(QPalette.Highlight, QColor("#0078d4"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipBase, QColor("#ffffdc"))
    palette.setColor(QPalette.ToolTipText, QColor("#1a1a1a"))
    palette.setColor(QPalette.PlaceholderText, QColor("#808080"))
    return palette


STYLESHEET = """
QMainWindow {
    background-color: #f0f0f0;
}
QWidget {
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    background-color: #fafafa;
    padding: 8px;
}
QLabel {
    color: #303030;
}
QLineEdit, QComboBox {
    font-size: 13px;
    padding: 6px 10px;
}
QListWidget {
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    background-color: #ffffff;
}
QListWidget::item {
    padding: 6px;
}
QListWidget::item:selected {
    background-color: #0078d4;
    color: white;
}
QTableWidget {
    gridline-color: #e0e0e0;
    selection-background-color: #0078d4;
    selection-color: white;
}
QTableWidget::item {
    padding: 6px;
}
QHeaderView::section {
    font-weight: bold;
    font-size: 13px;
    padding: 8px;
}
QPushButton {
    font-size: 13px;
    font-weight: 500;
    padding: 8px 20px;
    min-width: 80px;
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
"""

PRIMARY_STYLE = """
    QPushButton {
        background-color: #0078d4;
        color: #ffffff;
        border: 1px solid #005a9e;
        border-radius: 4px;
    }
    QPushButton:hover { background-color: #1084d8; }
    QPushButton:pressed { background-color: #005a9e; }
"""

DANGER_STYLE = """
    QPushButton {
        background-color: #d32f2f;
        color: #ffffff;
        border: 1px solid #b71c1c;
        border-radius: 4px;
    }
    QPushButton:hover { background-color: #e53935; }
    QPushButton:pressed { background-color: #b71c1c; }
"""

APPDATA_FOLDER = "Voice2Text"


def get_user_data_dir():
    """Get user data directory (~/.voice2text)."""
    data_dir = Path.home() / ".voice2text"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_app_dir():
    """Get the directory containing the application."""
    # For Nuitka onefile: use sys.argv[0] which has the original exe path
    # (sys.executable and __nuitka_binary_dir point to temp extraction folder)
    if sys.argv and sys.argv[0]:
        argv0_path = Path(sys.argv[0]).resolve().parent
        if (argv0_path / 'maps' / 'packs').exists():
            return argv0_path
    # Fallback for Nuitka standalone or PyInstaller
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    # For regular Python
    return Path(__file__).parent


def load_mappings():
    """Load custom mappings from file."""
    maps_file = get_user_data_dir() / "custom_mappings.json"
    if maps_file.exists():
        try:
            with open(maps_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading mappings: {e}")
    return {"wildcard_mode": "sql92", "enabled_packs": [], "names": {}}


def save_mappings(data):
    """Save custom mappings to file."""
    maps_file = get_user_data_dir() / "custom_mappings.json"
    try:
        with open(maps_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving mappings: {e}")
        return False


def load_rules():
    """Load rules from file."""
    rules_file = get_user_data_dir() / "rules.json"
    if rules_file.exists():
        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading rules: {e}")
    return {"rules": []}


def save_rules(data):
    """Save rules to file."""
    rules_file = get_user_data_dir() / "rules.json"
    try:
        with open(rules_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving rules: {e}")
        return False


def get_available_packs():
    """Get list of available map packs with their data."""
    packs = {}
    packs_dir = get_app_dir() / "maps" / "packs"
    if packs_dir.exists():
        for pack_file in packs_dir.glob("*.json"):
            try:
                with open(pack_file, 'r', encoding='utf-8') as f:
                    pack_data = json.load(f)
                    pack_name = pack_data.get("_name", pack_file.stem)
                    pack_data["_file_path"] = str(pack_file.resolve())
                    packs[pack_name] = pack_data
            except Exception as e:
                print(f"Error loading pack {pack_file}: {e}")
    return packs


class MappingRulesWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.data = load_mappings()
        self.rules_data = load_rules()
        self.packs = get_available_packs()
        self.selected_pack = None

        self.setWindowTitle("Voice2Text - Mapping/Rules")
        self.setMinimumSize(900, 700)
        self.resize(1000, 750)
        self.setStyleSheet(STYLESHEET)

        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def setup_ui(self):
        central = QWidget()
        central.setStyleSheet("background-color: #f5f5f7;")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = QLabel("Voice2Text - Mapping/Rules")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a1a1a;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Custom Mappings tab
        mappings_tab = QWidget()
        mappings_tab.setStyleSheet("background-color: #ffffff;")
        tabs.addTab(mappings_tab, "Custom Mappings")
        self.setup_mappings_tab(mappings_tab)

        # Rules tab
        rules_tab = QWidget()
        rules_tab.setStyleSheet("background-color: #ffffff;")
        tabs.addTab(rules_tab, "Rules")
        self.setup_rules_tab(rules_tab)

        # Map Packs tab
        packs_tab = QWidget()
        packs_tab.setStyleSheet("background-color: #ffffff;")
        tabs.addTab(packs_tab, "Map Packs")
        self.setup_packs_tab(packs_tab)

    # =========================================================================
    # CUSTOM MAPPINGS TAB
    # =========================================================================
    def setup_mappings_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Show file path
        maps_file = get_user_data_dir() / "custom_mappings.json"
        path_label = QLabel(f"Config file: {maps_file}")
        path_label.setStyleSheet("font-size: 11px; color: #888888; font-family: Consolas, monospace;")
        layout.addWidget(path_label)

        # Top row: instructions and wildcard mode
        top_layout = QHBoxLayout()

        instructions = QLabel("Map spoken phrases to text replacements:")
        instructions.setStyleSheet("font-size: 14px; color: #555555; margin-bottom: 4px;")
        top_layout.addWidget(instructions)

        top_layout.addStretch()

        top_layout.addWidget(QLabel("Wildcard Mode:"))
        self.wildcard_mode_combo = QComboBox()
        self.wildcard_mode_combo.addItems(["None", "SQL-92", "Regex"])
        self.wildcard_mode_combo.setToolTip(
            "None: Literal matching only\n"
            "SQL-92: Use % for any chars, _ for single char\n"
            "Regex: Full regular expression patterns"
        )
        # Set current value from data
        current_mode = self.data.get("wildcard_mode", "sql92")
        mode_map = {"none": "None", "sql92": "SQL-92", "regex": "Regex"}
        self.wildcard_mode_combo.setCurrentText(mode_map.get(current_mode, "SQL-92"))
        self.wildcard_mode_combo.currentTextChanged.connect(self.on_wildcard_mode_change)
        top_layout.addWidget(self.wildcard_mode_combo)

        layout.addLayout(top_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["From\nSpoken Phrase", "To\nReplacement", "Strip\nPunct", "Strip WS\nBefore", "Strip WS\nAfter"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        # Load existing mappings
        self._refresh_mappings_table()
        layout.addWidget(self.table)

        # Up/Down buttons for reordering
        reorder_layout = QHBoxLayout()
        reorder_layout.setSpacing(10)

        up_btn = QPushButton("▲ Up")
        up_btn.setMaximumWidth(70)
        up_btn.clicked.connect(self.move_mapping_up)
        reorder_layout.addWidget(up_btn)

        down_btn = QPushButton("▼ Down")
        down_btn.setMaximumWidth(70)
        down_btn.clicked.connect(self.move_mapping_down)
        reorder_layout.addWidget(down_btn)

        reorder_layout.addStretch()
        layout.addLayout(reorder_layout)

        # Entry fields
        entry_layout = QHBoxLayout()
        entry_layout.setSpacing(12)

        entry_layout.addWidget(QLabel("From:"))
        self.spoken_entry = QLineEdit()
        self.spoken_entry.setPlaceholderText("Enter spoken phrase")
        entry_layout.addWidget(self.spoken_entry, 1)

        entry_layout.addWidget(QLabel("To:"))
        self.replacement_entry = QLineEdit()
        self.replacement_entry.setPlaceholderText("Enter replacement text")
        entry_layout.addWidget(self.replacement_entry, 1)

        self.strip_checkbox = QCheckBox("Strip punctuation")
        self.strip_checkbox.setToolTip("Remove trailing period after this replacement")
        entry_layout.addWidget(self.strip_checkbox)

        self.strip_ws_before_checkbox = QCheckBox("Strip WS before")
        self.strip_ws_before_checkbox.setToolTip("Remove whitespace before this replacement")
        entry_layout.addWidget(self.strip_ws_before_checkbox)

        self.strip_ws_after_checkbox = QCheckBox("Strip WS after")
        self.strip_ws_after_checkbox.setToolTip("Remove whitespace after this replacement")
        entry_layout.addWidget(self.strip_ws_after_checkbox)

        layout.addLayout(entry_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        add_btn = QPushButton("Add")
        add_btn.setStyleSheet(PRIMARY_STYLE)
        add_btn.clicked.connect(self.add_mapping)
        btn_layout.addWidget(add_btn)

        update_btn = QPushButton("Update")
        update_btn.clicked.connect(self.update_mapping)
        btn_layout.addWidget(update_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet(DANGER_STYLE)
        delete_btn.clicked.connect(self.delete_mapping)
        btn_layout.addWidget(delete_btn)

        sort_btn = QPushButton("Sort")
        sort_btn.clicked.connect(self.sort_mappings)
        btn_layout.addWidget(sort_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _refresh_mappings_table(self):
        """Refresh the mappings table."""
        names = self.data.get("names", {})
        self.table.setRowCount(len(names))
        for row, (spoken, entry) in enumerate(names.items()):
            self.table.setItem(row, 0, QTableWidgetItem(spoken))
            if isinstance(entry, dict):
                replacement = entry.get("value", "")
                strip_punct = entry.get("strip_punctuation", False)
                strip_ws_before = entry.get("strip_whitespace_before", False)
                strip_ws_after = entry.get("strip_whitespace_after", False)
            else:
                replacement = entry
                strip_punct = False
                strip_ws_before = False
                strip_ws_after = False
            self.table.setItem(row, 1, QTableWidgetItem(replacement))
            strip_item = QTableWidgetItem("Yes" if strip_punct else "No")
            strip_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, strip_item)
            ws_before_item = QTableWidgetItem("Yes" if strip_ws_before else "No")
            ws_before_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, ws_before_item)
            ws_after_item = QTableWidgetItem("Yes" if strip_ws_after else "No")
            ws_after_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, ws_after_item)

    def on_selection_changed(self):
        """When a row is selected, populate the entry fields."""
        rows = self.table.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            spoken_item = self.table.item(row, 0)
            replacement_item = self.table.item(row, 1)
            strip_item = self.table.item(row, 2)
            ws_before_item = self.table.item(row, 3)
            ws_after_item = self.table.item(row, 4)
            if spoken_item and replacement_item:
                self.spoken_entry.setText(spoken_item.text())
                self.replacement_entry.setText(replacement_item.text())
                self.strip_checkbox.setChecked(strip_item and strip_item.text() == "Yes")
                self.strip_ws_before_checkbox.setChecked(ws_before_item and ws_before_item.text() == "Yes")
                self.strip_ws_after_checkbox.setChecked(ws_after_item and ws_after_item.text() == "Yes")

    def _save_mappings(self):
        """Save current mappings to file."""
        names = {}
        for row in range(self.table.rowCount()):
            spoken_item = self.table.item(row, 0)
            replacement_item = self.table.item(row, 1)
            strip_item = self.table.item(row, 2)
            ws_before_item = self.table.item(row, 3)
            ws_after_item = self.table.item(row, 4)
            if spoken_item and replacement_item:
                spoken = spoken_item.text()
                replacement = replacement_item.text()
                strip_punct = strip_item and strip_item.text() == "Yes"
                strip_ws_before = ws_before_item and ws_before_item.text() == "Yes"
                strip_ws_after = ws_after_item and ws_after_item.text() == "Yes"
                # Only use dict format if any flag is set
                if strip_punct or strip_ws_before or strip_ws_after:
                    entry = {"value": replacement}
                    if strip_punct:
                        entry["strip_punctuation"] = True
                    if strip_ws_before:
                        entry["strip_whitespace_before"] = True
                    if strip_ws_after:
                        entry["strip_whitespace_after"] = True
                    names[spoken] = entry
                else:
                    names[spoken] = replacement
        self.data["names"] = names
        save_mappings(self.data)

    def add_mapping(self):
        """Add a new mapping."""
        spoken = self.spoken_entry.text().strip()
        replacement = self.replacement_entry.text().strip()
        strip_punct = self.strip_checkbox.isChecked()
        strip_ws_before = self.strip_ws_before_checkbox.isChecked()
        strip_ws_after = self.strip_ws_after_checkbox.isChecked()

        if not spoken or not replacement:
            QMessageBox.warning(self, "Warning", "Both fields are required")
            return

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text().lower() == spoken.lower():
                QMessageBox.warning(self, "Warning",
                    "This spoken phrase already exists. Use Update to modify.")
                return

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(spoken))
        self.table.setItem(row, 1, QTableWidgetItem(replacement))
        strip_item = QTableWidgetItem("Yes" if strip_punct else "No")
        strip_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 2, strip_item)
        ws_before_item = QTableWidgetItem("Yes" if strip_ws_before else "No")
        ws_before_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 3, ws_before_item)
        ws_after_item = QTableWidgetItem("Yes" if strip_ws_after else "No")
        ws_after_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 4, ws_after_item)

        self.spoken_entry.clear()
        self.replacement_entry.clear()
        self.strip_checkbox.setChecked(False)
        self.strip_ws_before_checkbox.setChecked(False)
        self.strip_ws_after_checkbox.setChecked(False)
        self._save_mappings()

    def update_mapping(self):
        """Update the selected mapping."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "Warning", "Select a mapping to update")
            return

        spoken = self.spoken_entry.text().strip()
        replacement = self.replacement_entry.text().strip()
        strip_punct = self.strip_checkbox.isChecked()
        strip_ws_before = self.strip_ws_before_checkbox.isChecked()
        strip_ws_after = self.strip_ws_after_checkbox.isChecked()

        if not spoken or not replacement:
            QMessageBox.warning(self, "Warning", "Both fields are required")
            return

        row = rows[0].row()
        self.table.setItem(row, 0, QTableWidgetItem(spoken))
        self.table.setItem(row, 1, QTableWidgetItem(replacement))
        strip_item = QTableWidgetItem("Yes" if strip_punct else "No")
        strip_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 2, strip_item)
        ws_before_item = QTableWidgetItem("Yes" if strip_ws_before else "No")
        ws_before_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 3, ws_before_item)
        ws_after_item = QTableWidgetItem("Yes" if strip_ws_after else "No")
        ws_after_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 4, ws_after_item)
        self._save_mappings()

    def delete_mapping(self):
        """Delete the selected mapping."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "Warning", "Select a mapping to delete")
            return

        reply = QMessageBox.question(self, "Confirm", "Delete this mapping?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.table.removeRow(rows[0].row())
            self.spoken_entry.clear()
            self.replacement_entry.clear()
            self.strip_checkbox.setChecked(False)
            self._save_mappings()

    def on_wildcard_mode_change(self, text):
        """Handle wildcard mode dropdown change."""
        mode_map = {"None": "none", "SQL-92": "sql92", "Regex": "regex"}
        self.data["wildcard_mode"] = mode_map.get(text, "sql92")
        save_mappings(self.data)

    def sort_mappings(self):
        """Sort mappings by replacement value, then by spoken word."""
        names = self.data.get("names", {})
        if not names:
            return

        # Build list for sorting: (spoken, replacement_value, entry)
        mappings_list = []
        for spoken, entry in names.items():
            if isinstance(entry, dict):
                replacement = entry.get("value", "")
            else:
                replacement = entry
            mappings_list.append((spoken, replacement, entry))

        # Sort by replacement (case-insensitive), then by spoken (case-insensitive)
        mappings_list.sort(key=lambda x: (x[1].lower(), x[0].lower()))

        # Rebuild the names dict in sorted order
        sorted_names = {}
        for spoken, replacement, entry in mappings_list:
            sorted_names[spoken] = entry

        self.data["names"] = sorted_names
        save_mappings(self.data)
        self._refresh_mappings_table()

    def move_mapping_up(self):
        """Move selected mapping up one row."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if row <= 0:
            return  # Already at top

        # Swap rows in table
        self._swap_table_rows(row, row - 1)
        self.table.selectRow(row - 1)
        self._save_mappings()

    def move_mapping_down(self):
        """Move selected mapping down one row."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if row >= self.table.rowCount() - 1:
            return  # Already at bottom

        # Swap rows in table
        self._swap_table_rows(row, row + 1)
        self.table.selectRow(row + 1)
        self._save_mappings()

    def _swap_table_rows(self, row1, row2):
        """Swap two rows in the table."""
        for col in range(self.table.columnCount()):
            item1 = self.table.takeItem(row1, col)
            item2 = self.table.takeItem(row2, col)
            self.table.setItem(row1, col, item2)
            self.table.setItem(row2, col, item1)

    # =========================================================================
    # RULES TAB
    # =========================================================================
    def setup_rules_tab(self, parent):
        layout = QHBoxLayout(parent)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # === LEFT PANEL ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Header
        header = QLabel("Your Rules")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        left_layout.addWidget(header)

        notice = QLabel("Rules are evaluated in order; first match wins.\nRestart Voice2Text after changes.")
        notice.setStyleSheet("font-size: 11px; color: #666666; font-style: italic;")
        left_layout.addWidget(notice)

        # Active Rules list
        rules_group = QGroupBox("Active Rules")
        rules_group_layout = QVBoxLayout(rules_group)

        self.rules_list = QListWidget()
        self.rules_list.itemSelectionChanged.connect(self.on_rule_select)
        rules_group_layout.addWidget(self.rules_list)

        # Buttons
        btn_layout = QHBoxLayout()
        up_btn = QPushButton("▲ Up")
        up_btn.setMaximumWidth(70)
        up_btn.clicked.connect(self.move_rule_up)
        btn_layout.addWidget(up_btn)

        down_btn = QPushButton("▼ Down")
        down_btn.setMaximumWidth(70)
        down_btn.clicked.connect(self.move_rule_down)
        btn_layout.addWidget(down_btn)

        del_btn = QPushButton("Delete")
        del_btn.setStyleSheet(DANGER_STYLE)
        del_btn.clicked.connect(self.delete_rule)
        btn_layout.addWidget(del_btn)

        btn_layout.addStretch()
        rules_group_layout.addLayout(btn_layout)

        left_layout.addWidget(rules_group)

        # Selected Rule Details
        detail_group = QGroupBox("Selected Rule Details")
        detail_layout = QVBoxLayout(detail_group)

        self.rule_detail_text = QTextEdit()
        self.rule_detail_text.setReadOnly(True)
        self.rule_detail_text.setMaximumHeight(120)
        self.rule_detail_text.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        detail_layout.addWidget(self.rule_detail_text)

        self.rule_enabled_checkbox = QCheckBox("Enabled")
        self.rule_enabled_checkbox.setEnabled(False)
        self.rule_enabled_checkbox.stateChanged.connect(self.on_rule_enabled_toggle)
        detail_layout.addWidget(self.rule_enabled_checkbox)

        left_layout.addWidget(detail_group)
        layout.addWidget(left_panel, 1)

        # === RIGHT PANEL ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Header
        editor_header = QLabel("Create New Rule")
        editor_header.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_layout.addWidget(editor_header)

        # Rule Definition
        editor_group = QGroupBox("Rule Definition")
        editor_layout = QVBoxLayout(editor_group)

        # Rule name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Rule Name:"))
        self.rule_name_entry = QLineEdit()
        self.rule_name_entry.setPlaceholderText("Enter rule name")
        name_layout.addWidget(self.rule_name_entry)
        editor_layout.addLayout(name_layout)

        # Condition (IF)
        cond_layout = QHBoxLayout()
        cond_layout.addWidget(QLabel("IF:"))

        self.condition_type_combo = QComboBox()
        self.condition_type_combo.addItems(CONDITION_TYPES)
        self.condition_type_combo.currentTextChanged.connect(self.on_condition_type_change)
        cond_layout.addWidget(self.condition_type_combo)

        self.operator_combo = QComboBox()
        self.operator_combo.addItems(OPERATORS["Word count"])
        cond_layout.addWidget(self.operator_combo)

        self.condition_value_entry = QLineEdit()
        self.condition_value_entry.setText("3")
        self.condition_value_entry.setMaximumWidth(80)
        cond_layout.addWidget(self.condition_value_entry)

        cond_layout.addStretch()
        editor_layout.addLayout(cond_layout)

        # Actions (THEN)
        then_label = QLabel("THEN:")
        editor_layout.addWidget(then_label)

        self.action_checkboxes = {}
        for action_id, action_label in ACTIONS:
            cb = QCheckBox(action_label)
            self.action_checkboxes[action_id] = cb
            editor_layout.addWidget(cb)

        # Add Rule button
        add_rule_btn = QPushButton("Add Rule")
        add_rule_btn.setStyleSheet(PRIMARY_STYLE)
        add_rule_btn.clicked.connect(self.add_rule)
        editor_layout.addWidget(add_rule_btn)

        right_layout.addWidget(editor_group)

        # Example Rule
        example_group = QGroupBox("Example Rule (click to use)")
        example_layout = QVBoxLayout(example_group)

        example_label = QLabel("• Short phrase formatting: If 3 words or less,\n  remove punctuation and lowercase")
        example_label.setStyleSheet("color: #0078d4; cursor: pointer;")
        example_label.mousePressEvent = lambda e: self.load_example_rule()
        example_layout.addWidget(example_label)

        right_layout.addWidget(example_group)

        # How Rules Work
        explain_group = QGroupBox("How Rules Work")
        explain_layout = QVBoxLayout(explain_group)

        explain_text = QLabel(
            "Use Mappings to fix misheard words.\n"
            "Use Rules to control formatting based on conditions.\n\n"
            "Example: If transcription is 3 words or less,\n"
            "remove punctuation and lowercase - these are\n"
            "likely inserts/edits that don't need sentence formatting."
        )
        explain_text.setStyleSheet("font-size: 11px; color: #666666;")
        explain_layout.addWidget(explain_text)

        right_layout.addWidget(explain_group)
        right_layout.addStretch()

        layout.addWidget(right_panel, 1)

        # Load existing rules
        self._refresh_rules_list()

    def _refresh_rules_list(self):
        """Refresh the rules list."""
        self.rules_list.clear()
        for rule in self.rules_data.get("rules", []):
            name = rule.get("name", "Unnamed Rule")
            enabled = rule.get("enabled", True)
            status = "" if enabled else " [disabled]"
            self.rules_list.addItem(f"{name}{status}")

    def on_rule_select(self):
        """Handle rule selection."""
        row = self.rules_list.currentRow()
        if row >= 0 and row < len(self.rules_data.get("rules", [])):
            rule = self.rules_data["rules"][row]
            self.rule_detail_text.setText(json.dumps(rule, indent=2))
            self.rule_enabled_checkbox.setEnabled(True)
            self.rule_enabled_checkbox.blockSignals(True)
            self.rule_enabled_checkbox.setChecked(rule.get("enabled", True))
            self.rule_enabled_checkbox.blockSignals(False)
        else:
            self.rule_detail_text.clear()
            self.rule_enabled_checkbox.setEnabled(False)

    def on_rule_enabled_toggle(self):
        """Toggle rule enabled state."""
        row = self.rules_list.currentRow()
        if row >= 0 and row < len(self.rules_data.get("rules", [])):
            self.rules_data["rules"][row]["enabled"] = self.rule_enabled_checkbox.isChecked()
            save_rules(self.rules_data)
            self._refresh_rules_list()
            self.rules_list.setCurrentRow(row)

    def on_condition_type_change(self, text):
        """Update operators when condition type changes."""
        self.operator_combo.clear()
        self.operator_combo.addItems(OPERATORS.get(text, ["equals"]))

    def add_rule(self):
        """Add a new rule."""
        name = self.rule_name_entry.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a rule name")
            return

        # Get selected actions
        actions = [action_id for action_id, cb in self.action_checkboxes.items() if cb.isChecked()]
        if not actions:
            QMessageBox.warning(self, "Warning", "Please select at least one action")
            return

        # Build condition
        cond_type = self.condition_type_combo.currentText()
        operator = self.operator_combo.currentText()
        value = self.condition_value_entry.text().strip()

        if cond_type == "Word count":
            try:
                value = int(value)
            except ValueError:
                QMessageBox.warning(self, "Warning", "Word count must be a number")
                return
            condition = {"type": "word_count", "operator": operator, "value": value}
        else:
            cond_type_map = {
                "Starts with": "starts_with",
                "Ends with": "ends_with",
                "Contains": "contains"
            }
            condition = {"type": cond_type_map[cond_type], "value": value}

        rule = {
            "name": name,
            "enabled": True,
            "condition": condition,
            "actions": actions
        }

        if "rules" not in self.rules_data:
            self.rules_data["rules"] = []
        self.rules_data["rules"].append(rule)
        save_rules(self.rules_data)
        self._refresh_rules_list()

        # Clear form
        self.rule_name_entry.clear()
        for cb in self.action_checkboxes.values():
            cb.setChecked(False)

    def move_rule_up(self):
        """Move selected rule up."""
        row = self.rules_list.currentRow()
        if row > 0:
            rules = self.rules_data.get("rules", [])
            rules[row], rules[row-1] = rules[row-1], rules[row]
            save_rules(self.rules_data)
            self._refresh_rules_list()
            self.rules_list.setCurrentRow(row - 1)

    def move_rule_down(self):
        """Move selected rule down."""
        row = self.rules_list.currentRow()
        rules = self.rules_data.get("rules", [])
        if row >= 0 and row < len(rules) - 1:
            rules[row], rules[row+1] = rules[row+1], rules[row]
            save_rules(self.rules_data)
            self._refresh_rules_list()
            self.rules_list.setCurrentRow(row + 1)

    def delete_rule(self):
        """Delete selected rule."""
        row = self.rules_list.currentRow()
        if row >= 0:
            reply = QMessageBox.question(self, "Confirm", "Delete this rule?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                del self.rules_data["rules"][row]
                save_rules(self.rules_data)
                self._refresh_rules_list()
                self.rule_detail_text.clear()
                self.rule_enabled_checkbox.setEnabled(False)

    def load_example_rule(self):
        """Load example rule into form."""
        self.rule_name_entry.setText("Short phrase formatting")
        self.condition_type_combo.setCurrentText("Word count")
        self.operator_combo.setCurrentText("<=")
        self.condition_value_entry.setText("3")
        self.action_checkboxes["strip_punctuation"].setChecked(True)
        self.action_checkboxes["lowercase_first"].setChecked(True)

    # =========================================================================
    # MAP PACKS TAB
    # =========================================================================
    def setup_packs_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header row with path
        header_layout = QHBoxLayout()

        header = QLabel("Map Packs")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(header)

        header_layout.addStretch()

        packs_dir = get_app_dir() / "maps" / "packs"
        packs_path_label = QLabel(f"Packs folder: {packs_dir}")
        packs_path_label.setStyleSheet("font-size: 11px; color: #888888; font-family: Consolas, monospace;")
        header_layout.addWidget(packs_path_label)

        layout.addLayout(header_layout)

        instructions = QLabel("Check to enable, click to preview contents")
        instructions.setStyleSheet("font-size: 12px; color: #666666; font-style: italic;")
        layout.addWidget(instructions)

        # Available Map Packs
        packs_group = QGroupBox("Available Map Packs")
        packs_layout = QVBoxLayout(packs_group)

        self.pack_list = QListWidget()
        self.pack_list.itemClicked.connect(self.on_pack_click)
        packs_layout.addWidget(self.pack_list)

        layout.addWidget(packs_group)

        # Pack description
        self.pack_desc = QLabel("")
        self.pack_desc.setStyleSheet("font-size: 12px; color: #666666; font-style: italic;")
        layout.addWidget(self.pack_desc)

        # Map Pack Contents
        contents_group = QGroupBox("Map Pack Contents")
        contents_layout = QVBoxLayout(contents_group)

        self.pack_contents_list = QListWidget()
        self.pack_contents_list.setAlternatingRowColors(True)
        self.pack_contents_list.setStyleSheet("""
            QListWidget {
                font-family: Consolas, monospace;
                font-size: 12px;
            }
            QListWidget::item {
                border-bottom: 2px solid #b0b0b0;
                padding: 3px 6px;
            }
            QListWidget::item:alternate {
                background-color: #e8e8e8;
            }
        """)
        contents_layout.addWidget(self.pack_contents_list)

        layout.addWidget(contents_group)

        # Populate pack list
        self._refresh_pack_list()

        # Status
        status = QLabel("Restart to pick up new mappings.")
        status.setStyleSheet("font-size: 11px; color: #888888;")
        layout.addWidget(status)

    def _refresh_pack_list(self):
        """Refresh the pack list with checkboxes."""
        self.pack_list.clear()
        enabled_packs = self.data.get("enabled_packs", [])

        for pack_name in sorted(self.packs.keys()):
            pack_data = self.packs[pack_name]
            file_path = pack_data.get("_file_path", "")
            display_text = f"{pack_name}    {file_path}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, pack_name)  # Store pack name for lookups
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if pack_name in enabled_packs else Qt.Unchecked)
            self.pack_list.addItem(item)

        # Connect itemChanged after populating to avoid triggering during setup
        try:
            self.pack_list.itemChanged.disconnect()
        except:
            pass
        self.pack_list.itemChanged.connect(self.on_pack_toggle)

    def on_pack_click(self, item):
        """Handle pack click - show contents."""
        pack_name = item.data(Qt.UserRole)
        self.selected_pack = pack_name
        pack_data = self.packs.get(pack_name, {})

        # Update description
        desc = pack_data.get("_description", "")
        mapping_count = len(pack_data.get("names", {}))
        if desc:
            self.pack_desc.setText(f"{desc} ({mapping_count} mappings)")
        else:
            self.pack_desc.setText(f"{mapping_count} mappings")

        # Update contents list
        self.pack_contents_list.clear()
        for heard, replace in sorted(pack_data.get("names", {}).items()):
            self.pack_contents_list.addItem(f'"{heard}"  →  "{replace}"')

    def on_pack_toggle(self, item):
        """Handle pack checkbox toggle."""
        try:
            pack_name = item.data(Qt.UserRole)
            enabled = item.checkState() == Qt.Checked

            # Ensure enabled_packs exists
            if "enabled_packs" not in self.data:
                self.data["enabled_packs"] = []

            if enabled:
                if pack_name not in self.data["enabled_packs"]:
                    self.data["enabled_packs"].append(pack_name)
            else:
                if pack_name in self.data["enabled_packs"]:
                    self.data["enabled_packs"].remove(pack_name)

            if not save_mappings(self.data):
                QMessageBox.warning(self, "Error", f"Failed to save pack settings for '{pack_name}'")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to toggle pack '{pack_name}': {e}")


def show_mapping_rules():
    """Show the mapping/rules editor."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setStyle(QStyleFactory.create("Fusion"))
    app.setPalette(create_app_palette())

    window = MappingRulesWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    show_mapping_rules()
