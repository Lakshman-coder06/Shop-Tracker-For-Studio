"""
ui/expense_entry_window.py
-----------------------------
The EXPENSE screen. A fast entry form (Worker is automatic) plus a running
list of today's expenses right below it, so you can immediately confirm a
save worked without needing a separate screen.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QDoubleSpinBox, QMessageBox, QListWidget
)
from PySide6.QtGui import QFont
from datetime import datetime

import database

EXPENSE_CATEGORIES = ["Bus Fare", "Tea/Food", "Travel", "Stationery", "Shop Expense", "Other"]


class ExpenseEntryWindow(QWidget):
    def __init__(self, user, on_saved=None):
        super().__init__()
        self.user = user
        self.on_saved = on_saved

        self.setWindowTitle("Thalapathi Studio - Expense")
        self.setMinimumSize(440, 560)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self.setLayout(layout)

        title = QLabel("EXPENSE")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        worker_label = QLabel(f"Worker: {self.user['name']}")
        worker_label.setStyleSheet("color: gray;")
        layout.addWidget(worker_label)

        form = QFormLayout()
        form.setSpacing(10)

        self.category_combo = QComboBox()
        self.category_combo.addItems(EXPENSE_CATEGORIES)
        form.addRow("Category:", self.category_combo)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setPrefix("Rs ")
        self.amount_input.setMaximum(1_000_000)
        self.amount_input.setDecimals(0)
        form.addRow("Amount:", self.amount_input)

        self.reason_input = QLineEdit()
        self.reason_input.setPlaceholderText("e.g. Bus fare to bank")
        form.addRow("Reason:", self.reason_input)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["Cash", "UPI"])
        self.source_combo.setToolTip(
            "Which drawer this came out of - only Cash expenses reduce the\n"
            "physical cash-in-drawer calculation on Daily Closing."
        )
        form.addRow("Payment Source:", self.source_combo)

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("optional")
        form.addRow("Notes:", self.notes_input)

        layout.addLayout(form)

        button_row = QHBoxLayout()
        save_btn = QPushButton("SAVE EXPENSE")
        save_btn.setMinimumHeight(44)
        save_btn.clicked.connect(self.handle_save)
        button_row.addWidget(save_btn)
        layout.addLayout(button_row)

        self.confirm_label = QLabel("")
        self.confirm_label.setStyleSheet("color: #2e9e5b; font-weight: bold;")
        layout.addWidget(self.confirm_label)

        layout.addWidget(QLabel("TODAY'S EXPENSES"))
        self.expense_list = QListWidget()
        layout.addWidget(self.expense_list)

        self._refresh_list()

    def handle_save(self):
        amount = self.amount_input.value()
        if amount <= 0:
            QMessageBox.warning(self, "Invalid amount", "Amount must be greater than zero.")
            return
        reason = self.reason_input.text().strip()
        if not reason:
            QMessageBox.warning(self, "Reason required", "Please enter a short reason.")
            return

        row_id, code = database.create_expense(
            worker_id=self.user["id"],
            category=self.category_combo.currentText(),
            reason=reason,
            amount=amount,
            payment_method=self.source_combo.currentText(),
            notes=self.notes_input.text().strip() or None,
        )

        self.confirm_label.setText(f"Expense saved successfully. ({code})")

        self.amount_input.setValue(0)
        self.reason_input.clear()
        self.notes_input.clear()
        self.category_combo.setCurrentIndex(0)
        self.source_combo.setCurrentIndex(0)

        self._refresh_list()
        if self.on_saved:
            self.on_saved()

    def _refresh_list(self):
        self.expense_list.clear()
        for r in database.get_expenses_today(worker_id=self.user["id"]):
            ts = datetime.fromisoformat(r["created_at"])
            self.expense_list.addItem(
                f"{ts.strftime('%I:%M %p')}  —  {r['worker_name']}  —  {r['category']}  —  "
                f"Rs {r['amount']:.0f} ({r['payment_method']})  —  {r['purpose']}"
            )
