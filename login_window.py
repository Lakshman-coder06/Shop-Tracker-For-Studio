"""
ui/login_window.py
-------------------
PART 1 REDESIGN: a premium, private login screen. The previous version
showed a button for every worker, which is a real privacy problem in a
shop where anyone walking past the screen could see the full staff list
and pick "Admin." This version shows nothing but a name field and a PIN
field - the backend figures out who you are and whether you're a worker
or Admin, exactly like any real login screen.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QCheckBox, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

import database
import app_settings
import theme
from ui.server_settings_dialog import ServerSettingsDialog


class LoginWindow(QWidget):
    def __init__(self, on_login_success):
        """on_login_success: called with the logged-in user's database row
        once name+PIN are verified correctly."""
        super().__init__()
        self.on_login_success = on_login_success

        # Reads whichever theme (Light/Dark/System) is currently active, so
        # this screen's few colours that live outside the global
        # stylesheet (background gradient, card, shadow, text) match it -
        # same layout either way, only the colour values change.
        resolved = app_settings.resolve_theme()
        c = theme.colors_for(resolved)
        is_dark = resolved == "dark"
        accent_hover = "#4fd0a1" if is_dark else "#278a69"
        shadow_color = QColor(0, 0, 0, 110) if is_dark else QColor(31, 111, 87, 60)

        self.setWindowTitle("Thalapathi Studio - Login")
        self.setMinimumSize(460, 520)
        self.setStyleSheet(
            f"LoginWindow {{ background: qlineargradient("
            f"x1:0, y1:0, x2:0, y2:1, stop:0 {c['table_header_bg']}, stop:1 {c['app_bg']}); }}"
        )

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        self.setLayout(outer)
        outer.addStretch()

        center_row = QHBoxLayout()
        outer.addLayout(center_row)
        center_row.addStretch()

        card = QFrame()
        card.setFixedWidth(360)
        card.setStyleSheet(
            f"QFrame {{ background-color: {c['card_bg']}; border-radius: 16px; border: 1px solid {c['card_border']}; }}"
        )
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(36)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(shadow_color)
        card.setGraphicsEffect(shadow)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(36, 40, 36, 36)
        card_layout.setSpacing(6)
        card.setLayout(card_layout)
        center_row.addWidget(card)
        center_row.addStretch()

        logo = QLabel("\U0001F4BB")  # matches the laptop/computer glyph in the app's chosen branding
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("QLabel { font-size: 34px; background: transparent; border: none; }")
        card_layout.addWidget(logo)

        title = QLabel("THALAPATHI STUDIO \U0001F4BB")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"QLabel {{ color: {c['sidebar_active_text']}; background: transparent; border: none; }}")
        card_layout.addWidget(title)

        subtitle = QLabel("Shop Work & Collection Tracker")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"QLabel {{ color: {c['text_secondary']}; background: transparent; border: none; }}")
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(24)

        name_label = QLabel("Username / Worker Name")
        name_label.setStyleSheet(f"QLabel {{ color: {c['text_secondary']}; background: transparent; border: none; }}")
        card_layout.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Worker 1")
        self.name_input.setMinimumHeight(38)
        self.name_input.returnPressed.connect(lambda: self.pin_input.setFocus())
        card_layout.addWidget(self.name_input)

        card_layout.addSpacing(10)

        pin_label = QLabel("Password / PIN")
        pin_label.setStyleSheet(f"QLabel {{ color: {c['text_secondary']}; background: transparent; border: none; }}")
        card_layout.addWidget(pin_label)
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("Enter your PIN")
        self.pin_input.setMaxLength(8)
        self.pin_input.setMinimumHeight(38)
        self.pin_input.returnPressed.connect(self.attempt_login)
        card_layout.addWidget(self.pin_input)

        show_row = QHBoxLayout()
        self.show_pin_checkbox = QCheckBox("Show password")
        self.show_pin_checkbox.toggled.connect(self._toggle_pin_visibility)
        show_row.addWidget(self.show_pin_checkbox)
        show_row.addStretch()
        card_layout.addLayout(show_row)

        card_layout.addSpacing(14)

        self.login_button = QPushButton("LOGIN")
        self.login_button.setMinimumHeight(44)
        self.login_button.setStyleSheet(
            f"QPushButton {{ background-color: {c['accent']}; color: white; font-weight: bold; border: none; border-radius: 8px; }}"
            f"QPushButton:hover {{ background-color: {accent_hover}; }}"
        )
        self.login_button.clicked.connect(self.attempt_login)
        card_layout.addWidget(self.login_button)

        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("QLabel { color: #c0392b; font-weight: bold; background: transparent; border: none; }")
        card_layout.addWidget(self.message_label)

        # Small, quiet link showing which shop server this PC talks to. Always
        # reachable from here so a wrong address can be fixed without logging in.
        self.server_btn = QPushButton("")
        self.server_btn.setFlat(True)
        self.server_btn.setCursor(Qt.PointingHandCursor)
        self.server_btn.setStyleSheet(
            f"QPushButton {{ color: {c['text_secondary']}; background: transparent; border: none; font-size: 11px; }}"
            f"QPushButton:hover {{ color: {c['accent']}; text-decoration: underline; }}"
        )
        self.server_btn.clicked.connect(self._change_server)
        card_layout.addWidget(self.server_btn)
        self._refresh_server_label()

        outer.addStretch()
        self.name_input.setFocus()

    def _refresh_server_label(self):
        url = database.get_server_url()
        self.server_btn.setText(f"Server: {url}  \u2022  change" if url else "Server not set  \u2022  set address")

    def _change_server(self):
        dlg = ServerSettingsDialog(self)
        if dlg.exec():
            self.message_label.setText("")
        self._refresh_server_label()

    def _toggle_pin_visibility(self, checked):
        self.pin_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)

    def attempt_login(self):
        name = self.name_input.text().strip()
        pin = self.pin_input.text().strip()

        if not name or not pin:
            self._show_error("Please enter both your name and PIN.")
            return

        try:
            user = database.authenticate(name, pin)
        except database.LoginLockedError as e:
            self._show_error(str(e))
            self.pin_input.clear()
            return
        except database.ServerUnavailableError as e:
            # Not a wrong-PIN problem - the shop server can't be reached.
            self._show_error(str(e))
            return
        if user is None:
            # Deliberately the same message whether the name is wrong, the
            # PIN is wrong, or the account is inactive - never reveal which.
            self._show_error("Invalid username or PIN.")
            self.pin_input.clear()
            self.pin_input.setFocus()
            return

        self.message_label.setText("")
        self.on_login_success(user)

    def _show_error(self, text):
        self.message_label.setStyleSheet("QLabel { color: #c0392b; font-weight: bold; background: transparent; border: none; }")
        self.message_label.setText(text)
