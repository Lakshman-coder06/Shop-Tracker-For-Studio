"""
ui/service_management_window.py
----------------------------------
Admin-only. Add services, change rates, and activate/deactivate a
service. Changing a rate here only affects future New Job entries -
every past transaction already stored the rate it was created with, so
old records never change (see database.create_transaction / update_service_rate).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QLineEdit, QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt

import database


class ServiceManagementWindow(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._row_ids = []
        self.selected_id = None

        self.setWindowTitle("Thalapathi Studio - Manage Services")
        self.setMinimumSize(640, 560)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self.setLayout(layout)

        title = QLabel("SERVICE & RATE MANAGEMENT")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Service", "Rate", "Status"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.cellClicked.connect(self._on_row_clicked)
        layout.addWidget(self.table)

        form_label = QLabel("ADD SERVICE / CHANGE RATE")
        form_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(form_label)

        form = QFormLayout()
        form.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Typing")
        form.addRow("Service Name:", self.name_input)

        self.rate_input = QDoubleSpinBox()
        self.rate_input.setPrefix("Rs ")
        self.rate_input.setMaximum(1_000_000)
        self.rate_input.setDecimals(0)
        form.addRow("Rate:", self.rate_input)

        layout.addLayout(form)

        button_row = QHBoxLayout()
        add_btn = QPushButton("+ ADD SERVICE")
        add_btn.clicked.connect(self.handle_add)
        button_row.addWidget(add_btn)

        self.update_rate_btn = QPushButton("Update Rate for Selected")
        self.update_rate_btn.clicked.connect(self.handle_update_rate)
        self.update_rate_btn.setEnabled(False)
        button_row.addWidget(self.update_rate_btn)

        self.toggle_btn = QPushButton("Activate/Deactivate Selected")
        self.toggle_btn.clicked.connect(self.handle_toggle_active)
        self.toggle_btn.setEnabled(False)
        button_row.addWidget(self.toggle_btn)

        layout.addLayout(button_row)

        note = QLabel("Changing a rate here only affects new jobs from now on - past transactions keep the rate they were created with.")
        note.setStyleSheet("color: gray;")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        self.refresh()

    def refresh(self):
        services = database.get_all_services_admin()
        self._row_ids = [s["id"] for s in services]
        self.table.setRowCount(len(services))
        for i, s in enumerate(services):
            self.table.setItem(i, 0, QTableWidgetItem(s["name"]))
            self.table.setItem(i, 1, QTableWidgetItem(f"Rs {s['rate']:.0f}"))
            status_item = QTableWidgetItem("Active" if s["active"] else "Inactive")
            status_item.setForeground(QColor("#2e9e5b" if s["active"] else "#c0392b"))
            self.table.setItem(i, 2, status_item)

    def _on_row_clicked(self, row, _col):
        if row < 0 or row >= len(self._row_ids):
            return
        self.selected_id = self._row_ids[row]
        services = database.get_all_services_admin()
        s = next((s for s in services if s["id"] == self.selected_id), None)
        if s is None:
            return
        self.name_input.setText(s["name"])
        self.rate_input.setValue(s["rate"])
        self.update_rate_btn.setEnabled(True)
        self.toggle_btn.setEnabled(True)

    def handle_add(self):
        name = self.name_input.text().strip()
        if not name:
            self._show_error("Service name is required.")
            return
        try:
            database.create_service(name, self.rate_input.value(), self.user["id"])
        except database.DuplicateNameError:
            self._show_error(f"'{name}' already exists.")
            return
        except Exception:
            self._show_error("Unable to save the service. Please try again.")
            return
        self._show_success(f"Service '{name}' added successfully.")
        self.name_input.clear()
        self.rate_input.setValue(0)
        self.selected_id = None
        self.refresh()

    def handle_update_rate(self):
        if self.selected_id is None:
            return
        database.update_service_rate(self.selected_id, self.rate_input.value(), self.user["id"])
        self._show_success(f"Rate updated to Rs {self.rate_input.value():.0f}. Past transactions are unaffected.")
        self.refresh()

    def handle_toggle_active(self):
        if self.selected_id is None:
            return
        services = database.get_all_services_admin()
        s = next((s for s in services if s["id"] == self.selected_id), None)
        if s is None:
            return
        new_active = not bool(s["active"])
        database.set_service_active(self.selected_id, new_active, self.user["id"])
        self._show_success(f"'{s['name']}' is now {'Active' if new_active else 'Inactive'}.")
        self.refresh()

    def _show_error(self, text):
        self.message_label.setStyleSheet("color: #c0392b; font-weight: bold;")
        self.message_label.setText(text)

    def _show_success(self, text):
        self.message_label.setStyleSheet("color: #2e9e5b; font-weight: bold;")
        self.message_label.setText(text)
