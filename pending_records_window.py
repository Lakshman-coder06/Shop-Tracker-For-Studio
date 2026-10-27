"""
ui/pending_records_window.py
-------------------------------
The PENDING RECORDS screen. Shows every job that isn't both Completed and
Paid yet. A worker sees only their own pending jobs (this was previously
a privacy gap - any worker could see everyone's pending jobs; fixed by
scoping the query to worker_id for non-admin/supervisor roles). Admin and
Supervisor see everyone's.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView, QInputDialog,
    QDialog, QDoubleSpinBox, QComboBox, QDialogButtonBox
)
from PySide6.QtGui import QFont
from datetime import datetime

import database


class RecordPaymentDialog(QDialog):
    """Small dialog for recording a payment against a pending job - dated
    NOW (not backdated to when the job was created), which is what makes
    a balance collected days later count on the day it actually came in."""

    def __init__(self, parent, balance_due):
        super().__init__(parent)
        self.setWindowTitle("Record Payment")
        layout = QVBoxLayout()
        self.setLayout(layout)

        form = QFormLayout()
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setPrefix("Rs ")
        self.amount_input.setMaximum(1_000_000)
        self.amount_input.setDecimals(0)
        self.amount_input.setValue(max(balance_due, 0))
        form.addRow("Amount received now:", self.amount_input)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["Cash", "UPI"])
        form.addRow("Payment method:", self.method_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        return self.amount_input.value(), self.method_combo.currentText()


class PendingRecordsWindow(QWidget):
    def __init__(self, user, on_saved=None):
        super().__init__()
        self.user = user
        self.is_admin_or_supervisor = user["role"] in ("admin", "supervisor")
        self.on_saved = on_saved
        self._row_ids = []

        self.setWindowTitle("Thalapathi Studio - Pending Records")
        self.setMinimumSize(880, 540)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        self.setLayout(layout)

        header_row = QHBoxLayout()
        title = QLabel("PENDING RECORDS")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_row.addWidget(title)
        header_row.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        header_row.addWidget(refresh_btn)
        layout.addLayout(header_row)

        hint = QLabel("A job appears here until it is both Completed and Paid. Select a row, then use the buttons below.")
        hint.setStyleSheet("color: gray;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            ["Code", "Time", "Worker", "Customer/Ref", "Service", "Total", "Advance", "Balance", "Status", "Payment"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.table)

        button_row = QHBoxLayout()
        in_progress_btn = QPushButton("Mark In Progress")
        in_progress_btn.clicked.connect(self.handle_mark_in_progress)
        button_row.addWidget(in_progress_btn)
        complete_btn = QPushButton("Mark as Completed")
        complete_btn.clicked.connect(self.handle_mark_completed)
        button_row.addWidget(complete_btn)
        paid_btn = QPushButton("Record Payment")
        paid_btn.clicked.connect(self.handle_record_payment)
        button_row.addWidget(paid_btn)
        cancel_btn = QPushButton("Cancel Job")
        cancel_btn.clicked.connect(self.handle_cancel)
        button_row.addWidget(cancel_btn)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.refresh()

    def refresh(self):
        worker_id = None if self.is_admin_or_supervisor else self.user["id"]
        rows = database.get_pending_transactions(worker_id=worker_id)
        self._row_ids = [r["id"] for r in rows]
        self._row_balances = [r["amount"] - (r["paid_amount"] or 0) for r in rows]
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            ts = datetime.fromisoformat(r["created_at"])
            paid = r["paid_amount"] or 0
            balance = r["amount"] - paid
            self.table.setItem(i, 0, QTableWidgetItem(r["transaction_code"]))
            self.table.setItem(i, 1, QTableWidgetItem(ts.strftime("%d %b, %I:%M %p")))
            self.table.setItem(i, 2, QTableWidgetItem(r["worker_name"]))
            self.table.setItem(i, 3, QTableWidgetItem(r["customer_reference"] or ""))
            self.table.setItem(i, 4, QTableWidgetItem(r["service_name"]))
            self.table.setItem(i, 5, QTableWidgetItem(f"Rs {r['amount']:.0f}"))
            self.table.setItem(i, 6, QTableWidgetItem(f"Rs {paid:.0f}"))
            self.table.setItem(i, 7, QTableWidgetItem(f"Rs {balance:.0f}"))
            self.table.setItem(i, 8, QTableWidgetItem(r["status"]))
            self.table.setItem(i, 9, QTableWidgetItem(r["payment_status"]))
        if not rows:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("(nothing pending)"))
            for c in range(1, 10):
                self.table.setItem(0, c, QTableWidgetItem(""))
            self._row_ids = [None]
            self._row_balances = [0]

    def _selected_id(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.information(self, "No row selected", "Select a pending job first.")
            return None
        row = selected[0].row()
        if row >= len(self._row_ids) or self._row_ids[row] is None:
            return None
        return self._row_ids[row]

    def handle_mark_in_progress(self):
        tid = self._selected_id()
        if tid is None:
            return
        database.mark_transaction_in_progress(tid, self.user["id"])
        self.refresh()
        if self.on_saved:
            self.on_saved()

    def handle_mark_completed(self):
        tid = self._selected_id()
        if tid is None:
            return
        database.mark_transaction_completed(tid, self.user["id"])
        self.refresh()
        if self.on_saved:
            self.on_saved()

    def handle_record_payment(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.information(self, "No row selected", "Select a pending job first.")
            return
        row = selected[0].row()
        if row >= len(self._row_ids) or self._row_ids[row] is None:
            return
        tid = self._row_ids[row]
        balance_due = self._row_balances[row]

        dialog = RecordPaymentDialog(self, balance_due)
        if dialog.exec() != QDialog.Accepted:
            return
        amount, method = dialog.values()
        if amount <= 0:
            QMessageBox.warning(self, "Invalid amount", "Amount must be greater than zero.")
            return

        database.record_payment(tid, amount, method, self.user["id"])
        self.refresh()
        if self.on_saved:
            self.on_saved()

    def handle_cancel(self):
        tid = self._selected_id()
        if tid is None:
            return
        reason, ok = QInputDialog.getText(self, "Cancel Job", "Reason for cancelling:")
        if not ok or not reason.strip():
            return
        database.cancel_transaction(tid, reason.strip(), self.user["id"])
        self.refresh()
        if self.on_saved:
            self.on_saved()
