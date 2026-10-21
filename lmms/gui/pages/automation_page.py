"""
lmms.gui.pages.automation_page - Complete Automation Studio Page.
Integrates the n8n-style AutomationCanvas, right-side Trigger Drawer,
top workflow controls header, and workflow session persistence.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Optional, Dict, Any

from lmms.gui.qt import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QFrame,
    Qt,
    QColor,
    QCursor,
    pyqtSignal,
    QTimer,
)
from lmms.gui.branding import AutomationBranding
from lmms.gui.widgets.automation_canvas import AutomationCanvas
from lmms.gui.widgets.automation_drawer import AutomationDrawer
from lmms.gui.widgets.automation_inspector import AutomationInspector
from lmms.gui.widgets.automation_runner import WorkflowExecutionEngine, WorkflowHistoryStore
from lmms.gui.widgets.automation_executions_view import AutomationExecutionsView
from lmms.gui.qt import run_coro_safe


class AutomationHeader(QFrame):
    """Top header bar for workflow management, execution control, and status."""
    test_workflow_requested = pyqtSignal()
    stop_workflow_requested = pyqtSignal()
    save_workflow_requested = pyqtSignal()
    open_workflow_requested = pyqtSignal()
    clear_workflow_requested = pyqtSignal()
    mode_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("AutomationHeader")
        self.setFixedHeight(50)
        self.setStyleSheet("""
            QFrame#AutomationHeader {
                background-color: #16171d;
                border-bottom: 1px solid #282a35;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(14)

        # 1. Brand Logo & Workflow Name
        logo_lbl = QLabel()
        logo_lbl.setPixmap(AutomationBranding.get_logo_pixmap(24))
        logo_lbl.setFixedSize(24, 24)

        self.name_edit = QLineEdit("My workflow")
        self.name_edit.setToolTip("Rename workflow")
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                color: #f4f4f5;
                font-size: 14px;
                font-weight: 600;
                padding: 4px 8px;
            }
            QLineEdit:hover {
                background-color: #20212a;
                border: 1px solid #323544;
            }
            QLineEdit:focus {
                background-color: #1f2029;
                border: 1px solid #8b5cf6;
            }
        """)

        layout.addWidget(logo_lbl)
        layout.addWidget(self.name_edit)

        # 2. View Mode Tabs: [Editor] [Executions] [Evaluations]
        self.mode_container = QFrame()
        self.mode_container.setStyleSheet("""
            QFrame {
                background-color: #1c1d24;
                border: 1px solid #2a2c38;
                border-radius: 6px;
            }
        """)
        mode_layout = QHBoxLayout(self.mode_container)
        mode_layout.setContentsMargins(2, 2, 2, 2)
        mode_layout.setSpacing(2)

        self.mode_btns: Dict[str, QPushButton] = {}
        for mode in ("Editor", "Executions", "Evaluations"):
            btn = QPushButton(mode)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if mode == "Editor":
                btn.setChecked(True)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #9ca3af;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:checked {
                    background-color: #2e303e;
                    color: #f4f4f5;
                    font-weight: 600;
                }
                QPushButton:hover:!checked {
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda checked, m=mode: self._on_mode_clicked(m))
            self.mode_btns[mode] = btn
            mode_layout.addWidget(btn)

        layout.addWidget(self.mode_container)
        layout.addStretch()

        # 3. Engine Status Chip
        self.chip_engine = QLabel("● Engine Active")
        self.chip_engine.setStyleSheet("""
            color: #10b981;
            font-size: 11px;
            font-weight: 600;
            background-color: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 10px;
            padding: 3px 9px;
        """)
        layout.addWidget(self.chip_engine)

        # 4. Action Buttons
        self.btn_save = QPushButton("💾 Save")
        self.btn_save.setToolTip("Save workflow to project")
        self.btn_save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #232530;
                color: #d4d4d8;
                border: 1px solid #333647;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2c2f3e;
                color: #ffffff;
            }
        """)
        self.btn_save.clicked.connect(self.save_workflow_requested)
        layout.addWidget(self.btn_save)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setToolTip("Clear all nodes")
        self.btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #a1a1aa;
                border: 1px solid #2f3240;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #262833;
                color: #ef4444;
                border-color: #ef4444;
            }
        """)
        self.btn_clear.clicked.connect(self.clear_workflow_requested)
        layout.addWidget(self.btn_clear)

        self.btn_test = QPushButton("▶  Test workflow")
        self.btn_test.setToolTip("Execute workflow from triggers")
        self.btn_test.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_test.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
            QPushButton:disabled {
                background-color: #27272a;
                color: #71717a;
            }
        """)
        self.btn_test.clicked.connect(self.test_workflow_requested)
        layout.addWidget(self.btn_test)

    def _on_mode_clicked(self, active_mode: str):
        for mode, btn in self.mode_btns.items():
            btn.setChecked(mode == active_mode)
        self.mode_changed.emit(active_mode)

    def get_workflow_name(self) -> str:
        return self.name_edit.text().strip() or "Untitled workflow"

    def set_workflow_name(self, name: str):
        self.name_edit.setText(name)


