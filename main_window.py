"""
ui/main_window.py
--------------------
PART 2 REDESIGN: the premium single-window shell - header at the top,
sidebar navigation on the left, content area on the right. Replaces the
old design where every screen was its own floating popup window opened
from a flat grid of buttons.

Each page is one of the existing, already-tested screen classes,
embedded into a QStackedWidget instead of being shown as a separate
top-level window. This owns the ONE ActivityMonitor for the whole
session (previously owned by DashboardWindow) and the worker session
lifecycle (start/end, cleanup on close).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from datetime import datetime

import database
import app_settings
import theme
from activity_monitor import ActivityMonitor
from ui.dashboard_window import DashboardPage
from ui.job_entry_window import JobEntryWindow
from ui.transactions_window import TransactionsWindow
from ui.expense_entry_window import ExpenseEntryWindow
from ui.pending_records_window import PendingRecordsWindow
from ui.activity_monitor_window import ActivityMonitorWindow
from ui.daily_closing_window import DailyClosingWindow
from ui.enquiries_window import EnquiriesWindow
from ui.todo_window import TodoWindow
from ui.settings_window import SettingsWindow
from ui.worker_management_window import WorkerManagementWindow
from ui.service_management_window import ServiceManagementWindow
from ui.audit_log_window import AuditLogWindow

# (label, icon, page_key, admin_only)
NAV_ITEMS = [
    ("Dashboard", "\U0001F3E0", "dashboard", False),
    ("New Job", "\u2795", "new_job", False),
    ("Transactions", "\U0001F4CB", "transactions", False),
    ("Expenses", "\U0001F4B5", "expenses", False),
    ("Pending Records", "\u23F3", "pending", False),
    ("Activity", "\U0001F4CA", "activity", False),
    ("Daily Closing", "\U0001F9FE", "closing", False),
    ("Enquiries", "\u2753", "enquiries", False),
    ("To-Do", "\u2705", "todo", False),
    ("Worker Management", "\U0001F465", "workers", True),
    ("Services Management", "\U0001F6E0", "services", True),
    ("Audit Log", "\U0001F4DC", "audit", True),
    ("Settings", "\u2699", "settings", False),
]


class MainWindow(QWidget):
    def __init__(self, user, session_id, on_logout, on_theme_changed=None):
        super().__init__()
        self.user = user
        self.is_admin = user["role"] == "admin"
        self.session_id = session_id
        self.on_logout = on_logout
        self.on_theme_changed = on_theme_changed
        self.session_start = datetime.now()
        self._cleaned_up = False
        self._pages = {}
        self._nav_buttons = {}

        self.setWindowTitle("Thalapathi Studio \U0001F4BB")
        self.resize(1150, 760)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.setLayout(outer)

        self._build_header(outer)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, stretch=1)

        self._build_sidebar(body)

        self.stack = QStackedWidget()
        content_wrap = QFrame()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_wrap.setLayout(content_layout)
        content_layout.addWidget(self.stack)
        body.addWidget(content_wrap, stretch=1)

        # ---- Single ActivityMonitor for the whole session ----
        # Created here (pages below need the object to exist), but NOT
        # started yet: on a real Windows machine, .start() polls the
        # foreground window immediately and can emit activity_started/
        # activity_stopped synchronously, before _build_pages() has put
        # anything into self._pages. Starting it only after the pages
        # exist and the dashboard is showing is what actually prevents
        # that race, rather than just hoping it doesn't happen.
        self.activity_monitor = ActivityMonitor(self.user["id"])
        self.activity_monitor.activity_started.connect(self._on_activity_event)
        self.activity_monitor.activity_stopped.connect(self._on_activity_event)

        self._build_pages()
        self.show_page("dashboard")

        self.activity_monitor.start()

        # Keep the Dashboard's "current activity" ticking even when it's
        # not the visible page, so it's fresh the moment you switch back.
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_current_page_if_dashboard)
        self._refresh_timer.start(4000)

    # ---- Header ----

    def _build_header(self, outer):
        header = QFrame()
        header.setObjectName("headerFrame")
        header.setFixedHeight(60)
        row = QHBoxLayout()
        row.setContentsMargins(20, 0, 20, 0)
        header.setLayout(row)

        logo = QLabel("\U0001F4BB THALAPATHI STUDIO")
        logo.setFont(QFont("Segoe UI", 13, QFont.Bold))
        row.addWidget(logo)
        row.addStretch()

        self.datetime_label = QLabel(datetime.now().strftime("%A, %d %B %Y — %I:%M %p"))
        row.addWidget(self.datetime_label)
        row.addSpacing(20)

        # Connection light: green = talking to the shop server, red = can't reach it.
        self.conn_label = QLabel("\u25CF Connected")
        self.conn_label.setToolTip("Connection to the shop server")
        row.addWidget(self.conn_label)
        row.addSpacing(16)

        self.who_label = QLabel(f"{self.user['name']} ({self.user['role'].capitalize()})")
        row.addWidget(self.who_label)
        row.addSpacing(12)

        logout_btn = QPushButton("Log out")
        logout_btn.clicked.connect(self.handle_logout)
        row.addWidget(logout_btn)

        outer.addWidget(header)
        self.refresh_theme_colors()

        self._clock_timer = QTimer()
        self._clock_timer.timeout.connect(
            lambda: self.datetime_label.setText(datetime.now().strftime("%A, %d %B %Y — %I:%M %p"))
        )
        self._clock_timer.start(30000)

        self._conn_timer = QTimer()
        self._conn_timer.timeout.connect(self._update_connection_light)
        self._conn_timer.start(5000)
        self._update_connection_light()

    def _update_connection_light(self):
        online = database.ping()
        color = "#2e9e5b" if online else "#c0392b"
        text = "\u25CF Connected" if online else "\u25CF Offline - reconnecting..."
        self.conn_label.setText(text)
        self.conn_label.setStyleSheet(
            f"QLabel {{ color: {color}; font-weight: bold; background: transparent; border: none; }}"
        )

    def refresh_theme_colors(self):
        """The header's two labels set colour directly (bypassing the
        global stylesheet, same as the login screen) - this re-applies
        them for whichever theme (Light/Dark/System) is active right now.
        Called once when the header is built, and again live whenever the
        theme is changed from Settings."""
        resolved = app_settings.resolve_theme()
        colors = theme.colors_for(resolved)
        self.datetime_label.setStyleSheet(
            f"QLabel {{ color: {colors['text_secondary']}; background: transparent; border: none; }}"
        )
        self.who_label.setStyleSheet(
            f"QLabel {{ font-weight: bold; color: {colors['text_primary']}; background: transparent; border: none; }}"
        )

    # ---- Sidebar ----

    def _build_sidebar(self, body):
        sidebar = QFrame()
        sidebar.setObjectName("sidebarFrame")
        sidebar.setFixedWidth(250)
        col = QVBoxLayout()
        col.setContentsMargins(10, 16, 10, 16)
        col.setSpacing(4)
        sidebar.setLayout(col)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        for label, icon, key, admin_only in NAV_ITEMS:
            if admin_only and not self.is_admin:
                continue
            btn = QPushButton(f"  {icon}   {label}")
            btn.setObjectName("sidebarButton")
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda checked=False, k=key: self.show_page(k))
            col.addWidget(btn)
            self.nav_group.addButton(btn)
            self._nav_buttons[key] = btn

        col.addStretch()
        body.addWidget(sidebar)

    # ---- Pages ----

    def _build_pages(self):
        self._pages["dashboard"] = DashboardPage(self.user, self.activity_monitor)
        self._pages["new_job"] = JobEntryWindow(self.user, on_saved=self._on_data_changed)
        self._pages["transactions"] = TransactionsWindow(self.user)
        self._pages["expenses"] = ExpenseEntryWindow(self.user, on_saved=self._on_data_changed)
        self._pages["pending"] = PendingRecordsWindow(self.user, on_saved=self._on_data_changed)
        self._pages["activity"] = ActivityMonitorWindow(self.activity_monitor, self.user)
        self._pages["closing"] = DailyClosingWindow(self.user)
        self._pages["enquiries"] = EnquiriesWindow(self.user)
        self._pages["todo"] = TodoWindow(self.user)
        self._pages["settings"] = SettingsWindow(self.user, on_logout=self.handle_logout, on_theme_changed=self.on_theme_changed)
        if self.is_admin:
            self._pages["workers"] = WorkerManagementWindow(self.user)
            self._pages["services"] = ServiceManagementWindow(self.user)
            self._pages["audit"] = AuditLogWindow()

        for page in self._pages.values():
            self.stack.addWidget(page)

    def show_page(self, key):
        page = self._pages.get(key)
        if page is None:
            return
        if hasattr(page, "refresh"):
            page.refresh()
        self.stack.setCurrentWidget(page)
        btn = self._nav_buttons.get(key)
        if btn is not None:
            btn.setChecked(True)

    def _refresh_current_page_if_dashboard(self):
        dashboard = self._pages.get("dashboard")
        if dashboard is not None and self.stack.currentWidget() is dashboard:
            dashboard.refresh()

    def _on_activity_event(self, *_args):
        """Connected to the activity monitor's signals, which can in
        principle fire before the dashboard page exists (see the ordering
        note in __init__) - dashboard is None in that split second, and
        this simply does nothing that turn, rather than raising."""
        dashboard = self._pages.get("dashboard")
        if dashboard is not None and self.stack.currentWidget() is dashboard:
            dashboard.refresh()

    def _on_data_changed(self):
        """Called by New Job / Expense / Pending Records after a save, so
        every other page showing related numbers stays in sync."""
        self._pages["dashboard"].refresh()
        self._pages["transactions"].refresh()
        self._pages["pending"].refresh()
        self._pages["closing"].refresh()

    # ---- Session lifecycle ----

    def _cleanup(self):
        if self._cleaned_up:
            return
        self._cleaned_up = True
        self._conn_timer.stop()
        # If the server can't be reached right now (or the login already
        # expired), closing must still work - never trap the user in the app.
        try:
            self.activity_monitor.stop()
        except database.ShopServerError:
            pass
        try:
            database.end_worker_session(self.session_id)
        except database.ShopServerError:
            pass
        for page in self._pages.values():
            page.close()

    def closeEvent(self, event):
        self._cleanup()
        event.accept()

    def handle_logout(self):
        self.close()  # triggers closeEvent -> _cleanup()
        self.on_logout()
