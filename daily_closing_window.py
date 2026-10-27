"""
ui/daily_closing_window.py
-----------------------------
The DAILY CLOSING screen. Shows the day's cash math and lets Admin/
Supervisor enter opening and actual cash to see (and save) the difference.
Workers can view the numbers but the entry fields are read-only for them.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QDoubleSpinBox, QFrame, QMessageBox
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

import database


class DailyClosingWindow(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.can_edit = user["role"] in ("admin", "supervisor")

        self.setWindowTitle("Thalapathi Studio - Daily Closing")
        self.setMinimumSize(460, 560)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self.setLayout(layout)

        header_row = QHBoxLayout()
        title = QLabel("DAILY CLOSING")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_row.addWidget(title)
        header_row.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        header_row.addWidget(refresh_btn)
        layout.addLayout(header_row)

        subtitle = QLabel("Check today's cash against what the shop actually collected.")
        subtitle.setStyleSheet("color: gray;")
        layout.addWidget(subtitle)

        if not self.can_edit:
            note = QLabel("View only - only Admin/Supervisor can enter cash counts and save closing.")
            note.setStyleSheet("color: gray;")
            note.setWordWrap(True)
            layout.addWidget(note)

        form = QFormLayout()
        form.setSpacing(10)

        self.opening_cash_input = QDoubleSpinBox()
        self.opening_cash_input.setPrefix("Rs ")
        self.opening_cash_input.setMaximum(1_000_000)
        self.opening_cash_input.setDecimals(0)
        self.opening_cash_input.valueChanged.connect(self._recalculate)
        self.opening_cash_input.setEnabled(self.can_edit)
        form.addRow("Cash in Drawer at Start:", self.opening_cash_input)

        self.cash_sales_label = QLabel("Rs 0")
        form.addRow("Cash Sales:", self.cash_sales_label)

        self.upi_sales_label = QLabel("Rs 0")
        form.addRow("UPI Sales:", self.upi_sales_label)

        self.expenses_label = QLabel("Rs 0")
        form.addRow("Cash Expenses:", self.expenses_label)

        layout.addLayout(form)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        layout.addWidget(divider)

        expected_row = QHBoxLayout()
        expected_row.addWidget(QLabel("CASH THAT SHOULD BE IN DRAWER:"))
        expected_row.addStretch()
        self.expected_label = QLabel("Rs 0")
        self.expected_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        expected_row.addWidget(self.expected_label)
        layout.addLayout(expected_row)

        actual_form = QFormLayout()
        self.actual_cash_input = QDoubleSpinBox()
        self.actual_cash_input.setPrefix("Rs ")
        self.actual_cash_input.setMaximum(1_000_000)
        self.actual_cash_input.setDecimals(0)
        self.actual_cash_input.valueChanged.connect(self._recalculate)
        self.actual_cash_input.setEnabled(self.can_edit)
        actual_form.addRow("Cash Actually in Drawer:", self.actual_cash_input)
        layout.addLayout(actual_form)

        diff_row = QHBoxLayout()
        diff_row.addWidget(QLabel("CASH DIFFERENCE:"))
        diff_row.addStretch()
        self.difference_label = QLabel("Rs 0")
        self.difference_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        diff_row.addWidget(self.difference_label)
        layout.addLayout(diff_row)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        if self.can_edit:
            save_btn = QPushButton("Finish Today's Closing")
            save_btn.setMinimumHeight(40)
            save_btn.clicked.connect(self.handle_save)
            layout.addWidget(save_btn)

        self.saved_label = QLabel("")
        self.saved_label.setStyleSheet("color: #2e9e5b; font-weight: bold;")
        layout.addWidget(self.saved_label)

        layout.addStretch()
        self.refresh()

    def refresh(self):
        self.totals = database.get_daily_totals_for_closing()
        self.cash_sales_label.setText(f"Rs {self.totals['cash_sales']:.0f}")
        self.upi_sales_label.setText(f"Rs {self.totals['upi_sales']:.0f}")
        self.expenses_label.setText(f"Rs {self.totals['cash_expenses']:.0f}")

        existing = database.get_daily_closing()
        if existing is not None:
            # Pre-fill from a previously saved closing for today, so reopening
            # this screen doesn't lose what was already entered - this
            # includes Opening Cash, which used to be silently lost on
            # reopen (it was only ever used to calculate expected_cash, but
            # never itself saved/restored) - that was a real bug, now fixed.
            self.opening_cash_input.setValue(existing["opening_cash"] or 0)
            self.actual_cash_input.setValue(existing["actual_cash"] or 0)
            self.saved_label.setText(
                f"Last saved: opening Rs {existing['opening_cash'] or 0:.0f}, "
                f"expected Rs {existing['expected_cash']:.0f}, "
                f"actual Rs {existing['actual_cash']:.0f}, "
                f"difference Rs {existing['difference']:.0f}"
            )
        self._recalculate()

    def _recalculate(self):
        opening = self.opening_cash_input.value()
        expected = opening + self.totals["cash_sales"] - self.totals["cash_expenses"]
        self.expected_label.setText(f"Rs {expected:.0f}")

        actual = self.actual_cash_input.value()
        difference = actual - expected
        self.difference_label.setText(f"Rs {difference:.0f}")

        if actual == 0:
            self.difference_label.setStyleSheet("")
            self.status_label.setText("Enter the actual cash counted in the drawer to see the difference.")
            self.status_label.setStyleSheet("color: gray;")
        elif abs(difference) < 0.01:
            self.difference_label.setStyleSheet("color: #2e9e5b;")
            self.status_label.setText("Cash matches.")
            self.status_label.setStyleSheet("color: #2e9e5b; font-weight: bold;")
        else:
            self.difference_label.setStyleSheet("color: #c0392b;")
            self.status_label.setText("Cash difference detected — review transactions and expenses.")
            self.status_label.setStyleSheet("color: #c0392b; font-weight: bold;")

        self._last_expected = expected
        self._last_difference = difference

    def handle_save(self):
        opening = self.opening_cash_input.value()
        actual = self.actual_cash_input.value()
        database.save_daily_closing(
            opening_cash=opening,
            expected_cash=self._last_expected,
            actual_cash=actual,
            difference=self._last_difference,
            closed_by=self.user["id"],
        )
        self.saved_label.setText(
            f"Saved. Expected Rs {self._last_expected:.0f}, actual Rs {actual:.0f}, "
            f"difference Rs {self._last_difference:.0f}."
        )
