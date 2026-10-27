"""
ui/transactions_window.py
---------------------------
The TRANSACTIONS screen. A worker sees only their own transactions;
Admin/Supervisor can see everyone's and filter by worker. Filters: date
range, worker (admin only), payment method, service. The totals block
always reflects whatever filters are currently active, not a separate
fixed "today" query - so switching to "Yesterday" shows yesterday's totals.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QFrame, QGridLayout, QHeaderView
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from datetime import datetime

import database


class TransactionsWindow(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.is_admin_or_supervisor = user["role"] in ("admin", "supervisor")

        self.setWindowTitle("Thalapathi Studio - Transactions")
        self.setMinimumSize(820, 580)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        self.setLayout(layout)

        title = QLabel("TRANSACTIONS")
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

        filter_row.addWidget(QLabel("Payment:"))
        self.payment_filter = QComboBox()
        self.payment_filter.addItems(["All", "Cash", "UPI"])
        self.payment_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.payment_filter)

        filter_row.addWidget(QLabel("Service:"))
        self.service_filter = QComboBox()
        self.service_filter.addItem("All Services")
        for s in database.get_active_services():
            self.service_filter.addItem(s["name"])
        self.service_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.service_filter)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        filter_row.addWidget(refresh_btn)
        layout.addLayout(filter_row)

        # ---- Totals (always match the current filters) ----
        totals_frame = QFrame()
        totals_frame.setFrameShape(QFrame.StyledPanel)
        totals_layout = QGridLayout()
        totals_frame.setLayout(totals_layout)
        self.jobs_value = self._add_cell(totals_layout, 0, 0, "Number of Jobs")
        self.sales_value = self._add_cell(totals_layout, 0, 1, "Total Sales (Paid)")
        self.cash_value = self._add_cell(totals_layout, 0, 2, "Cash")
        self.upi_value = self._add_cell(totals_layout, 0, 3, "UPI")
        layout.addWidget(totals_frame)

        # ---- Table ----
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            ["Code", "Time", "Worker", "Service", "Qty", "Rate", "Total", "Payment", "Status"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.refresh()

    def _add_cell(self, grid, row, col, label_text):
        cell = QVBoxLayout()
        value = QLabel("—")
        value.setFont(QFont("Segoe UI", 15, QFont.Bold))
        value.setAlignment(Qt.AlignCenter)
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignCenter)
        cell.addWidget(value)
        cell.addWidget(label)
        grid.addLayout(cell, row, col)
        return value

    def refresh(self):
        date_map = {"Today": "today", "Yesterday": "yesterday", "Last 7 days": "week", "All": None}
        date_filter = date_map[self.date_filter.currentText()]
        worker_id = self.worker_filter.currentData() if self.is_admin_or_supervisor else self.user["id"]

        rows = database.get_transactions(date_filter=date_filter, worker_id=worker_id)

        payment = self.payment_filter.currentText()
        if payment != "All":
            rows = [r for r in rows if r["payment_method"] == payment]
        service = self.service_filter.currentText()
        if service != "All Services":
            rows = [r for r in rows if r["service_name"] == service]

        # Totals computed from these same filtered rows, so they always match what's shown below
        non_cancelled = [r for r in rows if r["status"] != "Cancelled"]
        paid = [r for r in non_cancelled if r["payment_status"] == "Paid"]
        self.jobs_value.setText(str(len(non_cancelled)))
        self.sales_value.setText(f"Rs {sum(r['amount'] for r in paid):.0f}")
        self.cash_value.setText(f"Rs {sum(r['amount'] for r in paid if r['payment_method']=='Cash'):.0f}")
        self.upi_value.setText(f"Rs {sum(r['amount'] for r in paid if r['payment_method']=='UPI'):.0f}")

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            ts = datetime.fromisoformat(r["created_at"])
            status_text = r["status"]
            if r["payment_status"] == "Unpaid":
                status_text += " (Unpaid)"
            self.table.setItem(i, 0, QTableWidgetItem(r["transaction_code"]))
            self.table.setItem(i, 1, QTableWidgetItem(ts.strftime("%d %b, %I:%M %p")))
            self.table.setItem(i, 2, QTableWidgetItem(r["worker_name"]))
            self.table.setItem(i, 3, QTableWidgetItem(r["service_name"]))
            self.table.setItem(i, 4, QTableWidgetItem(str(r["quantity"])))
            self.table.setItem(i, 5, QTableWidgetItem(f"Rs {r['rate'] or 0:.0f}"))
            self.table.setItem(i, 6, QTableWidgetItem(f"Rs {r['amount']:.0f}"))
            self.table.setItem(i, 7, QTableWidgetItem(r["payment_method"]))
            self.table.setItem(i, 8, QTableWidgetItem(status_text))
        self.table.setSortingEnabled(True)
