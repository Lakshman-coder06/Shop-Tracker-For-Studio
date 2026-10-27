"""
ui/diagnostics_window.py
--------------------------
Admin-only screen for troubleshooting the activity monitor - e.g. if an
application doesn't seem to be getting detected on a particular shop PC.
Refreshes automatically every 2 seconds - no manual refresh needed.

This window does not own an ActivityMonitor - it reads from the one
DashboardWindow already created and started.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtGui import QFont
from PySide6.QtCore import QTimer


class DiagnosticsWindow(QWidget):
    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor

        self.setWindowTitle("Thalapathi Studio - Monitor Diagnostics")
        self.setMinimumSize(480, 440)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        self.setLayout(layout)

        title = QLabel("MONITOR DIAGNOSTICS")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        self.rows = {}
        for key, label in [
            ("monitoring", "Monitoring"),
            ("mechanism", "Detection method"),
            ("last_scan", "Last scan"),
            ("current_app", "Current foreground application"),
            ("worker", "Current worker"),
            ("computer", "Computer"),
            ("db", "Database"),
            ("last_saved", "Last activity saved"),
        ]:
            row = QFrame()
            row_layout = QVBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 4)
            row_layout.setSpacing(2)
            row.setLayout(row_layout)
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet("color: gray;")
            value_lbl = QLabel("—")
            value_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
            value_lbl.setWordWrap(True)
            row_layout.addWidget(name_lbl)
            row_layout.addWidget(value_lbl)
            layout.addWidget(row)
            self.rows[key] = value_lbl

        layout.addStretch()

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)
        self.refresh()

    def refresh(self):
        diag = self.monitor.diagnostics()

        self.rows["monitoring"].setText("ACTIVE" if diag["monitoring_active"] else "INACTIVE")
        self.rows["mechanism"].setText(
            f"Foreground-window detection, polling every {diag['poll_interval_seconds']:.0f}s "
            f"({diag['status_text']})"
        )
        self.rows["last_scan"].setText(
            diag["last_scan"].strftime("%I:%M:%S %p") if diag["last_scan"] else "—"
        )
        self.rows["current_app"].setText(diag["current_app"] or "(nothing tracked right now)")
        self.rows["worker"].setText(f"Worker ID {diag['worker_id']}")
        self.rows["computer"].setText(diag["computer_name"] or "unknown")
        self.rows["db"].setText("CONNECTED" if diag["db_connected"] else "ERROR - could not query database")
        self.rows["last_saved"].setText(diag["last_activity_saved"] or "—")

    def closeEvent(self, event):
        self.timer.stop()
        event.accept()
