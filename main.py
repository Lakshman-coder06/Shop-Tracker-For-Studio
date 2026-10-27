"""
main.py
--------
Entry point for Thalapathi Studio (ShopTracker).

Run this file to start the application:
    python main.py
    
NETWORK VERSION: the app no longer keeps its own private database. It
connects to the shared shop server (see the ShopTrackerServer folder), so
every PC - workers and Admin - sees the same records. The first time it
starts on a PC it asks for the server's address.
"""

import os
import sys
import time

from PySide6.QtWidgets import QApplication, QMessageBox, QDialog
from PySide6.QtCore import QTimer

import database
import app_settings
from theme import qss_for
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from ui.change_pin_window import ChangePinWindow
from ui.server_settings_dialog import ServerSettingsDialog


class App:
    def __init__(self):
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setStyle("Fusion")  # a consistent base style across Windows versions
        self.login_window = None
        self.dashboard = None  # the MainWindow shell, once logged in
        self.forced_pin_window = None
        self._pending_user = None
        self._last_unreachable_popup = 0.0
        self._popup_open = False
        self.apply_theme()  # loads the saved Light/Dark/System preference (System by default)
        self.qt_app.aboutToQuit.connect(self._on_quit)
        self._install_error_handler()
        self._connect_to_server()
        self.show_login()

    # ---- Server connection ----

    def _connect_to_server(self):
        """Tells the app which shop server to use. An environment variable
        (SHOPTRACKER_SERVER) wins if set - handy for IT-style setups and
        testing; otherwise the address saved on this PC; otherwise ask."""
        url = os.environ.get("SHOPTRACKER_SERVER") or app_settings.get_server_url()
        if not url:
            dlg = ServerSettingsDialog(first_run=True)
            if dlg.exec() != QDialog.Accepted:
                sys.exit(0)
            url = app_settings.get_server_url()
        database.configure(app_settings.normalize_server_url(url))

    # ---- Friendly handling of network problems ----

    def _install_error_handler(self):
        """Any server problem that happens inside a button click or a timer
        lands here and becomes a clear message - instead of a silent failure
        or a crash. Real programming errors still go to the normal handler."""
        previous_hook = sys.excepthook

        def hook(exc_type, exc, tb):
            if issubclass(exc_type, database.AuthExpiredError):
                QTimer.singleShot(0, self.session_expired)
                return
            if issubclass(exc_type, database.ServerUnavailableError):
                # Background refreshes can fail every few seconds while the
                # connection is down - only nag once in a while.
                if time.monotonic() - self._last_unreachable_popup > 20:
                    self._popup(
                        "Can't reach the shop server",
                        f"{exc}\n\nWhatever you were just doing was NOT saved. "
                        "The app will reconnect by itself once the connection is back.",
                    )
                    self._last_unreachable_popup = time.monotonic()
                return
            if issubclass(exc_type, database.ShopServerError):
                self._popup("Thalapathi Studio", str(exc))
                return
            previous_hook(exc_type, exc, tb)

        sys.excepthook = hook

    def _popup(self, title, text):
        if self._popup_open:
            return
        self._popup_open = True
        try:
            QMessageBox.warning(self.dashboard or self.login_window, title, text)
        finally:
            self._popup_open = False

    def session_expired(self):
        if self.dashboard is None:
            return
        self._popup("Please log in again",
                    "Your login has expired (or this account was turned off). Please log in again.")
        self.show_login()

    # ---- Theme ----

    def apply_theme(self, theme_setting: str = None):
        """Applies the given theme setting ('light'/'dark'/'system'), or
        re-reads the saved one if none is given. Called once at startup,
        and again from Settings whenever the person changes their choice -
        that call also saves it, so it's remembered on the next launch."""
        if theme_setting is not None:
            app_settings.set_theme(theme_setting)
        resolved = app_settings.resolve_theme(theme_setting)
        self.qt_app.setStyleSheet(qss_for(resolved))
        if self.dashboard is not None:
            self.dashboard.refresh_theme_colors()

    # ---- Screens ----

    def show_login(self):
        if self.dashboard is not None:
            dashboard, self.dashboard = self.dashboard, None
            dashboard.close()  # triggers its closeEvent -> ends session + stops monitor
        database.logout()
        if self.login_window is not None:
            self.login_window.close()
        self.login_window = LoginWindow(on_login_success=self.show_dashboard)
        self.login_window.show()

    def show_dashboard(self, user):
        if user["must_change_pin"]:
            # A temporary/reset PIN was used - require a change before
            # anything else is reachable.
            self._pending_user = user
            self.login_window.close()
            self.forced_pin_window = ChangePinWindow(
                user, on_changed=self._after_forced_pin_change, forced=True,
            )
            self.forced_pin_window.show()
            return
        self._enter_dashboard(user)

    def _after_forced_pin_change(self):
        self.forced_pin_window.close()
        self.forced_pin_window = None
        self._enter_dashboard(self._pending_user)
        self._pending_user = None

    def _enter_dashboard(self, user):
        if self.login_window is not None:
            self.login_window.close()
        session_id = database.start_worker_session(user["id"])
        self.dashboard = MainWindow(user, session_id, on_logout=self.show_login, on_theme_changed=self.apply_theme)
        self.dashboard.show()

    def _on_quit(self):
        """Safety net: if the app closes in a way that skips the shell's
        own closeEvent (forced close, Alt+F4, etc.), still end the session
        and stop the activity monitor cleanly instead of leaving it open."""
        if self.dashboard is not None:
            self.dashboard._cleanup()

    def run(self):
        sys.exit(self.qt_app.exec())


if __name__ == "__main__":
    app = App()
    app.run()
