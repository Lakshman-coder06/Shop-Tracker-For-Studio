"""
ui/server_settings_dialog.py
-------------------------------
"Connect to your shop server" - where each PC is told the address of the
one shared server. Shown automatically the first time the app starts on a
PC, and reachable any time from the small "Server" link on the login
screen (so a wrong address can always be fixed without logging in).
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialogButtonBox
)
from PySide6.QtCore import Qt

import app_settings
import database


class ServerSettingsDialog(QDialog):
    def __init__(self, parent=None, first_run=False):
        super().__init__(parent)
        self.first_run = first_run
        self._unreachable_confirmed_for = None
        self.setWindowTitle("Thalapathi Studio - Connect to shop server")
        self.setMinimumWidth(470)
        self.setModal(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(10)
        self.setLayout(layout)

        title = QLabel("Connect to your shop server")
        title.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; }")
        layout.addWidget(title)

        intro = QLabel(
            "All your PCs share one set of records, kept on the shop server. "
            "Type the server's address below. The person who set up the server "
            "can read it from the server window (it looks like "
            "<b>http://192.168.1.20:8000</b>)."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("e.g. http://192.168.1.20:8000")
        self.url_input.setMinimumHeight(36)
        self.url_input.setText(app_settings.get_server_url())
        self.url_input.returnPressed.connect(self._test)
        self.url_input.textChanged.connect(self._address_edited)
        layout.addWidget(self.url_input)

        test_row = QHBoxLayout()
        self.test_btn = QPushButton("Test connection")
        self.test_btn.clicked.connect(self._test)
        test_row.addWidget(self.test_btn)
        test_row.addStretch()
        layout.addLayout(test_row)

        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        buttons = QDialogButtonBox()
        self.save_btn = buttons.addButton("Save", QDialogButtonBox.AcceptRole)
        self.cancel_btn = buttons.addButton("Quit" if first_run else "Cancel", QDialogButtonBox.RejectRole)
        self.save_btn.clicked.connect(self._save)
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self.url_input.setFocus()

    def _address_edited(self, _text):
        self._unreachable_confirmed_for = None
        self.save_btn.setText("Save")

    def _typed_url(self):
        return app_settings.normalize_server_url(self.url_input.text())

    def _test(self):
        url = self._typed_url()
        if not url:
            self._show(False, "Enter the server address first.")
            return
        self.url_input.setText(url)
        self.test_btn.setEnabled(False)
        self.result_label.setText("Testing...")
        self.result_label.repaint()
        try:
            result = database.check_server(url)
        finally:
            self.test_btn.setEnabled(True)
        self._show(result["ok"], result["message"])
        return result["ok"]

    def _save(self):
        url = self._typed_url()
        if not url:
            self._show(False, "Enter the server address first.")
            return
        # If the address hasn't changed since a failed test, a second click on
        # "Save anyway" is a deliberate choice (e.g. the server PC is simply
        # switched off right now) - respect it.
        if not (self._unreachable_confirmed_for == url):
            result = database.check_server(url)
            if not result["ok"]:
                self._unreachable_confirmed_for = url
                self.save_btn.setText("Save anyway")
                self._show(False, result["message"])
                return
        app_settings.set_server_url(url)
        database.configure(url)
        self.accept()

    def _show(self, ok, text):
        color = "#2e9e5b" if ok else "#c0392b"
        self.result_label.setStyleSheet(f"QLabel {{ color: {color}; font-weight: bold; }}")
        self.result_label.setText(("\u2713 " if ok else "\u2717 ") + text)
