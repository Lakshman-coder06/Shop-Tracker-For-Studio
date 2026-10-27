"""
ui/dashboard_window.py
-----------------------
PART 2/3 REDESIGN: DashboardPage is now pure CONTENT - the header,
sidebar navigation, and activity monitor lifecycle all moved up to
ui/main_window.py's MainWindow shell, which embeds this as the default
page in its QStackedWidget instead of DashboardPage being its own
top-level window with its own menu grid.

WORKER sees only their own numbers ("My Jobs Today", "My Sales", ...),
their own recent jobs, their own pending jobs, and their own current
activity - enforced by always passing worker_id=self.user["id"] into
every query, not just by hiding UI elements.

ADMIN sees shop-wide totals, a per-worker performance breakdown, recent
shop-wide activity, pending jobs across everyone, today's Daily Closing/
mismatch status, and To-Do counts.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGridLayout, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QListWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from datetime import datetime

import database

COLOR_GREEN = "#2e9e5b"
COLOR_BLUE = "#3a7bd5"
COLOR_ORANGE = "#d97b1f"
COLOR_RED = "#c0392b"


class DashboardPage(QWidget):
    def __init__(self, user, activity_monitor):
        super().__init__()
        self.user = user
        self.is_admin = user["role"] == "admin"
        self.activity_monitor = activity_monitor

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        self.setLayout(layout)
        self.layout_ = layout

        greeting = QLabel(
            f"GOOD {self._time_of_day()}, {user['name'].upper()}" if not self.is_admin
            else "SHOP OVERVIEW"
        )
        greeting.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(greeting)

        if self.is_admin:
            self._build_admin_dashboard()
        else:
            self._build_worker_dashboard()

    @staticmethod
    def _time_of_day():
        hour = datetime.now().hour
        if hour < 12:
            return "MORNING"
        if hour < 17:
            return "AFTERNOON"
        return "EVENING"

    # ---- Worker dashboard ----

    def _build_worker_dashboard(self):
        summary_frame = QFrame()
        summary_layout = QGridLayout()
        summary_layout.setSpacing(14)
        summary_frame.setLayout(summary_layout)

        self.jobs_value = self._add_summary_cell(summary_layout, 0, 0, "Today's Work")
        self.sales_value = self._add_summary_cell(summary_layout, 0, 1, "My Sales")
        self.cash_value = self._add_summary_cell(summary_layout, 0, 2, "Cash Collected")
        self.upi_value = self._add_summary_cell(summary_layout, 1, 0, "UPI Collected")
        self.expenses_value = self._add_summary_cell(summary_layout, 1, 1, "My Expenses")
        self.drawer_value = self._add_summary_cell(summary_layout, 1, 2, "My Pending Jobs")
        self.layout_.addWidget(summary_frame)

        activity_row = QHBoxLayout()
        activity_row.addWidget(QLabel("My Current Activity:"))
        self.my_current_activity_label = QLabel("—")
        self.my_current_activity_label.setStyleSheet(f"color: {COLOR_BLUE}; font-weight: bold;")
        activity_row.addWidget(self.my_current_activity_label)
        activity_row.addStretch()
        self.layout_.addLayout(activity_row)

        lists_row = QHBoxLayout()

        recent_col = QVBoxLayout()
        recent_col.addWidget(self._section_label("RECENT WORK"))
        self.recent_jobs_list = QListWidget()
        self.recent_jobs_list.setMaximumHeight(160)
        recent_col.addWidget(self.recent_jobs_list)
        lists_row.addLayout(recent_col)

        pending_col = QVBoxLayout()
        pending_col.addWidget(self._section_label("MY PENDING JOBS"))
        self.pending_jobs_list = QListWidget()
        self.pending_jobs_list.setMaximumHeight(160)
        pending_col.addWidget(self.pending_jobs_list)
        lists_row.addLayout(pending_col)

        self.layout_.addLayout(lists_row)
        self.layout_.addStretch()

    # ---- Admin dashboard ----

    def _build_admin_dashboard(self):
        summary_frame = QFrame()
        summary_layout = QGridLayout()
        summary_layout.setSpacing(14)
        summary_frame.setLayout(summary_layout)

        self.jobs_value = self._add_summary_cell(summary_layout, 0, 0, "Today's Jobs")
        self.sales_value = self._add_summary_cell(summary_layout, 0, 1, "Total Sales")
        self.cash_value = self._add_summary_cell(summary_layout, 0, 2, "Cash Collected")
        self.upi_value = self._add_summary_cell(summary_layout, 1, 0, "UPI Collected")
        self.expenses_value = self._add_summary_cell(summary_layout, 1, 1, "Expenses")
        self.drawer_value = self._add_summary_cell(summary_layout, 1, 2, "Expected Drawer")
        self.layout_.addWidget(summary_frame)

        self.layout_.addWidget(self._section_label("WORKER PERFORMANCE TODAY"))
        self.performance_table = QTableWidget()
        self.performance_table.setColumnCount(6)
        self.performance_table.setHorizontalHeaderLabels(
            ["Worker", "Jobs", "Sales", "Cash", "UPI", "Expenses"]
        )
        self.performance_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.performance_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.performance_table.setMaximumHeight(160)
        self.layout_.addWidget(self.performance_table)

        status_row = QHBoxLayout()

        closing_col = QVBoxLayout()
        closing_col.addWidget(self._section_label("DAILY CLOSING STATUS"))
        self.closing_status_label = QLabel("—")
        self.closing_status_label.setWordWrap(True)
        closing_col.addWidget(self.closing_status_label)
        status_row.addLayout(closing_col)

        pending_col = QVBoxLayout()
        pending_col.addWidget(self._section_label("PENDING JOBS (ALL WORKERS)"))
        self.admin_pending_label = QLabel("—")
        pending_col.addWidget(self.admin_pending_label)
        status_row.addLayout(pending_col)

        todo_col = QVBoxLayout()
        todo_col.addWidget(self._section_label("TO-DO"))
        self.todo_summary_label = QLabel("—")
        todo_col.addWidget(self.todo_summary_label)
        status_row.addLayout(todo_col)

        self.layout_.addLayout(status_row)

        self.layout_.addWidget(self._section_label("RECENT ACTIVITY (ALL WORKERS)"))
        self.admin_recent_activity_list = QListWidget()
        self.admin_recent_activity_list.setMaximumHeight(120)
        self.layout_.addWidget(self.admin_recent_activity_list)
        self.layout_.addStretch()

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        return lbl

    def _add_summary_cell(self, grid, row, col, label_text):
        cell = QVBoxLayout()
        cell.setSpacing(2)
        value = QLabel("—")
        value.setFont(QFont("Segoe UI", 18, QFont.Bold))
        value.setAlignment(Qt.AlignCenter)
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #b8b8bc;")
        cell.addWidget(value)
        cell.addWidget(label)
        grid.addLayout(cell, row, col)
        return value

    # ---- Refresh (role-aware) ----

    def refresh(self):
        worker_id = None if self.is_admin else self.user["id"]
        summary = database.get_today_summary(worker_id=worker_id)
        self.jobs_value.setText(str(summary["jobs"]))
        self.sales_value.setText(f"Rs {summary['sales']:.0f}")
        self.cash_value.setText(f"Rs {summary['cash']:.0f}")
        self.upi_value.setText(f"Rs {summary['upi']:.0f}")
        self.expenses_value.setText(f"Rs {summary['expenses']:.0f}")

        if self.is_admin:
            self.drawer_value.setText(f"Rs {summary['expected_drawer']:.0f}")
            self._refresh_admin_extras()
        else:
            pending_count = len(database.get_pending_transactions(worker_id=self.user["id"]))
            self.drawer_value.setText(str(pending_count))
            self._refresh_worker_extras()

    def _refresh_worker_extras(self):
        current = self.activity_monitor.current_app() if self.activity_monitor else None
        self.my_current_activity_label.setText(current[0] if current else "(nothing tracked right now)")

        self.recent_jobs_list.clear()
        for r in database.get_transactions(date_filter="today", worker_id=self.user["id"])[:5]:
            ts = datetime.fromisoformat(r["created_at"])
            self.recent_jobs_list.addItem(
                f"{ts.strftime('%I:%M %p')} — {r['service_name']} — Rs {r['amount']:.0f} ({r['payment_method']})"
            )
        if self.recent_jobs_list.count() == 0:
            self.recent_jobs_list.addItem("No jobs recorded today.")

        self.pending_jobs_list.clear()
        for r in database.get_pending_transactions(worker_id=self.user["id"])[:5]:
            self.pending_jobs_list.addItem(
                f"{r['transaction_code']} — {r['service_name']} — {r['status']} / {r['payment_status']}"
            )
        if self.pending_jobs_list.count() == 0:
            self.pending_jobs_list.addItem("Nothing pending.")

    def _refresh_admin_extras(self):
        perf = database.get_worker_performance_today()
        self.performance_table.setRowCount(len(perf))
        for i, p in enumerate(perf):
            self.performance_table.setItem(i, 0, QTableWidgetItem(p["worker_name"]))
            self.performance_table.setItem(i, 1, QTableWidgetItem(str(p["jobs"])))
            self.performance_table.setItem(i, 2, QTableWidgetItem(f"Rs {p['sales']:.0f}"))
            self.performance_table.setItem(i, 3, QTableWidgetItem(f"Rs {p['cash']:.0f}"))
            self.performance_table.setItem(i, 4, QTableWidgetItem(f"Rs {p['upi']:.0f}"))
            self.performance_table.setItem(i, 5, QTableWidgetItem(f"Rs {p['expenses']:.0f}"))

        closing = database.get_daily_closing()
        if closing is None:
            self.closing_status_label.setText("Not yet done today.")
            self.closing_status_label.setStyleSheet("color: gray;")
        else:
            diff = closing["difference"] or 0
            if abs(diff) < 0.01:
                self.closing_status_label.setText(
                    f"Balanced. Expected Rs {closing['expected_cash']:.0f}, actual Rs {closing['actual_cash']:.0f}."
                )
                self.closing_status_label.setStyleSheet(f"color: {COLOR_GREEN}; font-weight: bold;")
            elif diff < 0:
                self.closing_status_label.setText(f"Short by Rs {abs(diff):.0f}.")
                self.closing_status_label.setStyleSheet(f"color: {COLOR_RED}; font-weight: bold;")
            else:
                self.closing_status_label.setText(f"Over by Rs {diff:.0f}.")
                self.closing_status_label.setStyleSheet(f"color: {COLOR_ORANGE}; font-weight: bold;")

        pending_all = database.get_pending_transactions()
        self.admin_pending_label.setText(f"{len(pending_all)} job(s) pending")
        self.admin_pending_label.setStyleSheet(
            f"color: {COLOR_ORANGE}; font-weight: bold;" if pending_all else "color: gray;"
        )

        todo_counts = database.get_todo_dashboard_counts()
        self.todo_summary_label.setText(
            f"{todo_counts['pending']} Pending, {todo_counts['due_today']} Due Today, {todo_counts['overdue']} Overdue"
        )
        self.todo_summary_label.setStyleSheet(
            f"color: {COLOR_RED}; font-weight: bold;" if todo_counts["overdue"] else "color: inherit;"
        )

        self.admin_recent_activity_list.clear()
        for r in database.get_recent_activity(limit=8):
            ts = datetime.fromisoformat(r["start_time"])
            self.admin_recent_activity_list.addItem(
                f"{ts.strftime('%I:%M %p')} — {r['worker_name']} — {r['app_name']}"
            )
