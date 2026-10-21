"""
lmms.gui.widgets.automation_executions_view - Executions History Dashboard.
Presents past workflow runs, execution duration, status badges, and expandable JSON step traces.
"""

from __future__ import annotations

import datetime
import json
from typing import Optional, List, Dict, Any

from lmms.gui.qt import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSplitter,
    QPlainTextEdit,
    QFrame,
    Qt,
    QColor,
    QCursor,
    pyqtSignal,
)
from lmms.gui.widgets.automation_runner import WorkflowHistoryStore


class AutomationExecutionsView(QWidget):
    """
    Executions dashboard shown when clicking the [Executions] mode tab in AutomationHeader.
    """
    trace_selected = pyqtSignal(dict)

    def __init__(self, history_store: Optional[WorkflowHistoryStore] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("AutomationExecutionsView")
        self.history = history_store or WorkflowHistoryStore()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # Header Bar
        top_bar = QHBoxLayout()
        lbl_title = QLabel("Workflow Execution History")
        lbl_title.setStyleSheet("color: #f4f4f5; font-size: 15px; font-weight: 700;")

        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #20212a;
                color: #d4d4d8;
                border: 1px solid #2d303e;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2d303e;
                color: #ffffff;
            }
        """)
        self.btn_refresh.clicked.connect(self.reload_history)

        top_bar.addWidget(lbl_title)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_refresh)
        main_layout.addLayout(top_bar)

        # Splitter: Left Table / Right Trace Details
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.setHandleWidth(1)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Start Time", "Workflow", "Status", "Duration", "Steps"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #121318;
                border: 1px solid #282a35;
                border-radius: 8px;
                gridline-color: #1c1d24;
                color: #d4d4d8;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #181920;
                color: #9ca3af;
                font-weight: 600;
                border: none;
                border-bottom: 1px solid #282a35;
                padding: 6px;
            }
            QTableWidget::item:selected {
                background-color: #262836;
                color: #ffffff;
            }
        """)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        self.splitter.addWidget(self.table)

        # Right Trace Panel
        self.trace_box = QFrame()
        self.trace_box.setStyleSheet("background-color: #16171d; border: 1px solid #282a35; border-radius: 8px;")
        t_layout = QVBoxLayout(self.trace_box)
        t_layout.setContentsMargins(12, 12, 12, 12)
        t_layout.setSpacing(8)

        lbl_trace = QLabel("Execution Step Trace:")
        lbl_trace.setStyleSheet("color: #9ca3af; font-size: 12px; font-weight: 600;")
        self.trace_text = QPlainTextEdit()
        self.trace_text.setReadOnly(True)
        self.trace_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0f1014;
                border: 1px solid #232530;
                border-radius: 6px;
                color: #a7f3d0;
                font-family: monospace;
                font-size: 11px;
                padding: 8px;
            }
        """)
        t_layout.addWidget(lbl_trace)
        t_layout.addWidget(self.trace_text)
        self.splitter.addWidget(self.trace_box)

        self.splitter.setSizes([600, 350])
        main_layout.addWidget(self.splitter)

        self.reload_history()

    def reload_history(self):
        records = self.history.list_executions(limit=50)
        self.table.setRowCount(len(records))

        for row_idx, r in enumerate(records):
            # Timestamp
            dt_str = datetime.datetime.fromtimestamp(r["start_time"]).strftime("%Y-%m-%d %H:%M:%S")
            item_time = QTableWidgetItem(dt_str)

            # Workflow name
            item_name = QTableWidgetItem(r.get("workflow_name", "Workflow"))

            # Status pill
            status = r.get("status", "success")
            status_symbol = "● Success" if status == "success" else "● Error"
            item_status = QTableWidgetItem(status_symbol)
            if status == "success":
                item_status.setForeground(QColor("#10b981"))
            else:
                item_status.setForeground(QColor("#ef4444"))

            # Duration
            dur_str = f"{r.get('duration_ms', 0)}ms"
            item_dur = QTableWidgetItem(dur_str)

            # Steps
            steps_str = f"{r.get('step_count', 0)} steps"
            item_steps = QTableWidgetItem(steps_str)

            # Store ID on item
            item_time.setData(Qt.ItemDataRole.UserRole, r["id"])

            self.table.setItem(row_idx, 0, item_time)
            self.table.setItem(row_idx, 1, item_name)
            self.table.setItem(row_idx, 2, item_status)
            self.table.setItem(row_idx, 3, item_dur)
            self.table.setItem(row_idx, 4, item_steps)

        if records:
            self.table.selectRow(0)

    def _on_row_selected(self):
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return
        exec_id = self.table.item(self.table.currentRow(), 0).data(Qt.ItemDataRole.UserRole)
        trace = self.history.get_execution_trace(exec_id)
        if trace:
            self.trace_text.setPlainText(json.dumps(trace, indent=2))
        else:
            self.trace_text.setPlainText("No trace captured for this execution.")
