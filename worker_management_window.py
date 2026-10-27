"""
ui/worker_management_window.py
---------------------------------
Admin-only. Add/edit workers, change their Active/On Leave/Inactive
status, and reset a PIN (with a forced change-on-next-login option for
temporary/shift-cover PINs). A deactivated or On Leave worker cannot log
in - this is enforced in database.get_active_workers(), which the login
screen already uses.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem, QMessageBox,
    QHeaderView, QCheckBox
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt

import database

STATUS_COLORS = {"Active": "#2e9e5b", "On Leave": "#d97b1f", "Inactive": "#c0392b"}


class WorkerManagementWindow(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._row_ids = []

        self.setWindowTitle("Thalapathi Studio - Manage Workers")
        self.setMinimumSize(720, 620)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self.setLayout(layout)

        title = QLabel("MANAGE WORKERS")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        # ---- Table of existing workers ----
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Employee ID", "Role", "Status", ""])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.cellClicked.connect(self._on_row_clicked)
        layout.addWidget(self.table)

        # ---- Add / Edit form ----
        form_label = QLabel("ADD / EDIT WORKER")
        form_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(form_label)

        form = QFormLayout()
        form.setSpacing(8)

        self.name_input = QLineEdit()
        form.addRow("Name:", self.name_input)

        self.employee_id_input = QLineEdit()
        self.employee_id_input.setPlaceholderText("optional")
        form.addRow("Employee ID:", self.employee_id_input)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["worker", "supervisor", "admin"])
        form.addRow("Role:", self.role_combo)

        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("required when adding a new worker")
        form.addRow("PIN:", self.pin_input)

        self.temp_pin_checkbox = QCheckBox("Require PIN change at next login (temporary/shift-cover PIN)")
        form.addRow("", self.temp_pin_checkbox)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "On Leave", "Inactive"])
        form.addRow("Status:", self.status_combo)

        layout.addLayout(form)

        button_row = QHBoxLayout()
        self.add_btn = QPushButton("+ ADD WORKER")
        self.add_btn.clicked.connect(self.handle_add)
        button_row.addWidget(self.add_btn)

        self.save_btn = QPushButton("Save Changes to Selected")
        self.save_btn.clicked.connect(self.handle_save_selected)
        self.save_btn.setEnabled(False)
        button_row.addWidget(self.save_btn)

        self.reset_pin_btn = QPushButton("Reset PIN for Selected")
        self.reset_pin_btn.clicked.connect(self.handle_reset_pin)
        self.reset_pin_btn.setEnabled(False)
        button_row.addWidget(self.reset_pin_btn)

        clear_btn = QPushButton("Clear Form")
        clear_btn.clicked.connect(self._clear_form)
        button_row.addWidget(clear_btn)

        layout.addLayout(button_row)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        self.selected_id = None
        self.refresh()

    def refresh(self):
        workers = database.get_all_workers_admin()
        self._row_ids = [w["id"] for w in workers]
        self.table.setRowCount(len(workers))
        for i, w in enumerate(workers):
            self.table.setItem(i, 0, QTableWidgetItem(w["name"]))
            self.table.setItem(i, 1, QTableWidgetItem(w["employee_id"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(w["role"].capitalize()))
            status_item = QTableWidgetItem(w["status"] or "Active")
            status_item.setForeground(Qt.GlobalColor.white)
            self.table.setItem(i, 3, status_item)
            self.table.item(i, 3).setBackground(QColor(STATUS_COLORS.get(w["status"] or "Active")))
            pending = " (must change PIN)" if w["must_change_pin"] else ""
            self.table.setItem(i, 4, QTableWidgetItem(pending))

    def _on_row_clicked(self, row, _col):
        if row < 0 or row >= len(self._row_ids):
            return
        self.selected_id = self._row_ids[row]
        workers = database.get_all_workers_admin()
        w = next((w for w in workers if w["id"] == self.selected_id), None)
        if w is None:
            return
        self.name_input.setText(w["name"])
        self.employee_id_input.setText(w["employee_id"] or "")
        self.role_combo.setCurrentText(w["role"])
        self.status_combo.setCurrentText(w["status"] or "Active")
        self.pin_input.clear()
        self.save_btn.setEnabled(True)
        self.reset_pin_btn.setEnabled(True)

    def _clear_form(self):
        self.selected_id = None
        self.name_input.clear()
        self.employee_id_input.clear()
        self.role_combo.setCurrentIndex(0)
        self.pin_input.clear()
        self.temp_pin_checkbox.setChecked(False)
        self.status_combo.setCurrentIndex(0)
        self.save_btn.setEnabled(False)
        self.reset_pin_btn.setEnabled(False)
        self.table.clearSelection()

    def handle_add(self):
        name = self.name_input.text().strip()
        pin = self.pin_input.text().strip()
        if not name:
            self._show_error("Name is required.")
            return
        if not pin or len(pin) < 4:
            self._show_error("A PIN of at least 4 digits is required for a new worker.")
            return
        database.create_worker(
            name=name,
            pin=pin,
            role=self.role_combo.currentText(),
            employee_id=self.employee_id_input.text().strip() or None,
        )
        self._show_success(f"Worker '{name}' added.")
        self._clear_form()
        self.refresh()

    def handle_save_selected(self):
        if self.selected_id is None:
            return
        name = self.name_input.text().strip()
        if not name:
            self._show_error("Name is required.")
            return
        database.update_worker(self.selected_id, name, self.employee_id_input.text().strip() or None, self.user["id"])
        try:
            database.set_worker_status(self.selected_id, self.status_combo.currentText(), self.user["id"])
        except database.LastAdminError:
            self._show_error("Cannot deactivate the last remaining active Admin account.")
            self.refresh()
            return
        except Exception:
            self._show_error("Unable to save changes. Please try again.")
            return
        self._show_success(f"Changes saved for '{name}'.")
        self.refresh()

    def handle_reset_pin(self):
        if self.selected_id is None:
            return
        pin = self.pin_input.text().strip()
        if not pin or len(pin) < 4:
            self._show_error("Enter a new PIN of at least 4 digits in the PIN field, then click Reset PIN.")
            return
        require_change = self.temp_pin_checkbox.isChecked()
        database.admin_reset_pin(self.selected_id, pin, self.user["id"], require_change=require_change)
        self._show_success(
            "PIN reset." + (" Worker must change it at next login." if require_change else "")
        )
        self.pin_input.clear()
        self.temp_pin_checkbox.setChecked(False)
        self.refresh()

    def _show_error(self, text):
        self.message_label.setStyleSheet("color: #c0392b; font-weight: bold;")
        self.message_label.setText(text)

    def _show_success(self, text):
        self.message_label.setStyleSheet("color: #2e9e5b; font-weight: bold;")
        self.message_label.setText(text)
