#!/usr/bin/env python3
# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under CC BY-NC 4.0.
"""dbdude-v2t Mapping/Rules Editor for Ubuntu - PySide6 version."""

import sys
import os
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QMessageBox, QHeaderView, QStyleFactory, QCheckBox,
    QGroupBox, QScrollArea, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor


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

QLineEdit {
    font-size: 13px;
    padding: 6px 10px;
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


def get_user_data_dir():
    """Get Linux user data directory (~/.dbdude-v2t)."""
    sudo_user = os.environ.get('SUDO_USER')
    if sudo_user:
        data_dir = Path(f"/home/{sudo_user}/.dbdude-v2t")
    else:
        data_dir = Path.home() / ".dbdude-v2t"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_app_dir():
    """Get the directory containing the script."""
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


def get_available_packs():
    """Get list of available map packs."""
    packs = []
    packs_dir = get_app_dir() / "maps" / "packs"
    if packs_dir.exists():
        for pack_file in packs_dir.glob("*.json"):
            try:
                with open(pack_file, 'r', encoding='utf-8') as f:
                    pack_data = json.load(f)
                    pack_name = pack_data.get("_name", pack_file.stem)
                    pack_desc = pack_data.get("_description", "")
                    count = len(pack_data.get("names", {}))
                    packs.append({
                        "name": pack_name,
                        "description": pack_desc,
                        "count": count,
                        "file": pack_file.name
                    })
            except Exception as e:
                print(f"Error loading pack {pack_file}: {e}")
    return packs


class MappingRulesWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.data = load_mappings()
        self.available_packs = get_available_packs()

        self.setWindowTitle("dbdude-v2t - Mapping/Rules")
        self.setMinimumSize(700, 600)
        self.resize(700, 600)
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
        header = QLabel("dbdude-v2t - Mapping/Rules")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a1a1a;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Custom Mappings tab (first)
        mappings_tab = QWidget()
        mappings_tab.setStyleSheet("background-color: #ffffff;")
        tabs.addTab(mappings_tab, "Custom Mappings")
        self.setup_mappings_tab(mappings_tab)

        # Rules tab (placeholder)
        rules_tab = QWidget()
        rules_tab.setStyleSheet("background-color: #ffffff;")
        tabs.addTab(rules_tab, "Rules")
        self.setup_rules_tab(rules_tab)

        # Map Packs tab (last)
        packs_tab = QWidget()
        packs_tab.setStyleSheet("background-color: #ffffff;")
        tabs.addTab(packs_tab, "Map Packs")
        self.setup_packs_tab(packs_tab)

    def setup_packs_tab(self, parent):
        """Setup the Map Packs tab."""
        layout = QVBoxLayout(parent)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        instructions = QLabel("Enable or disable built-in map packs:")
        instructions.setStyleSheet("font-size: 14px; color: #555555; margin-bottom: 4px;")
        layout.addWidget(instructions)

        # Pack checkboxes
        self.pack_checkboxes = {}
        enabled_packs = self.data.get("enabled_packs", [])

        for pack in self.available_packs:
            group = QGroupBox(pack["name"])
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(12, 16, 12, 12)

            desc = QLabel(pack["description"] or f"{pack['count']} mappings")
            desc.setStyleSheet("font-weight: normal; color: #666666;")
            group_layout.addWidget(desc)

            checkbox = QCheckBox("Enabled")
            checkbox.setChecked(pack["name"] in enabled_packs)
            checkbox.stateChanged.connect(self._on_pack_changed)
            self.pack_checkboxes[pack["name"]] = checkbox
            group_layout.addWidget(checkbox)

            layout.addWidget(group)

        layout.addStretch()

        # Info label
        info = QLabel("Changes take effect after restarting dbdude-v2t.")
        info.setStyleSheet("font-size: 12px; color: #888888; font-style: italic;")
        layout.addWidget(info)

    def setup_mappings_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Top row: instructions and wildcard mode
        top_layout = QHBoxLayout()

        instructions = QLabel("Map spoken phrases to text replacements:")
        instructions.setStyleSheet("font-size: 14px; color: #555555; margin-bottom: 4px;")
        top_layout.addWidget(instructions)

        top_layout.addStretch()

        top_layout.addWidget(QLabel("Wildcard Mode:"))
        self.wildcard_mode_combo = QComboBox()
        self.wildcard_mode_combo.addItems(["None", "SQL-92"])
        self.wildcard_mode_combo.setToolTip(
            "None: Literal matching only\n"
            "SQL-92: Use % for any chars, _ for single char"
        )
        # Set current value from data
        current_mode = self.data.get("wildcard_mode", "sql92")
        mode_map = {"none": "None", "sql92": "SQL-92"}
        self.wildcard_mode_combo.setCurrentText(mode_map.get(current_mode, "SQL-92"))
        self.wildcard_mode_combo.currentTextChanged.connect(self.on_wildcard_mode_change)
        top_layout.addWidget(self.wildcard_mode_combo)

        layout.addLayout(top_layout)

        # Show file path, so there's never ambiguity about which file is live.
        maps_file = get_user_data_dir() / "custom_mappings.json"
        path_label = QLabel(f"Config file: {maps_file}")
        path_label.setStyleSheet("font-size: 11px; color: #888888; font-family: monospace;")
        path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        path_label.setToolTip(str(maps_file))
        layout.addWidget(path_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Spoken Phrase", "Replacement", "Strip Punct", "Strip WS Before", "Strip WS After"])
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
        names = self.data.get("names", {})
        self.table.setRowCount(len(names))
        for row, (spoken, entry) in enumerate(names.items()):
            self.table.setItem(row, 0, QTableWidgetItem(spoken))

            # Handle both string and dict format
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

        layout.addWidget(self.table)

        # Entry fields
        entry_layout = QHBoxLayout()
        entry_layout.setSpacing(12)

        entry_layout.addWidget(QLabel("Spoken:"))
        self.spoken_entry = QLineEdit()
        self.spoken_entry.setPlaceholderText("Enter spoken phrase")
        entry_layout.addWidget(self.spoken_entry, 1)

        entry_layout.addWidget(QLabel("Replacement:"))
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

        btn_layout.addStretch()

        layout.addLayout(btn_layout)

    def setup_rules_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(20, 40, 20, 20)

        label = QLabel("Rules editor coming soon...")
        label.setStyleSheet("font-size: 16px; color: #888888;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        sublabel = QLabel("This will allow you to define text transformation rules\n"
                          "like capitalization, punctuation, and formatting.")
        sublabel.setStyleSheet("font-size: 13px; color: #aaaaaa;")
        sublabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(sublabel)

        layout.addStretch()

    def _on_pack_changed(self):
        """Save pack changes."""
        enabled = []
        for pack_name, checkbox in self.pack_checkboxes.items():
            if checkbox.isChecked():
                enabled.append(pack_name)
        self.data["enabled_packs"] = enabled
        save_mappings(self.data)

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

        # Check if already exists
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text().lower() == spoken.lower():
                QMessageBox.warning(self, "Warning",
                    "This spoken phrase already exists. Use Update to modify.")
                return

        # Add new row
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
            self.strip_ws_before_checkbox.setChecked(False)
            self.strip_ws_after_checkbox.setChecked(False)
            self._save_mappings()

    def on_wildcard_mode_change(self, text):
        """Handle wildcard mode dropdown change."""
        mode_map = {"None": "none", "SQL-92": "sql92"}
        self.data["wildcard_mode"] = mode_map.get(text, "sql92")
        save_mappings(self.data)


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
