"""
ui/activity_monitor_window.py
------------------------------
PHASE 3 REDESIGN: the live "ACTIVITY MONITOR" screen, rebuilt around the
new foreground-window model (one current app, not a list of many) with a
more visual, colour-coded professional layout:
  - a status card (green = active, orange/red = unavailable)
  - a "Current Application" card showing what's in front right now, with
    a live-ticking duration
  - "Today's Application Usage" - a ranked list with simple bar indicators
  - "Live Activity" - a running feed of switches, colour-coded by event type

This window does NOT create its own ActivityMonitor - it's handed the one
DashboardWindow already created and started, so there's only ever one
poller per login.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QProgressBar
)
from PySide6.QtGui import QFont
from PySide6.QtCore import QTimer, Qt
from datetime import datetime

import activity_monitor as activity_monitor_module
from ui.diagnostics_window import DiagnosticsWindow
from ui.activity_history_window import ActivityHistoryWindow
import database

COLOR_GREEN = "#2e9e5b"
COLOR_BLUE = "#3a7bd5"
COLOR_ORANGE = "#d97b1f"
COLOR_RED = "#c0392b"
COLOR_GRAY = "#8a8a8a"


def _card(bg="#2a2a2e", border=None):
    frame = QFrame()
    style = f"QFrame {{ background-color: {bg}; border-radius: 8px; padding: 4px; }}"
    if border:
        style = f"QFrame {{ background-color: {bg}; border-radius: 8px; padding: 4px; border: 1px solid {border}; }}"
    frame.setStyleSheet(style)
    return frame


class ActivityMonitorWindow(QWidget):
    def __init__(self, monitor, user):
        super().__init__()
        self.monitor = monitor
        self.user = user
        self.diagnostics_window = None
        self.history_window = None

        self.setWindowTitle("Thalapathi Studio - Activity Monitor")
        self.setMinimumSize(600, 700)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        self.setLayout(layout)

        title = QLabel("ACTIVITY MONITOR")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        layout.addWidget(title)

        # ---- Status card ----
        available = self.monitor.watcher.available
        status_color = COLOR_GREEN if available else COLOR_ORANGE
        self.status_card = _card(border=status_color)
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(14, 10, 14, 10)
        self.status_card.setLayout(status_layout)

        status_text = "\u25CF MONITORING ACTIVE" if available else "\u25CF " + self.monitor.watcher.diagnostic_status()
        self.status_label = QLabel(status_text)
        self.status_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.status_label.setStyleSheet(f"color: {status_color};")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel(f"Current Worker: {self.user['name']}"))
        info_row.addStretch()
        info_row.addWidget(QLabel(f"Computer: {self.monitor.computer_name or 'unknown'}"))
        status_layout.addLayout(info_row)
        layout.addWidget(self.status_card)

        # ---- Current Application card ----
        self.current_card = _card(border=COLOR_BLUE)
        current_layout = QVBoxLayout()
        current_layout.setContentsMargins(14, 12, 14, 12)
        self.current_card.setLayout(current_layout)

        current_header = QLabel("CURRENT APPLICATION")
        current_header.setFont(QFont("Segoe UI", 9, QFont.Bold))
        current_header.setStyleSheet(f"color: {COLOR_BLUE};")
        current_layout.addWidget(current_header)

        self.current_app_label = QLabel("—")
        self.current_app_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        current_layout.addWidget(self.current_app_label)

        detail_row = QHBoxLayout()
        self.started_label = QLabel("")
        self.started_label.setStyleSheet("color: gray;")
        detail_row.addWidget(self.started_label)
        detail_row.addStretch()
        self.duration_label = QLabel("")
        self.duration_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.duration_label.setStyleSheet(f"color: {COLOR_GREEN};")
        detail_row.addWidget(self.duration_label)
        current_layout.addLayout(detail_row)

        layout.addWidget(self.current_card)

        # ---- Today's Application Usage ----
        layout.addWidget(self._section_label("TODAY'S APPLICATION USAGE"))
        self.usage_container = QVBoxLayout()
        self.usage_container.setSpacing(6)
        usage_wrap = QFrame()
        usage_wrap.setLayout(self.usage_container)
        layout.addWidget(usage_wrap)

        # ---- Live Activity feed ----
        layout.addWidget(self._section_label("LIVE ACTIVITY"))
        self.recent_list = QListWidget()
        layout.addWidget(self.recent_list)

        # ---- Buttons ----
        button_row = QHBoxLayout()
        test_btn = QPushButton("\U0001F9EA Insert Test Event")
        test_btn.setToolTip(
            "Adds a fake activity that auto-closes after 5 seconds, purely to verify "
            "the recording + display pipeline. This is NOT real detection."
        )
        test_btn.clicked.connect(self.handle_test_event)
        button_row.addWidget(test_btn)

        history_btn = QPushButton("View Full History")
        history_btn.clicked.connect(self.open_history)
        button_row.addWidget(history_btn)

        if self.user["role"] == "admin":
            diag_btn = QPushButton("View Diagnostics")
            diag_btn.clicked.connect(self.open_diagnostics)
            button_row.addWidget(diag_btn)

        button_row.addStretch()
        layout.addLayout(button_row)

        # ---- Wiring ----
        self.monitor.activity_started.connect(self._on_started)
        self.monitor.activity_stopped.connect(self._on_stopped)

        self.tick_timer = QTimer()
        self.tick_timer.timeout.connect(self._refresh_current)
        self.tick_timer.start(1000)

        self._refresh_current()
        self._refresh_usage()

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        return lbl

    def _on_started(self, app_name):
        ts = datetime.now().strftime("%I:%M:%S %p")
        item = QListWidgetItem(f"\u25CF {ts}  —  {app_name}  OPENED")
        item.setForeground(Qt.green)
        self.recent_list.insertItem(0, item)
        self._refresh_current()

    def _on_stopped(self, app_name, duration_seconds):
        ts = datetime.now().strftime("%I:%M:%S %p")
        item = QListWidgetItem(f"\u25CB {ts}  —  {app_name}  CLOSED ({self._format_duration(duration_seconds)})")
        item.setForeground(Qt.gray)
        self.recent_list.insertItem(0, item)
        self._refresh_current()
        self._refresh_usage()

    def _refresh_current(self):
        current = self.monitor.current_app()
        if current is None:
            self.current_app_label.setText("(nothing tracked right now)")
            self.current_app_label.setStyleSheet("color: gray;")
            self.started_label.setText("")
            self.duration_label.setText("")
            return
        friendly, start_time, _title = current
        self.current_app_label.setStyleSheet("")
        self.current_app_label.setText(friendly)
        self.started_label.setText(f"Started: {start_time.strftime('%I:%M:%S %p')}")
        duration = int((datetime.now() - start_time).total_seconds())
        self.duration_label.setText(self._format_duration(duration))

    def _refresh_usage(self):
        while self.usage_container.count():
            item = self.usage_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rows = database.get_today_app_usage_totals(worker_id=self.user["id"])
        if not rows:
            empty = QLabel("No completed activity yet today.")
            empty.setStyleSheet("color: gray;")
            self.usage_container.addWidget(empty)
            return

        max_seconds = max(r["total_seconds"] for r in rows) or 1
        for r in rows[:8]:
            row_widget = QWidget()
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_widget.setLayout(row_layout)

            name_label = QLabel(r["app_name"])
            name_label.setMinimumWidth(140)
            row_layout.addWidget(name_label)

            bar = QProgressBar()
            bar.setMaximum(max_seconds)
            bar.setValue(min(r["total_seconds"], max_seconds))
            bar.setTextVisible(False)
            bar.setFixedHeight(14)
            bar.setStyleSheet(
                f"QProgressBar {{ background-color: #3a3a3e; border-radius: 6px; }}"
                f"QProgressBar::chunk {{ background-color: {COLOR_BLUE}; border-radius: 6px; }}"
            )
            row_layout.addWidget(bar, stretch=1)

            time_label = QLabel(self._format_duration(r["total_seconds"]))
            time_label.setMinimumWidth(70)
            time_label.setAlignment(Qt.AlignRight)
            row_layout.addWidget(time_label)

            self.usage_container.addWidget(row_widget)

    @staticmethod
    def _format_duration(seconds):
        seconds = int(seconds)
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {secs}s"
        return f"{secs}s"

    def handle_test_event(self):
        self.monitor.insert_test_event()
        QMessageBox.information(
            self, "Test event added",
            "A synthetic 'Test Event' has been logged. It will automatically "
            "close itself after 5 seconds - watch Current Application and "
            "Live Activity above.\n\n"
            "This only checks that recording and display work - it does not "
            "test real Windows detection."
        )

    def open_diagnostics(self):
        if self.diagnostics_window is None or not self.diagnostics_window.isVisible():
            self.diagnostics_window = DiagnosticsWindow(self.monitor)
        self.diagnostics_window.show()
        self.diagnostics_window.raise_()
        self.diagnostics_window.activateWindow()

    def open_history(self):
        if self.history_window is None or not self.history_window.isVisible():
            self.history_window = ActivityHistoryWindow(self.user)
        self.history_window.show()
        self.history_window.raise_()
        self.history_window.activateWindow()

    def closeEvent(self, event):
        self.tick_timer.stop()
        if self.diagnostics_window is not None:
            self.diagnostics_window.close()
        if self.history_window is not None:
            self.history_window.close()
        event.accept()
