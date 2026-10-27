"""
ui/settings_window.py
------------------------
PART 2 of the correction request: Settings is now the one place for a
logged-in person's own account - their details, changing their own PIN
(Worker AND Admin both use this exact same screen - nothing here is
role-restricted), and logging out. This replaces the old Settings page,
which was just a bare Change PIN form with no account info or logout.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QComboBox
)
from PySide6.QtGui import QFont

import database
import app_settings


class SettingsWindow(QWidget):
    def __init__(self, user, on_logout, on_theme_changed=None):
        super().__init__()
        self.user = user
        self.on_logout = on_logout
        self.on_theme_changed = on_theme_changed

        self.setWindowTitle("Thalapathi Studio - Settings")
        self.setMinimumSize(440, 560)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        self.setLayout(layout)

        title = QLabel("SETTINGS")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        # ---- Account / Worker Details ----
        layout.addWidget(self._section_label("ACCOUNT DETAILS"))
        details_card = QFrame()
        details_layout = QFormLayout()
        details_card.setLayout(details_layout)

        self.name_value = QLabel("—")
        details_layout.addRow("Name:", self.name_value)
        self.username_value = QLabel("—")
        details_layout.addRow("Username:", self.username_value)
        self.role_value = QLabel("—")
        details_layout.addRow("Role:", self.role_value)
        self.status_value = QLabel("—")
        details_layout.addRow("Account Status:", self.status_value)

        layout.addWidget(details_card)

        # ---- Theme ----
        layout.addWidget(self._section_label("THEME"))
        theme_card = QFrame()
        theme_layout = QFormLayout()
        theme_card.setLayout(theme_layout)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("System (Default)", "system")
        current_theme = app_settings.get_theme()
        idx = self.theme_combo.findData(current_theme)
        self.theme_combo.setCurrentIndex(idx if idx >= 0 else self.theme_combo.findData("system"))
        self.theme_combo.currentIndexChanged.connect(self.handle_theme_changed)
        theme_layout.addRow("Appearance:", self.theme_combo)

        layout.addWidget(theme_card)

        # ---- Change PIN (both Worker and Admin use this - not restricted) ----
        layout.addWidget(self._section_label("CHANGE PIN"))
        pin_card = QFrame()
        pin_layout = QFormLayout()
        pin_layout.setSpacing(10)
        pin_card.setLayout(pin_layout)

        self.current_pin_input = QLineEdit()
        self.current_pin_input.setEchoMode(QLineEdit.Password)
        pin_layout.addRow("Current PIN:", self.current_pin_input)

        self.new_pin_input = QLineEdit()
        self.new_pin_input.setEchoMode(QLineEdit.Password)
        pin_layout.addRow("New PIN:", self.new_pin_input)

        self.confirm_pin_input = QLineEdit()
        self.confirm_pin_input.setEchoMode(QLineEdit.Password)
        self.confirm_pin_input.returnPressed.connect(self.handle_change_pin)
        pin_layout.addRow("Confirm New PIN:", self.confirm_pin_input)

        layout.addWidget(pin_card)

        save_pin_btn = QPushButton("SAVE NEW PIN")
        save_pin_btn.setMinimumHeight(40)
        save_pin_btn.clicked.connect(self.handle_change_pin)
        layout.addWidget(save_pin_btn)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        layout.addStretch()

        # ---- Logout ----
        logout_btn = QPushButton("LOG OUT")
        logout_btn.setMinimumHeight(44)
        logout_btn.setStyleSheet(
            "QPushButton { background-color: #c0392b; color: white; font-weight: bold; border: none; }"
            "QPushButton:hover { background-color: #d64535; }"
        )
        logout_btn.clicked.connect(self.handle_logout)
        layout.addWidget(logout_btn)

        self.refresh()

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lbl.setStyleSheet("color: #b8b8bc;")
        return lbl

    def refresh(self):
        """Re-reads account details fresh, in case Admin changed this
        person's status/role/name while their session was already open."""
        fresh = database.get_user_by_id(self.user["id"])
        if fresh is None:
            return
        self.name_value.setText(fresh["name"])
        self.username_value.setText(fresh["name"])  # login uses name as the username
        self.role_value.setText(fresh["role"].capitalize())
        self.status_value.setText(fresh["status"] or "Active")

    def handle_change_pin(self):
        current = self.current_pin_input.text().strip()
        new = self.new_pin_input.text().strip()
        confirm = self.confirm_pin_input.text().strip()

        if not current or not new or not confirm:
            self._show_error("Please fill in all three fields.")
            return
        if len(new) < 4:
            self._show_error("New PIN must be at least 4 digits.")
            return
        if new != confirm:
            self._show_error("New PIN and confirmation do not match.")
            return
        if new == current:
            self._show_error("New PIN must be different from the current PIN.")
            return

        ok = database.change_own_pin(self.user["id"], current, new)
        if not ok:
            self._show_error("Current PIN is incorrect.")
            return

        self.message_label.setStyleSheet("color: #2e9e5b; font-weight: bold;")
        self.message_label.setText("PIN changed successfully.")
        self.current_pin_input.clear()
        self.new_pin_input.clear()
        self.confirm_pin_input.clear()

    def handle_theme_changed(self):
        selected = self.theme_combo.currentData()
        if self.on_theme_changed:
            self.on_theme_changed(selected)  # saves the preference AND applies it live

    def handle_logout(self):
        self.on_logout()

    def _show_error(self, text):
        self.message_label.setStyleSheet("color: #c0392b; font-weight: bold;")
        self.message_label.setText(text)
