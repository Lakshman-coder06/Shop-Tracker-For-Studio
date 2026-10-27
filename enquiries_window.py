"""
ui/enquiries_window.py
-------------------------
PART 12: lets a worker record a problem/issue while the owner is away
("Printer 2 not working"), and lets Admin see everything, respond, and
change status. Workers see only their own enquiries and status updates -
scoped the same way Transactions/Expenses/Pending Records are.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QListWidget, QListWidgetItem, QMessageBox, QFrame
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from datetime import datetime

import database

PRIORITY_COLORS = {"Low": "#3a7bd5", "Medium": "#3a7bd5", "High": "#d97b1f", "Urgent": "#c0392b"}
STATUS_COLORS = {"Open": "#d97b1f", "In Progress": "#3a7bd5", "Resolved": "#2e9e5b", "Closed": "gray"}


class EnquiriesWindow(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.is_admin = user["role"] == "admin"
        self.selected_id = None

        self.setWindowTitle("Thalapathi Studio - Enquiries")
        self.setMinimumSize(820, 620)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self.setLayout(layout)

        title = QLabel("ENQUIRIES")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        # ---- New enquiry form ----
        form_frame = QFrame()
        form_layout = QFormLayout()
        form_frame.setLayout(form_layout)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. Printer 2 is not printing")
        form_layout.addRow("Title:", self.title_input)

        self.category_input = QComboBox()
        self.category_input.addItems(["Equipment", "Customer", "Supplies", "Other"])
        form_layout.addRow("Category:", self.category_input)

        self.priority_input = QComboBox()
        self.priority_input.addItems(["Low", "Medium", "High", "Urgent"])
        self.priority_input.setCurrentText("Medium")
        form_layout.addRow("Priority:", self.priority_input)

        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(70)
        form_layout.addRow("Description:", self.description_input)

        layout.addWidget(form_frame)

        submit_btn = QPushButton("Submit Enquiry")
        submit_btn.clicked.connect(self.handle_submit)
        layout.addWidget(submit_btn)

        self.message_label = QLabel("")
        layout.addWidget(self.message_label)

        # ---- Filter (Admin only) ----
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Open", "In Progress", "Resolved", "Closed"])
        self.status_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.status_filter)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        filter_row.addWidget(refresh_btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        # ---- List of enquiries as cards ----
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_select)
        layout.addWidget(self.list_widget, stretch=1)

        # ---- Admin response panel ----
        if self.is_admin:
            response_row = QHBoxLayout()
            self.comment_input = QLineEdit()
            self.comment_input.setPlaceholderText("Add a response/comment...")
            response_row.addWidget(self.comment_input)
            comment_btn = QPushButton("Add Comment")
            comment_btn.clicked.connect(self.handle_add_comment)
            response_row.addWidget(comment_btn)
            layout.addLayout(response_row)

            status_row = QHBoxLayout()
            status_row.addWidget(QLabel("Set status:"))
            self.new_status_combo = QComboBox()
            self.new_status_combo.addItems(["Open", "In Progress", "Resolved", "Closed"])
            status_row.addWidget(self.new_status_combo)
            apply_status_btn = QPushButton("Apply")
            apply_status_btn.clicked.connect(self.handle_set_status)
            status_row.addWidget(apply_status_btn)
            status_row.addStretch()
            layout.addLayout(status_row)

        self._ids = []
        self.refresh()

    def handle_submit(self):
        title = self.title_input.text().strip()
        if not title:
            self._show_error("Title is required.")
            return
        database.create_enquiry(
            title, self.category_input.currentText(), self.description_input.toPlainText().strip(),
            self.priority_input.currentText(), self.user["id"],
        )
        self._show_success("Enquiry submitted.")
        self.title_input.clear()
        self.description_input.clear()
        self.refresh()

    def refresh(self):
        created_by = None if self.is_admin else self.user["id"]
        status = self.status_filter.currentText() if self.is_admin else None
        rows = database.get_enquiries(created_by=created_by, status=status)
        self._ids = [r["id"] for r in rows]

        self.list_widget.clear()
        if not rows:
            self.list_widget.addItem("No open enquiries." if not self.is_admin else "Nothing here.")
            return

        for r in rows:
            ts = datetime.fromisoformat(r["created_at"])
            p_color = PRIORITY_COLORS.get(r["priority"], "#3a7bd5")
            s_color = STATUS_COLORS.get(r["status"], "gray")
            text = (
                f"[{r['priority'].upper()}] {r['title']}\n"
                f"   Reported by: {r['created_by_name']}   {ts.strftime('%d %b, %I:%M %p')}\n"
                f"   Status: {r['status']}"
            )
            item = QListWidgetItem(text)
            self.list_widget.addItem(item)

    def on_select(self, item):
        row = self.list_widget.row(item)
        if row >= len(self._ids):
            return
        self.selected_id = self._ids[row]

    def handle_add_comment(self):
        if self.selected_id is None:
            QMessageBox.information(self, "No enquiry selected", "Click an enquiry first.")
            return
        comment = self.comment_input.text().strip()
        if not comment:
            return
        database.add_enquiry_comment(self.selected_id, comment, self.user["id"])
        self.comment_input.clear()
        self._show_success("Comment added.")

    def handle_set_status(self):
        if self.selected_id is None:
            QMessageBox.information(self, "No enquiry selected", "Click an enquiry first.")
            return
        database.update_enquiry_status(self.selected_id, self.new_status_combo.currentText(), self.user["id"])
        self._show_success("Status updated.")
        self.refresh()

    def _show_error(self, text):
        self.message_label.setStyleSheet("color: #c0392b; font-weight: bold;")
        self.message_label.setText(text)

    def _show_success(self, text):
        self.message_label.setStyleSheet("color: #2e9e5b; font-weight: bold;")
        self.message_label.setText(text)
