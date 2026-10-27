"""
ui/audit_log_window.py
-------------------------
Admin-only viewer for the audit trail. There's no delete/edit here on
purpose - workers can't reach this screen at all, and even Admin can only
view, never alter, past audit entries.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtGui import QFont
from datetime import datetime

import database


class AuditLogWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Thalapathi Studio - Audit Log")
        self.setMinimumSize(760, 560)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        self.setLayout(layout)

        header_row = QHBoxLayout()
        title = QLabel("AUDIT LOG")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_row.addWidget(title)
        header_row.addStretch()

        header_row.addWidget(QLabel("Table:"))
        self.table_filter = QComboBox()
        self.table_filter.addItems(["All", "transactions", "users", "services"])
        self.table_filter.currentIndexChanged.connect(self.refresh)
        header_row.addWidget(self.table_filter)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        header_row.addWidget(refresh_btn)
        layout.addLayout(header_row)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Date/Time", "User", "Table", "Record ID", "Field", "Old Value", "New Value"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self):
        table_name = None if self.table_filter.currentText() == "All" else self.table_filter.currentText()
        rows = database.get_audit_logs(table_name=table_name)

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            ts = datetime.fromisoformat(r["created_at"])
            self.table.setItem(i, 0, QTableWidgetItem(ts.strftime("%d %b %Y, %I:%M:%S %p")))
            self.table.setItem(i, 1, QTableWidgetItem(r["changed_by_name"] or "—"))
            self.table.setItem(i, 2, QTableWidgetItem(r["table_name"]))
            self.table.setItem(i, 3, QTableWidgetItem(str(r["record_id"])))
            self.table.setItem(i, 4, QTableWidgetItem(r["field_changed"] or ""))
            self.table.setItem(i, 5, QTableWidgetItem(r["old_value"] or ""))
            self.table.setItem(i, 6, QTableWidgetItem(r["new_value"] or ""))
        self.table.setSortingEnabled(True)