class AutomationPage(QWidget):
    """
    Main LMMs Desktop Automation Page.
    Serves as the root orchestrator view for n8n-style node workflows.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("AutomationPage")
        self.active_file_path: Optional[str] = None

        self.init_ui()
        self.wire_signals()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header
        self.header = AutomationHeader(self)
        main_layout.addWidget(self.header)

        # 2. Main Content Stack (Editor / Executions / Evaluations)
        self.content_stack = QStackedWidget(self)

        # Mode 0: Editor Canvas & Drawer Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self.content_stack)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #282a35;
            }
        """)

        # Left Canvas
        self.canvas = AutomationCanvas(self.splitter)
        self.splitter.addWidget(self.canvas)

        # Right Drawer Area: Stacked widget containing Catalog and Inspector
        self.right_stack = QStackedWidget(self.splitter)
        self.right_stack.setObjectName("RightDrawerStack")
        self.right_stack.setFixedWidth(360)

        self.drawer = AutomationDrawer(self.right_stack)
        self.inspector = AutomationInspector(self.right_stack)

        self.right_stack.addWidget(self.drawer)       # Index 0: Catalog
        self.right_stack.addWidget(self.inspector)    # Index 1: Node Inspector

        self.splitter.addWidget(self.right_stack)
        self.splitter.setSizes([900, 360])
        self.content_stack.addWidget(self.splitter)   # Index 0: Editor

        # Mode 1: Executions Dashboard
        self.executions_view = AutomationExecutionsView(parent=self.content_stack)
        self.content_stack.addWidget(self.executions_view)  # Index 1: Executions

        # Mode 2: Evaluations
        self.evals_view = QWidget(self.content_stack)
        evals_layout = QVBoxLayout(self.evals_view)
        evals_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_eval = QLabel("Evaluation benchmarks & test datasets appear here.")
        lbl_eval.setStyleSheet("color: #71717a; font-size: 13px;")
        evals_layout.addWidget(lbl_eval)
        self.content_stack.addWidget(self.evals_view)  # Index 2: Evaluations

        main_layout.addWidget(self.content_stack)

        # Bottom Bar (Logs & quick info)
        self.bottom_bar = QFrame(self)
        self.bottom_bar.setFixedHeight(26)
        self.bottom_bar.setStyleSheet("""
            QFrame {
                background-color: #121318;
                border-top: 1px solid #232530;
                color: #71717a;
                font-size: 11px;
            }
        """)
        b_layout = QHBoxLayout(self.bottom_bar)
        b_layout.setContentsMargins(12, 0, 12, 0)

        self.lbl_status = QLabel("Ready • 0 nodes")
        self.lbl_status.setStyleSheet("color: #71717a;")
        b_layout.addWidget(self.lbl_status)
        b_layout.addStretch()

        lbl_zoom = QLabel("Drag canvas with middle-click / Space")
        lbl_zoom.setStyleSheet("color: #52525b;")
        b_layout.addWidget(lbl_zoom)

        main_layout.addWidget(self.bottom_bar)

    def wire_signals(self):
        # Header signals
        self.header.save_workflow_requested.connect(self.save_workflow)
        self.header.clear_workflow_requested.connect(self.clear_workflow)
        self.header.test_workflow_requested.connect(self.run_workflow)
        self.header.mode_changed.connect(self._on_mode_changed)

        # Catalog Drawer signals
        self.drawer.node_selected.connect(self._on_drawer_node_selected)
        self.drawer.closed.connect(self.hide_drawer)

        # Node Inspector signals
        self.inspector.closed.connect(self._on_inspector_closed)
        self.inspector.node_deleted.connect(lambda n: self.update_status_bar())

        # Canvas signals
        self.canvas.toggle_drawer_requested.connect(self.toggle_drawer)
        self.canvas.node_selected.connect(self._on_node_selected)
        self.canvas.node_double_clicked.connect(self._on_node_selected)
        self.canvas.graph.nodes_deleted.connect(lambda nodes: self.update_status_bar())

    def _on_drawer_node_selected(self, item_data: dict):
        """Instantiates selected node from drawer and drops onto canvas."""
        node_id = item_data.get("id")
        title = item_data.get("title", "Node")
        if node_id:
            node = self.canvas.add_node(node_id, name=title)
            if node:
                self.update_status_bar()
                self.canvas.graph.center_on([node])
                # Immediately inspect new node
                self._on_node_selected(node)

    def _on_node_selected(self, node):
        """Shows parameters and live test execution in inspector when a node is selected."""
        if node:
            self.inspector.inspect_node(node)
            self.right_stack.setCurrentIndex(1)
            self.right_stack.show()

    def _on_inspector_closed(self):
        """When inspector is closed, switch back to catalog drawer."""
        self.right_stack.setCurrentIndex(0)

    def toggle_drawer(self):
        if self.right_stack.isVisible():
            if self.right_stack.currentIndex() == 1:
                # If inspector was active, toggle back to catalog
                self.right_stack.setCurrentIndex(0)
                self.drawer.focus_search()
            else:
                self.right_stack.hide()
        else:
            self.right_stack.setCurrentIndex(0)
            self.right_stack.show()
            self.drawer.focus_search()

    def show_drawer(self):
        self.right_stack.setCurrentIndex(0)
        self.right_stack.show()
        self.drawer.focus_search()

    def hide_drawer(self):
        self.right_stack.hide()

    def update_status_bar(self):
        count = len(self.canvas.graph.all_nodes())
        name = self.header.get_workflow_name()
        self.lbl_status.setText(f"{name} • {count} node{'s' if count != 1 else ''}")

    def clear_workflow(self):
        self.canvas.clear_canvas()
        self.update_status_bar()

    def save_workflow(self) -> str:
        """Serializes current workflow canvas to a local JSON file."""
        data = self.canvas.graph.serialize_session()
        data["workflow_name"] = self.header.get_workflow_name()

        # Target directory: .lmms/workflows
        wf_dir = os.path.expanduser("~/.lmms/workflows")
        os.makedirs(wf_dir, exist_ok=True)

        slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in self.header.get_workflow_name().lower())
        file_path = os.path.join(wf_dir, f"{slug}.json")

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        self.active_file_path = file_path
        self.lbl_status.setText(f"Saved: {os.path.basename(file_path)}")
        return file_path

    def load_workflow_file(self, file_path: str):
        if not os.path.exists(file_path):
            return
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        name = data.get("workflow_name", os.path.splitext(os.path.basename(file_path))[0])
        self.header.set_workflow_name(name)
        self.canvas.graph.deserialize_session(data)
        self.canvas.update_empty_state()
        self.update_status_bar()

    def _on_mode_changed(self, mode: str):
        """Switches central view between Editor, Executions dashboard, and Evaluations."""
        if mode == "Editor":
            self.content_stack.setCurrentIndex(0)
        elif mode == "Executions":
            self.executions_view.reload_history()
            self.content_stack.setCurrentIndex(1)
        elif mode == "Evaluations":
            self.content_stack.setCurrentIndex(2)

    def run_workflow(self):
        """Executes current workflow nodes via WorkflowExecutionEngine, recording SQLite traces."""
        nodes = self.canvas.graph.all_nodes()
        if not nodes:
            self.lbl_status.setText("Cannot run: workflow has no nodes")
            return

        self.lbl_status.setText(f"Executing {len(nodes)} nodes...")
        self.header.btn_test.setEnabled(False)

        # Topological sorting: triggers first, then downstream
        triggers = [n for n in nodes if getattr(n, "CATEGORY", "") == "trigger"]
        others = [n for n in nodes if n not in triggers]
        pipeline = triggers + others

        # Create or reuse execution runner
        if not hasattr(self, "runner") or self.runner is None:
            self.runner = WorkflowExecutionEngine()

        def _on_step_update(node, status, payload):
            if hasattr(node, "set_status"):
                node.set_status(status)
            if self.inspector.current_node == node:
                self.inspector.inspect_node(node)
            self.lbl_status.setText(f"Step {status}: {node.name()}")

        async def _run_async():
            res = await self.runner.run_pipeline(
                nodes=pipeline,
                workflow_name=self.header.get_workflow_name(),
                on_step_update=_on_step_update,
            )
            self.header.btn_test.setEnabled(True)
            self.lbl_status.setText(
                f"Workflow completed: {res['status'].upper()} in {res['duration_ms']}ms ({len(pipeline)} steps)"
            )
            # Update history table
            self.executions_view.reload_history()

        run_coro_safe(_run_async())
