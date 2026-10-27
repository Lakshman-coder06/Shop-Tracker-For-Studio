"""
ui/change_pin_window.py
--------------------------
Lets the currently logged-in user (worker or admin) change their own PIN.
Requires the current PIN to be entered correctly first - this is not
reachable by anyone else, since it always operates on self.user["id"].
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QPushButton, QLineEdit, QMessageBox
)
from PySide6.QtGui import QFont

import database


class ChangePinWindow(QWidget):
    def __init__(self, user, on_changed=None, forced=False):
        super().__init__()
        self.user = user
        self.on_changed = on_changed
        self.forced = forced  # True when this is a required change (e.g. after an admin reset)

        self.setWindowTitle("Thalapathi Studio - Change PIN")
        self.setMinimumSize(380, 320)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self.setLayout(layout)

        title = QLabel("CHANGE PIN")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        if forced:
            note = QLabel("Your PIN was reset by Admin. Please set a new PIN to continue.")
            note.setStyleSheet("color: #d97b1f; font-weight: bold;")
            note.setWordWrap(True)
            layout.addWidget(note)

        form = QFormLayout()
        form.setSpacing(10)

        self.current_pin_input = QLineEdit()
        self.current_pin_input.setEchoMode(QLineEdit.Password)
        form.addRow("Current PIN:", self.current_pin_input)

        self.new_pin_input = QLineEdit()
        self.new_pin_input.setEchoMode(QLineEdit.Password)
        form.addRow("New PIN:", self.new_pin_input)

        self.confirm_pin_input = QLineEdit()
        self.confirm_pin_input.setEchoMode(QLineEdit.Password)
        self.confirm_pin_input.returnPressed.connect(self.handle_save)
        form.addRow("Confirm New PIN:", self.confirm_pin_input)

        layout.addLayout(form)

        save_btn = QPushButton("SAVE NEW PIN")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self.handle_save)
        layout.addWidget(save_btn)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        layout.addStretch()

    def handle_save(self):
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

        if self.on_changed:
            self.on_changed()

    def _show_error(self, text):
        self.message_label.setStyleSheet("color: #c0392b; font-weight: bold;")
        self.message_label.setText(text)
