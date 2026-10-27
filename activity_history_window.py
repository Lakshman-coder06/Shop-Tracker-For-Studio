"""
ui/activity_history_window.py
-------------------------------
Filterable, sortable history of all recorded activity. Workers can only
see their own history; Admin and Supervisor can see everyone's (matches
the existing role rules - workers must not be able to inspect other
workers' records).

Each stored activity (one row with a start_time and, once it ends, an
end_time) is expanded into up to two table rows here - a "Started" row
and a "Closed" row - so the table reads as a plain event timeline.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
)
from PySide6.QtGui import QFont
from datetime import datetime

import database


class ActivityHistoryWindow(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.is_admin_or_supervisor = user["role"] in ("admin", "supervisor")

        self.setWindowTitle("Thalapathi Studio - Activity History")
        self.setMinimumSize(780, 580)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        self.setLayout(layout)

        title = QLabel("ACTIVITY HISTORY")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        # ---- Filters ----
        filter_row = QHBoxLayout()

        filter_row.addWidget(QLabel("Date:"))
        self.date_filter = QComboBox()
        self.date_filter.addItems(["Today", "Yesterday", "Last 7 days", "All"])
        self.date_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.date_filter)

        filter_row.addWidget(QLabel("Worker:"))
        self.worker_filter = QComboBox()
        if self.is_admin_or_supervisor:
            self.worker_filter.addItem("All Workers", None)
            for w in database.get_active_workers():
                self.worker_filter.addItem(w["name"], w["id"])
        else:
            self.worker_filter.addItem(self.user["name"], self.user["id"])
            self.worker_filter.setEnabled(False)
        self.worker_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.worker_filter)

        filter_row.addWidget(QLabel("Application:"))
        self.app_filter = QComboBox()
        self.app_filter.addItem("All Applications", None)
        for name in database.get_distinct_activity_apps():
            self.app_filter.addItem(name, name)
        self.app_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.app_filter)

        filter_row.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Currently Open", "Closed"])
        self.status_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.status_filter)

        layout.addLayout(filter_row)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter by application name...")
        self.search_box.textChanged.connect(self.refresh)
        search_row.addWidget(self.search_box)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        search_row.addWidget(refresh_btn)
        layout.addLayout(search_row)

        # ---- Table ----
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Time", "Worker", "Application", "Event", "Duration"])
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.cellDoubleClicked.connect(self.show_details)
        layout.addWidget(self.table)

        hint = QLabel("Double-click a row for full details. Click a column header to sort.")
        hint.setStyleSheet("color: gray;")
        layout.addWidget(hint)

        self._row_activity_ids = []  # parallel list: table row index -> source activity id
        self.refresh()

    def refresh(self):
        date_map = {"Today": "today", "Yesterday": "yesterday", "Last 7 days": "week", "All": None}
        date_filter = date_map[self.date_filter.currentText()]
        worker_id = self.worker_filter.currentData()
        app_name = self.app_filter.currentData()
        status_map = {"All": None, "Currently Open": "open", "Closed": "closed"}
        status_filter = status_map[self.status_filter.currentText()]
        search_text = self.search_box.text().strip().lower()

        rows = database.get_activity_history(
            date_filter=date_filter, worker_id=worker_id,
            app_name=app_name, status_filter=status_filter,
        )

        if search_text:
            rows = [r for r in rows if search_text in r["app_name"].lower()]

        # Expand each stored activity into its Started (and, if applicable, Closed) event rows
        display_rows = []
        for r in rows:
            start_dt = datetime.fromisoformat(r["start_time"])
            display_rows.append((start_dt, r["worker_name"], r["app_name"], "Started", "—", r["id"]))
            if r["end_time"]:
                end_dt = datetime.fromisoformat(r["end_time"])
                dur = r["duration_seconds"] or 0
                display_rows.append((end_dt, r["worker_name"], r["app_name"], "Closed", f"{dur} sec", r["id"]))

        display_rows.sort(key=lambda x: x[0], reverse=True)

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(display_rows))
        self._row_activity_ids = []
        for i, (ts, worker_name, app_name_, event, duration_text, activity_id) in enumerate(display_rows):
            self.table.setItem(i, 0, QTableWidgetItem(ts.strftime("%I:%M:%S %p")))
            self.table.setItem(i, 1, QTableWidgetItem(worker_name))
            self.table.setItem(i, 2, QTableWidgetItem(app_name_))
            self.table.setItem(i, 3, QTableWidgetItem(event))
            self.table.setItem(i, 4, QTableWidgetItem(duration_text))
            self._row_activity_ids.append(activity_id)
        self.table.setSortingEnabled(True)

    def show_details(self, row, _col):
        if row < 0 or row >= len(self._row_activity_ids):
            return
        activity_id = self._row_activity_ids[row]
        r = database.get_activity_by_id(activity_id)
        if r is None:
            return

        start_dt = datetime.fromisoformat(r["start_time"])
        end_text = "Still open"
        duration_text = "—"
        if r["end_time"]:
            end_dt = datetime.fromisoformat(r["end_time"])
            end_text = end_dt.strftime("%I:%M:%S %p")
            mins, secs = divmod(r["duration_seconds"] or 0, 60)
            duration_text = f"{mins}m {secs}s" if mins else f"{secs}s"

        details = (
            f"Worker: {r['worker_name']}\n"
            f"Application: {r['app_name']}\n"
            f"Process: {r['process_name'] or 'n/a'}\n"
            f"Window title: {r['window_title'] or 'n/a'}\n\n"
            f"Started: {start_dt.strftime('%I:%M:%S %p')}\n"
            f"Closed: {end_text}\n"
            f"Duration: {duration_text}\n\n"
            f"Computer: {r['computer_name'] or 'n/a'}\n"
            f"Date: {start_dt.strftime('%d %B %Y')}"
        )
        QMessageBox.information(self, f"Activity #{r['id']}", details)
