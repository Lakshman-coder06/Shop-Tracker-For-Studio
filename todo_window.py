"""
ui/todo_window.py
--------------------
PART 13: the owner's task list. Admin has full task management; workers
see only tasks assigned to them and can update/complete those.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QDateEdit, QListWidget, QListWidgetItem, QMessageBox, QFrame
)
from PySide6.QtGui import QFont
from PySide6.QtCore import QDate, Qt
from datetime import datetime, date

import database

PRIORITY_COLORS = {"Low": "#3a7bd5", "Medium": "#3a7bd5", "High": "#d97b1f", "Urgent": "#c0392b"}


class TodoWindow(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.is_admin = user["role"] == "admin"
        self.selected_id = None

        self.setWindowTitle("Thalapathi Studio - To-Do")
        self.setMinimumSize(780, 620)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self.setLayout(layout)

        title = QLabel("TO-DO")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        if self.is_admin:
            form_frame = QFrame()
            form_layout = QFormLayout()
            form_frame.setLayout(form_layout)

            self.title_input = QLineEdit()
            self.title_input.setPlaceholderText("e.g. Call wedding customer")
            form_layout.addRow("Title:", self.title_input)

            self.description_input = QTextEdit()
            self.description_input.setMaximumHeight(60)
            form_layout.addRow("Description:", self.description_input)

            self.priority_input = QComboBox()
            self.priority_input.addItems(["Low", "Medium", "High", "Urgent"])
            self.priority_input.setCurrentText("Medium")
            form_layout.addRow("Priority:", self.priority_input)

            self.due_date_input = QDateEdit()
            self.due_date_input.setCalendarPopup(True)
            self.due_date_input.setDate(QDate.currentDate())
            form_layout.addRow("Due Date:", self.due_date_input)

            self.assigned_input = QComboBox()
            self.assigned_input.addItem("(unassigned - owner task)", None)
            for w in database.get_active_workers():
                if w["role"] != "admin":
                    self.assigned_input.addItem(w["name"], w["id"])
            form_layout.addRow("Assign To:", self.assigned_input)

            layout.addWidget(form_frame)

            add_btn = QPushButton("+ ADD TASK")
            add_btn.clicked.connect(self.handle_add)
            layout.addWidget(add_btn)

            self.message_label = QLabel("")
            layout.addWidget(self.message_label)

        # ---- Dashboard-style counts ----
        counts = database.get_todo_dashboard_counts()
        counts_row = QHBoxLayout()
        counts_row.addWidget(QLabel(f"{counts['pending']} Pending"))
        counts_row.addWidget(QLabel(f"{counts['due_today']} Due Today"))
        overdue_label = QLabel(f"{counts['overdue']} Overdue")
        if counts["overdue"]:
            overdue_label.setStyleSheet("color: #c0392b; font-weight: bold;")
        counts_row.addWidget(overdue_label)
        counts_row.addStretch()
        layout.addLayout(counts_row)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Pending", "In Progress", "Completed", "Cancelled"])
        self.status_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.status_filter)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        filter_row.addWidget(refresh_btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_select)
        layout.addWidget(self.list_widget, stretch=1)

        action_row = QHBoxLayout()
        action_row.addWidget(QLabel("Set status:"))
        self.new_status_combo = QComboBox()
        self.new_status_combo.addItems(["Pending", "In Progress", "Completed", "Cancelled"])
        action_row.addWidget(self.new_status_combo)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.handle_set_status)
        action_row.addWidget(apply_btn)
        action_row.addStretch()
        layout.addLayout(action_row)

        self._ids = []
        self.refresh()

    def handle_add(self):
        title = self.title_input.text().strip()
        if not title:
            self._show_error("Title is required.")
            return
        due = self.due_date_input.date().toString("yyyy-MM-dd")
        database.create_todo(
            title, self.description_input.toPlainText().strip(), self.priority_input.currentText(),
            due, self.user["id"], assigned_to=self.assigned_input.currentData(),
        )
        self._show_success("Task created.")
        self.title_input.clear()
        self.description_input.clear()
        self.refresh()

    def refresh(self):
        assigned_to = None if self.is_admin else self.user["id"]
        status = self.status_filter.currentText()
        rows = database.get_todos(assigned_to=assigned_to, status=status)
        self._ids = [r["id"] for r in rows]

        self.list_widget.clear()
        if not rows:
            self.list_widget.addItem("You're all caught up.")
            return

        today_str = date.today().isoformat()
        for r in rows:
            overdue = r["due_date"] and r["due_date"] < today_str and r["status"] in ("Pending", "In Progress")
            due_text = f"Due: {r['due_date']}" if r["due_date"] else "No due date"
            if overdue:
                due_text += " (OVERDUE)"
            assigned_text = r["assigned_to_name"] or "Unassigned"
            text = (
                f"[{r['priority'].upper()}] {r['title']}\n"
                f"   Assigned to: {assigned_text}   {due_text}\n"
                f"   Status: {r['status']}"
            )
            self.list_widget.addItem(QListWidgetItem(text))

    def on_select(self, item):
        row = self.list_widget.row(item)
        if row >= len(self._ids):
            return
        self.selected_id = self._ids[row]

    def handle_set_status(self):
        if self.selected_id is None:
            QMessageBox.information(self, "No task selected", "Click a task first.")
            return
        database.update_todo_status(self.selected_id, self.new_status_combo.currentText(), self.user["id"])
        self.refresh()

    def _show_error(self, text):
        self.message_label.setStyleSheet("color: #c0392b; font-weight: bold;")
        self.message_label.setText(text)

    def _show_success(self, text):
        self.message_label.setStyleSheet("color: #2e9e5b; font-weight: bold;")
        self.message_label.setText(text)
