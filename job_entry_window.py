"""
ui/job_entry_window.py
------------------------
The NEW JOB screen. Designed for speed: pick a service, its fixed rate
appears automatically, type a quantity, the total updates live, pick
payment method and status, hit Save.

SECURITY: the Rate shown here is a read-only DISPLAY, not an input field -
there is no spinbox, text box, or any other editable control for it. The
worker cannot change ₹5.00 to anything else. This is enforced again on
the backend: database.create_transaction() doesn't even accept a rate
parameter - it looks the current price up itself from the services
table, so nothing submitted from this screen (or anywhere else) could
override it even if this UI were bypassed entirely. Only Admin can change
a service's rate, via Service Management.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QMessageBox
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

import database


class JobEntryWindow(QWidget):
    def __init__(self, user, on_saved=None):
        super().__init__()
        self.user = user
        self.on_saved = on_saved  # called after a successful save, so the Dashboard can refresh its numbers
        self.services = database.get_active_services()

        self.setWindowTitle("Thalapathi Studio - New Job")
        self.setMinimumSize(440, 480)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self.setLayout(layout)

        title = QLabel("NEW JOB")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        worker_label = QLabel(f"Worker: {self.user['name']}")
        worker_label.setStyleSheet("color: gray;")
        layout.addWidget(worker_label)

        form = QFormLayout()
        form.setSpacing(10)

        self.customer_input = QLineEdit()
        self.customer_input.setPlaceholderText("optional")
        form.addRow("Customer/Reference:", self.customer_input)

        self.service_combo = QComboBox()
        for s in self.services:
            self.service_combo.addItem(s["name"], s)
        self.service_combo.currentIndexChanged.connect(self._on_service_changed)
        form.addRow("Service:", self.service_combo)

        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(1)
        self.quantity_input.setMaximum(9999)
        self.quantity_input.setValue(1)
        self.quantity_input.valueChanged.connect(self._recalculate)
        form.addRow("Quantity:", self.quantity_input)

        # Rate is a READ-ONLY display, not an input - fixed shop rates are
        # set by Admin in Service Management and cannot be changed here.
        self.rate_display = QLabel("Rs 0")
        self.rate_display.setFont(QFont("Segoe UI", 11, QFont.Bold))
        form.addRow("Rate:", self.rate_display)

        self.total_label = QLabel("Rs 0")
        self.total_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.total_label.setStyleSheet("color: #2e9e5b;")
        form.addRow("Total:", self.total_label)

        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["Cash", "UPI"])
        form.addRow("Payment Method:", self.payment_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Completed", "Pending", "In Progress"])
        self.status_combo.setToolTip(
            "Completed = done and paid now (the normal case).\n"
            "Pending / In Progress = work not finished yet - it'll show up in\n"
            "Pending Records until marked Completed and Paid."
        )
        self.status_combo.currentIndexChanged.connect(self._on_status_changed)
        form.addRow("Status:", self.status_combo)

        self.advance_input = QDoubleSpinBox()
        self.advance_input.setPrefix("Rs ")
        self.advance_input.setMaximum(1_000_000)
        self.advance_input.setDecimals(0)
        self.advance_input.setEnabled(False)
        self.advance_input.setToolTip("Advance/deposit taken now, for a job that isn't finished yet (e.g. Album Design).")
        form.addRow("Advance (optional):", self.advance_input)

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("optional")
        form.addRow("Notes:", self.notes_input)

        layout.addLayout(form)

        button_row = QHBoxLayout()
        save_btn = QPushButton("SAVE")
        save_btn.setMinimumHeight(44)
        save_btn.clicked.connect(self.handle_save)
        button_row.addWidget(save_btn)
        layout.addLayout(button_row)

        self.confirm_label = QLabel("")
        self.confirm_label.setStyleSheet("color: #2e9e5b; font-weight: bold;")
        layout.addWidget(self.confirm_label)

        layout.addStretch()
        self._on_service_changed()  # shows Rate for the initially-selected service

    def refresh(self):
        """Re-fetches services (and their current rates) from the database.
        This page is created once and reused, so without this, a rate
        change Admin makes in Service Management wouldn't show up here
        until the app restarted - this is what makes it show up the next
        time a worker opens New Job instead."""
        previous_service_id = None
        current = self.service_combo.currentData()
        if current is not None:
            previous_service_id = current["id"]

        self.services = database.get_active_services()
        self.service_combo.blockSignals(True)
        self.service_combo.clear()
        restore_index = 0
        for i, s in enumerate(self.services):
            self.service_combo.addItem(s["name"], s)
            if s["id"] == previous_service_id:
                restore_index = i
        self.service_combo.setCurrentIndex(restore_index)
        self.service_combo.blockSignals(False)
        self._on_service_changed()

    def _on_service_changed(self):
        """Shows the Rate for the newly selected service - always its
        current, authoritative price from Service Management. There is
        nothing here for a worker to type over."""
        service = self.service_combo.currentData()
        if service is None:
            return
        self.rate_display.setText(f"Rs {service['rate']:.0f}")
        self._recalculate()

    def _on_status_changed(self):
        completed = self.status_combo.currentText() == "Completed"
        self.advance_input.setEnabled(not completed)
        if completed:
            self.advance_input.setValue(0)

    def _recalculate(self):
        service = self.service_combo.currentData()
        rate = service["rate"] if service else 0
        qty = self.quantity_input.value()
        total = rate * qty
        self.total_label.setText(f"Rs {total:.0f}")

    def handle_save(self):
        service = self.service_combo.currentData()
        if service is None:
            QMessageBox.warning(self, "Missing service", "Please select a service.")
            return
        qty = self.quantity_input.value()
        if qty < 1:
            QMessageBox.warning(self, "Invalid quantity", "Quantity must be at least 1.")
            return

        # Note: no 'rate' is passed here at all - create_transaction looks
        # the current fixed rate up itself from service_id, so there is no
        # way for this screen (or anything calling this function) to
        # submit a different price.
        row_id, code = database.create_transaction(
            worker_id=self.user["id"],
            service_id=service["id"],
            quantity=qty,
            payment_method=self.payment_combo.currentText(),
            status=self.status_combo.currentText(),
            customer_reference=self.customer_input.text().strip() or None,
            notes=self.notes_input.text().strip() or None,
            advance_amount=self.advance_input.value(),
        )

        self.confirm_label.setText(f"Job saved successfully. ({code})")

        # Reset the form for the next job, ready to go immediately
        self.customer_input.clear()
        self.service_combo.setCurrentIndex(0)
        self.quantity_input.setValue(1)
        self.payment_combo.setCurrentIndex(0)
        self.status_combo.setCurrentIndex(0)
        self.advance_input.setValue(0)
        self.notes_input.clear()
        self._on_service_changed()  # re-shows Rate for service[0], even if the index didn't change

        if self.on_saved:
            self.on_saved()
