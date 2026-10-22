"""
lmms.gui.panel - Dedicated Workflow Canvas & Visual Execution GUI.
Provides an n8n-style interactive node canvas powered by PyQt6 QGraphicsView/Scene.
Listens to live events from LMMs Event Bus and animates active nodes, data flows,
diff previews, and execution status in real-time.
"""

from __future__ import annotations

import os
import sys
import json
import time
import math
import socket
import argparse
import threading
from typing import Dict, Any, List, Optional, Tuple

from lmms.gui.qt import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QComboBox,
    QFrame,
    QMessageBox,
    QSplitter,
    QTextEdit,
    QPlainTextEdit,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsPathItem,
    QGraphicsDropShadowEffect,
    QPainter,
    QPainterPath,
    QColor,
    QPen,
    QBrush,
    QFont,
    QTimer,
    QRectF,
    QPointF,
    Qt,
    pyqtSignal,
    pyqtSlot,
)


class NodeState:
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAIL = "fail"
    WAITING_APPROVAL = "waiting_approval"


NODE_COLORS = {
    NodeState.PENDING: {"bg": QColor(30, 34, 42), "border": QColor(70, 78, 92), "text": QColor(160, 174, 192), "glow": QColor(0, 0, 0, 0)},
    NodeState.RUNNING: {"bg": QColor(26, 44, 76), "border": QColor(66, 153, 225), "text": QColor(235, 248, 255), "glow": QColor(66, 153, 225, 180)},
    NodeState.SUCCESS: {"bg": QColor(24, 52, 38), "border": QColor(72, 187, 120), "text": QColor(240, 255, 244), "glow": QColor(72, 187, 120, 160)},
    NodeState.FAIL: {"bg": QColor(60, 25, 25), "border": QColor(245, 101, 101), "text": QColor(255, 245, 245), "glow": QColor(245, 101, 101, 180)},
    NodeState.WAITING_APPROVAL: {"bg": QColor(65, 50, 15), "border": QColor(234, 179, 8), "text": QColor(254, 240, 138), "glow": QColor(234, 179, 8, 180)},
}


class CanvasNode(QGraphicsItem):
    """Interactive workflow node drawn on the QGraphicsScene."""

    def __init__(self, node_id: str, title: str, subtitle: str, x: float, y: float, parent_canvas: Any):
        super().__init__()
        self.node_id = node_id
        self.title = title
        self.subtitle = subtitle
        self.state = NodeState.PENDING
        self.payload: Dict[str, Any] = {}
        self.parent_canvas = parent_canvas
        self.pulse_phase = 0.0

        self.width = 180.0
        self.height = 70.0

        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        )
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        return QRectF(-10, -10, self.width + 20, self.height + 20)

    def paint(self, painter: QPainter, option: Any, widget: Any = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = NODE_COLORS[self.state]

        # Pulse glow effect when RUNNING
        if self.state == NodeState.RUNNING:
            pulse_rad = 6.0 + 3.0 * math.sin(self.pulse_phase)
            glow_pen = QPen(c["glow"], pulse_rad)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(0, 0, self.width, self.height), 12, 12)

        # Main node body
        painter.setPen(QPen(c["border"], 2.0 if self.state != NodeState.RUNNING else 2.5))
        painter.setBrush(QBrush(c["bg"]))
        painter.drawRoundedRect(QRectF(0, 0, self.width, self.height), 10, 10)

        # Title
        painter.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        painter.setPen(c["text"])
        painter.drawText(QRectF(14, 12, self.width - 28, 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.title)

        # Subtitle
        painter.setFont(QFont("Inter", 8, QFont.Weight.Normal))
        painter.setPen(QColor(160, 174, 192))
        painter.drawText(QRectF(14, 36, self.width - 28, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.subtitle)

        # Connection ports
        port_pen = QPen(c["border"], 2)
        port_brush = QBrush(c["bg"])
        painter.setPen(port_pen)
        painter.setBrush(port_brush)
        # In-port (left)
        painter.drawEllipse(QPointF(0, self.height / 2), 4, 4)
        # Out-port (right)
        painter.drawEllipse(QPointF(self.width, self.height / 2), 4, 4)

    def mousePressEvent(self, event: Any):
        super().mousePressEvent(event)
        self.parent_canvas.on_node_clicked(self)

    def set_state(self, state: str, subtitle: Optional[str] = None, payload: Optional[Dict[str, Any]] = None):
        old_state = self.state
        self.state = state
        if subtitle:
            self.subtitle = subtitle
        if payload is not None:
            self.payload = payload
        self.update()

        try:
            log_entry = {
                "timestamp": time.time(),
                "datetime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
                "node_id": self.node_id,
                "old_state": old_state,
                "new_state": state,
                "subtitle": self.subtitle
            }
            log_path = os.path.expanduser("~/.lmms/events/panel_node_states.jsonl")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            pass


class FlowConnection(QGraphicsPathItem):
    """Curved cubic bezier connection between two workflow nodes with animated particle flow."""

    def __init__(self, source_node: CanvasNode, target_node: CanvasNode):
        super().__init__()
        self.source = source_node
        self.target = target_node
        self.progress = 0.0  # 0.0 to 1.0 along the path
        self.is_flowing = False
        self.flow_color = QColor(66, 153, 225)

        self.setZValue(-1)
        self.update_path()

    def update_path(self):
        start = self.source.pos() + QPointF(self.source.width, self.source.height / 2)
        end = self.target.pos() + QPointF(0, self.target.height / 2)

        path = QPainterPath(start)
        dx = (end.x() - start.x()) * 0.5
        c1 = QPointF(start.x() + dx, start.y())
        c2 = QPointF(end.x() - dx, end.y())
        path.cubicTo(c1, c2, end)
        self.setPath(path)

    def paint(self, painter: QPainter, option: Any, widget: Any = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.update_path()

        # Base connection line
        is_active = self.source.state in (NodeState.RUNNING, NodeState.SUCCESS)
        line_color = QColor(66, 153, 225, 200) if is_active else QColor(55, 65, 81, 160)
        line_pen = QPen(line_color, 2.0, Qt.PenStyle.DashLine if not is_active else Qt.PenStyle.SolidLine)
        painter.setPen(line_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        # Animated flowing particle dot
        if self.is_flowing:
            pt = self.path().pointAtPercent(self.progress)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self.flow_color))
            painter.drawEllipse(pt, 4.5, 4.5)
            # Particle glow
            glow = QColor(self.flow_color.red(), self.flow_color.green(), self.flow_color.blue(), 100)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(pt, 8.0, 8.0)


class WorkflowCanvasView(QGraphicsView):
    """Grid-background viewport for n8n-style nodes."""

    def __init__(self, scene: QGraphicsScene):
        super().__init__(scene)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setBackgroundBrush(QBrush(QColor(18, 21, 26)))

    def drawBackground(self, painter: QPainter, rect: QRectF):
        super().drawBackground(painter, rect)
        # Dark dot grid
        grid_size = 24
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        painter.setPen(QPen(QColor(40, 46, 56), 1.5))
        for x in range(left, int(rect.right()), grid_size):
            for y in range(top, int(rect.bottom()), grid_size):
                painter.drawPoint(x, y)


class EventWorker(threading.Thread):
    """Background listener that feeds real events from LMMs Event Bus to the GUI."""

    def __init__(self, callback, socket_path: Optional[str] = None, jsonl_path: Optional[str] = None):
        super().__init__(daemon=True)
        self.callback = callback
        self.socket_path = socket_path or os.path.expanduser("~/.lmms/events/lmms_events.sock")
        self.jsonl_path = jsonl_path or os.path.expanduser("~/.lmms/events/live_events.jsonl")
        self.running = True

    def run(self):
        # First tail existing jsonl if available
        last_pos = 0
        if os.path.exists(self.jsonl_path):
            try:
                last_pos = os.path.getsize(self.jsonl_path)
            except OSError:
                pass

        sock = None
        while self.running:
            # Try connecting to live UNIX socket
            if sock is None and os.path.exists(self.socket_path):
                try:
                    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    sock.connect(self.socket_path)
                    sock.settimeout(0.5)
                except Exception:
                    sock = None

            if sock is not None:
                try:
                    data = sock.recv(4096)
                    if data:
                        for line in data.decode("utf-8", errors="ignore").splitlines():
                            if line.strip():
                                try:
                                    event = json.loads(line)
                                    self.callback(event)
                                except Exception:
                                    pass
                    else:
                        sock.close()
                        sock = None
                except socket.timeout:
                    pass
                except Exception:
                    try:
                        sock.close()
                    except Exception:
                        pass
                    sock = None
            else:
                # Fallback: poll JSONL file
                if os.path.exists(self.jsonl_path):
                    try:
                        curr_size = os.path.getsize(self.jsonl_path)
                        if curr_size > last_pos:
                            with open(self.jsonl_path, "r", encoding="utf-8", errors="ignore") as f:
                                f.seek(last_pos)
                                lines = f.readlines()
                                last_pos = f.tell()
                            for line in lines:
                                if line.strip():
                                    try:
                                        event = json.loads(line)
                                        self.callback(event)
                                    except Exception:
                                        pass
                    except Exception:
                        pass
                time.sleep(0.05)


class PanelWindow(QMainWindow):
    """Main Automation Canvas Window for /panel."""

    event_received = pyqtSignal(dict)

    def __init__(self, test_mode: bool = False):
        super().__init__()
        self.test_mode = test_mode
        self.setWindowTitle("LMMs OS — Automation Canvas (/panel)")
        self.resize(1100, 680)

        self.scene = QGraphicsScene(-50, -50, 1100, 650)
        self.view = WorkflowCanvasView(self.scene)

        self.nodes: Dict[str, CanvasNode] = {}
        self.connections: List[FlowConnection] = []

        self._init_ui()
        self._build_workflow_pipeline()

        # 60fps animation timer
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_animation_frame)
        self.anim_timer.start(16)

        # Wire event receiver signal
        self.event_received.connect(self.handle_event)

        # Start live event listener
        self.worker = EventWorker(self._emit_event_safe)
        self.worker.start()

    def _emit_event_safe(self, event: Dict[str, Any]):
        self.event_received.emit(event)

    def _init_ui(self):
        # Dark style
        self.setStyleSheet("""
            QMainWindow { background-color: #12151a; }
            QWidget { color: #e2e8f0; font-family: 'Inter', 'Segoe UI', sans-serif; }
            QPushButton {
                background-color: #2d3748;
                border: 1px solid #4a5568;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                color: #edf2f7;
            }
            QPushButton:hover { background-color: #4a5568; }
            QPushButton:pressed { background-color: #1a202c; }
            QTextEdit, QPlainTextEdit {
                background-color: #1a202c;
                border: 1px solid #2d3748;
                border-radius: 6px;
                color: #e2e8f0;
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
                font-size: 11px;
            }
            QLabel { font-weight: 500; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Top Toolbar
        top_bar = QHBoxLayout()
        title_lbl = QLabel("⚡ <b>Automation Canvas</b> <span style='color:#718096;'>| n8n-Style Native Studio</span>")
        top_bar.addWidget(title_lbl)
        top_bar.addSpacing(16)

        # Workflow selector
        self.wf_combo = QComboBox()
        self.wf_combo.setStyleSheet("""
            QComboBox {
                background-color: #1f2937;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 4px 10px;
                color: #f3f4f6;
                font-size: 12px;
                min-width: 180px;
            }
        """)
        self._populate_workflows_combo()
        top_bar.addWidget(self.wf_combo)

        # Run Workflow button
        self.btn_run_wf = QPushButton("▶ Run Workflow")
        self.btn_run_wf.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                border: 1px solid #10b981;
                border-radius: 6px;
                padding: 5px 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #10b981; }
            QPushButton:disabled { background-color: #374151; color: #9ca3af; }
        """)
        self.btn_run_wf.clicked.connect(self._run_selected_workflow)
        top_bar.addWidget(self.btn_run_wf)

        self.btn_export = QPushButton("Export JSON")
        self.btn_export.clicked.connect(self._export_selected_workflow)
        top_bar.addWidget(self.btn_export)

        top_bar.addStretch()

        self.status_badge = QLabel("<span style='color:#48bb78;'>● Connected (Live Bus)</span>")
        top_bar.addWidget(self.status_badge)

        self.step_mode_chk = QCheckBox("Single-Step Mode")
        top_bar.addWidget(self.step_mode_chk)

        self.pause_btn = QPushButton("Pause Loop")
        self.pause_btn.clicked.connect(self._toggle_pause)
        top_bar.addWidget(self.pause_btn)

        clear_btn = QPushButton("Reset Canvas")
        clear_btn.clicked.connect(self._reset_canvas)
        top_bar.addWidget(clear_btn)

        main_layout.addLayout(top_bar)

        # Approval Gate Action Banner (Hidden until gate paused)
        self.approval_banner = QFrame()
        self.approval_banner.setStyleSheet("""
            QFrame {
                background-color: #2b2311;
                border: 1px solid #eab308;
                border-radius: 8px;
                padding: 6px 12px;
            }
        """)
        ab_layout = QHBoxLayout(self.approval_banner)
        ab_layout.setContentsMargins(8, 4, 8, 4)
        ab_layout.setSpacing(12)

        self.lbl_approval_msg = QLabel("<b>⚠️ APPROVAL REQUIRED:</b> Workflow paused at human review gate.")
        self.lbl_approval_msg.setStyleSheet("color: #fef08a; font-size: 12px;")
        ab_layout.addWidget(self.lbl_approval_msg)
        ab_layout.addStretch()

        self.btn_approve = QPushButton("✔ Approve & Resume")
        self.btn_approve.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 5px 14px;
            }
            QPushButton:hover { background-color: #22c55e; }
        """)
        self.btn_approve.clicked.connect(self._on_approve_gate)
        ab_layout.addWidget(self.btn_approve)

        self.btn_deny = QPushButton("✖ Reject & Abort")
        self.btn_deny.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 5px 14px;
            }
            QPushButton:hover { background-color: #ef4444; }
        """)
        self.btn_deny.clicked.connect(self._on_deny_gate)
        ab_layout.addWidget(self.btn_deny)

        self.approval_banner.setVisible(False)
        main_layout.addWidget(self.approval_banner)

        # Splitter: Canvas View on Left, Details Inspector on Right
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.view)

        # Right Inspector Panel
        inspector = QWidget()
        ins_layout = QVBoxLayout(inspector)
        ins_layout.setContentsMargins(8, 0, 0, 0)
        ins_layout.setSpacing(6)

        ins_title = QLabel("<b>Node Inspector</b>")
        ins_layout.addWidget(ins_title)

        self.inspector_summary = QLabel("<span style='color:#a0aec0;'>Click any node on the canvas to inspect its arguments, live outputs, and AST diffs.</span>")
        self.inspector_summary.setWordWrap(True)
        ins_layout.addWidget(self.inspector_summary)

        self.payload_view = QPlainTextEdit()
        self.payload_view.setReadOnly(True)
        self.payload_view.setPlaceholderText("Node payload details will appear here...")
        ins_layout.addWidget(self.payload_view)

        splitter.addWidget(inspector)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

    def _populate_workflows_combo(self):
        self.wf_combo.clear()
        try:
            from lmms_workflow.store import default_workflow_store
            wfs = default_workflow_store.list_workflows(include_builtins=True)
            for w in wfs:
                self.wf_combo.addItem(f"{w['name']} ({w['id']})", w['id'])
        except Exception:
            self.wf_combo.addItem("Default Agent Pipeline", "default")

    def _render_workflow_dag(self, wf: Any):
        """Dynamically renders workflow nodes and curved connections on the scene."""
        self.scene.clear()
        self.nodes.clear()
        self.connections.clear()

        import networkx as nx
        from lmms_workflow.engine import WorkflowEngine
        engine = WorkflowEngine()
        dag = engine.build_dag(wf)
        generations = list(nx.topological_generations(dag))

        x_start = 40
        y_start = 140
        col_width = 240
        row_height = 110

        for col_idx, gen in enumerate(generations):
            x = x_start + (col_idx * col_width)
            total_in_col = len(gen)
            for row_idx, nid in enumerate(gen):
                y = y_start + (row_idx * row_height) - ((total_in_col - 1) * 35)
                wnode = wf.nodes[nid]
                title = wnode.name[:20]
                sub = f"Type: {wnode.node_type.value}"
                cnode = CanvasNode(nid, title, sub, x, y, self)
                self.scene.addItem(cnode)
                self.nodes[nid] = cnode

        for edge in wf.edges:
            if edge.source_node in self.nodes and edge.target_node in self.nodes:
                conn = FlowConnection(self.nodes[edge.source_node], self.nodes[edge.target_node])
                self.scene.addItem(conn)
                self.connections.append(conn)

    def _run_selected_workflow(self):
        wid = self.wf_combo.currentData()
        if not wid:
            return
        from lmms_workflow.store import default_workflow_store
        from lmms_workflow.engine import WorkflowEngine
        from lmms_workflow.models import NodeStatus

        wf = default_workflow_store.get_workflow(wid)
        if not wf:
            self.inspector_summary.setText(f"<span style='color:#f56565;'>Workflow '{wid}' not found.</span>")
            return

        self._render_workflow_dag(wf)
        self.btn_run_wf.setEnabled(False)
        self.btn_run_wf.setText("Running...")
        self.status_badge.setText("<span style='color:#4299e1;'>● Executing DAG...</span>")
        self.approval_banner.setVisible(False)

        engine = WorkflowEngine(workspace_root=os.getcwd())
        self.active_engine = engine
        self.active_wf = wf

        def _on_engine_event(evt_name, payload):
            self.event_received.emit({"type": f"engine_{evt_name}", "data": payload})

        engine.add_listener(_on_engine_event)

        def _worker():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                run = loop.run_until_complete(engine.execute(wf))
                default_workflow_store.save_run(run)
                self.active_run = run
                QTimer.singleShot(0, lambda: self._on_workflow_finished(run))
            except Exception as e:
                err_text = str(e)
                QTimer.singleShot(0, lambda: self._on_workflow_error(err_text))
            finally:
                loop.close()

        threading.Thread(target=_worker, daemon=True).start()

    def _on_workflow_finished(self, run: Any):
        from lmms_workflow.models import NodeStatus
        self.btn_run_wf.setEnabled(True)
        self.btn_run_wf.setText("▶ Run Workflow")

        for nid, res in run.results.items():
            if nid in self.nodes:
                st = NodeState.SUCCESS if res.status == NodeStatus.SUCCESS else (
                    NodeState.WAITING_APPROVAL if res.status == NodeStatus.WAITING_APPROVAL else NodeState.FAIL
                )
                self.nodes[nid].set_state(st, f"{res.duration_ms:.0f}ms • {res.status.value}", {
                    "output": res.output,
                    "error": res.error,
                    "status": res.status.value,
                    "duration_ms": res.duration_ms,
                })

        if run.status == NodeStatus.WAITING_APPROVAL and run.pending_approval:
            self.status_badge.setText("<span style='color:#ecc94b;'>⏸ Waiting Approval</span>")
            self.lbl_approval_msg.setText(f"<b>⚠️ APPROVAL REQUIRED:</b> Gate <code>{run.pending_approval}</code> requires operator review.")
            self.approval_banner.setVisible(True)
            if run.pending_approval in self.nodes:
                self.on_node_clicked(self.nodes[run.pending_approval])
        elif run.status == NodeStatus.SUCCESS:
            self.status_badge.setText("<span style='color:#48bb78;'>✔ Completed Successfully</span>")
        else:
            self.status_badge.setText("<span style='color:#f56565;'>✖ Workflow Failed</span>")

    def _on_workflow_error(self, err_msg: str):
        self.btn_run_wf.setEnabled(True)
        self.btn_run_wf.setText("▶ Run Workflow")
        self.status_badge.setText(f"<span style='color:#f56565;'>✖ Error</span>")
        self.inspector_summary.setText(f"<span style='color:#f56565;'>Execution error: {err_msg}</span>")

    def _on_approve_gate(self):
        self.approval_banner.setVisible(False)
        if not hasattr(self, "active_run") or not self.active_run or not self.active_run.pending_approval:
            return

        run = self.active_run
        wf = self.active_wf
        gate_nid = run.pending_approval
        engine = self.active_engine

        self.btn_run_wf.setEnabled(False)
        self.btn_run_wf.setText("Resuming...")
        self.status_badge.setText("<span style='color:#4299e1;'>● Resuming DAG...</span>")

        def _resume():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                res_run = loop.run_until_complete(engine.approve_gate(wf, run, gate_nid, approved=True))
                from lmms_workflow.store import default_workflow_store
                default_workflow_store.save_run(res_run)
                self.active_run = res_run
                QTimer.singleShot(0, lambda: self._on_workflow_finished(res_run))
            finally:
                loop.close()

        threading.Thread(target=_resume, daemon=True).start()

    def _on_deny_gate(self):
        self.approval_banner.setVisible(False)
        if hasattr(self, "active_run") and self.active_run and self.active_run.pending_approval:
            gate_nid = self.active_run.pending_approval
            if gate_nid in self.nodes:
                self.nodes[gate_nid].set_state(NodeState.FAIL, "Approval denied", {"status": "denied by user"})
            self.status_badge.setText("<span style='color:#f56565;'>✖ Gate Rejected by User</span>")
            self.btn_run_wf.setEnabled(True)
            self.btn_run_wf.setText("▶ Run Workflow")

    def _export_selected_workflow(self):
        wid = self.wf_combo.currentData()
        if not wid:
            return
        from lmms_workflow.store import default_workflow_store
        wf = default_workflow_store.get_workflow(wid)
        if wf:
            out_file = f"{wid}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(wf.to_json())
            self.inspector_summary.setText(f"<span style='color:#48bb78;'>✔ Workflow exported to {os.path.abspath(out_file)}</span>")

    def _build_workflow_pipeline(self):
        """Construct the 7 primary execution graph nodes with curved connections."""
        pipeline_defs = [
            ("user_input", "User Input", "Awaiting prompt", 30, 220),
            ("planner", "RuleRouter", "Intent analysis", 240, 220),
            ("tool_call", "Tool Execution", "ReAct tool loop", 450, 140),
            ("patch_engine", "Patch Engine", "AST diff guard", 660, 140),
            ("sandbox_run", "Sandbox Run", "bwrap isolation", 450, 310),
            ("test_verify", "Test Verifier", "pytest / unittest", 660, 310),
            ("response", "Response", "Final answer", 870, 220),
        ]

        for nid, title, sub, x, y in pipeline_defs:
            node = CanvasNode(nid, title, sub, x, y, self)
            self.scene.addItem(node)
            self.nodes[nid] = node

        # Connections
        edges = [
            ("user_input", "planner"),
            ("planner", "tool_call"),
            ("planner", "sandbox_run"),
            ("tool_call", "patch_engine"),
            ("sandbox_run", "test_verify"),
            ("patch_engine", "test_verify"),
            ("test_verify", "response"),
            ("patch_engine", "response"),
        ]

        for src_id, dst_id in edges:
            conn = FlowConnection(self.nodes[src_id], self.nodes[dst_id])
            self.scene.addItem(conn)
            self.connections.append(conn)

    def _on_animation_frame(self):
        for node in self.nodes.values():
            if node.state == NodeState.RUNNING:
                node.pulse_phase += 0.08
                node.update()

        for conn in self.connections:
            if conn.is_flowing:
                conn.progress += 0.02
                if conn.progress > 1.0:
                    conn.progress = 0.0
                conn.update()

    def on_node_clicked(self, node: CanvasNode):
        self.inspector_summary.setText(f"<b>{node.title}</b> — Status: <code>{node.state.upper()}</code><br><span style='color:#a0aec0;'>{node.subtitle}</span>")
        payload_str = json.dumps(node.payload, indent=2) if node.payload else "(No execution payload recorded yet)"
        self.payload_view.setPlainText(payload_str)

    def _toggle_pause(self):
        if self.pause_btn.text() == "Pause Loop":
            self.pause_btn.setText("Resume Loop")
            self.status_badge.setText("<span style='color:#ecc94b;'>⏸ Paused by User</span>")
        else:
            self.pause_btn.setText("Pause Loop")
            self.status_badge.setText("<span style='color:#48bb78;'>● Connected (Live Bus)</span>")

    def _reset_canvas(self):
        for node in self.nodes.values():
            node.set_state(NodeState.PENDING, "Ready", {})
        for conn in self.connections:
            conn.is_flowing = False
            conn.update()
        self.inspector_summary.setText("Canvas reset.")
        self.payload_view.clear()

    @pyqtSlot(dict)
    def handle_event(self, event: Dict[str, Any]):
        etype = event.get("type", "")

        if etype == "turn_start":
            self._reset_canvas()
            prompt = event.get("prompt", "")
            self.nodes["user_input"].set_state(NodeState.SUCCESS, prompt[:25] or "Prompt received", event)
            self.nodes["planner"].set_state(NodeState.RUNNING, "Planning steps...")
            self._set_flow("user_input", "planner", True)

        elif etype == "execution_graph_planned":
            intent = event.get("intent", "general")
            self.nodes["planner"].set_state(NodeState.SUCCESS, f"Intent: {intent}", event)
            self._set_flow("planner", "tool_call", True)
            self._set_flow("planner", "sandbox_run", True)

        elif etype == "tool_start":
            tname = event.get("tool", "")
            kwargs = event.get("kwargs", {})
            self.nodes["tool_call"].set_state(NodeState.RUNNING, f"Running: {tname}", event)
            self._set_flow("planner", "tool_call", True)

            if "terminal" in tname:
                self.nodes["sandbox_run"].set_state(NodeState.RUNNING, kwargs.get("command", "")[:25], kwargs)

        elif etype == "tool_end":
            tname = event.get("tool", "")
            success = event.get("success", True)
            output = event.get("output", "")
            st = NodeState.SUCCESS if success else NodeState.FAIL
            self.nodes["tool_call"].set_state(st, f"{tname} ({'✓' if success else '✗'})", event)

        elif etype == "patch_applied":
            mods = event.get("files_modified", event.get("files", []))
            diff = event.get("diff_summary", event.get("diff", ""))
            self.nodes["patch_engine"].set_state(NodeState.SUCCESS, f"Modified {len(mods)} file(s)", event)
            self._set_flow("tool_call", "patch_engine", True)
            self._set_flow("patch_engine", "test_verify", True)

        elif etype == "test_result":
            exit_code = event.get("exit_code", 0)
            passed = event.get("passed", exit_code == 0)
            cmd = event.get("command", "")
            st = NodeState.SUCCESS if passed else NodeState.FAIL
            self.nodes["test_verify"].set_state(st, f"{'PASS' if passed else 'FAIL'}: {cmd[:18]}", event)
            if "sandbox_run" in self.nodes:
                self.nodes["sandbox_run"].set_state(st, f"{'Exit 0' if passed else f'Exit {exit_code}'}", event)
            self._set_flow("test_verify", "response", True)

        elif etype == "turn_end":
            summary = event.get("summary", "Complete")
            self.nodes["response"].set_state(NodeState.SUCCESS, summary[:25], event)

        elif etype == "engine_node_start":
            data = event.get("data", {})
            nid = data.get("node_id")
            if nid in self.nodes:
                self.nodes[nid].set_state(NodeState.RUNNING, "Executing...")
                for conn in self.connections:
                    if conn.target.node_id == nid:
                        conn.is_flowing = True
                        conn.update()

        elif etype == "engine_node_end":
            data = event.get("data", {})
            nid = data.get("node_id")
            st_val = data.get("status")
            if nid in self.nodes:
                st = NodeState.SUCCESS if st_val == "success" else (
                    NodeState.WAITING_APPROVAL if st_val == "waiting_approval" else NodeState.FAIL
                )
                dur = data.get("duration_s", 0) * 1000.0
                self.nodes[nid].set_state(st, f"{dur:.0f}ms • {st_val}", data)
                for conn in self.connections:
                    if conn.source.node_id == nid:
                        conn.is_flowing = False
                        conn.update()

        elif etype == "error":
            err_msg = event.get("message", "Error")
            self.nodes["tool_call"].set_state(NodeState.FAIL, err_msg[:25], event)

    def _set_flow(self, src_id: str, dst_id: str, flowing: bool):
        for conn in self.connections:
            if conn.source.node_id == src_id and conn.target.node_id == dst_id:
                conn.is_flowing = flowing
                conn.update()

    def run_synthetic_test(self, output_screenshot_path: str = "panel_test.png"):
        """Executes a simulated workflow across all nodes and captures a screenshot."""
        self.handle_event({"type": "turn_start", "prompt": "Implement quicksort algorithm in python and verify"})
        self.handle_event({"type": "execution_graph_planned", "intent": "coding", "steps": []})
        self.handle_event({"type": "tool_start", "tool": "files.write", "kwargs": {"path": "quicksort.py"}})
        self.handle_event({"type": "tool_end", "tool": "files.write", "success": True, "output": "File written"})
        self.handle_event({"type": "patch_applied", "files_modified": ["quicksort.py"], "diff_summary": "+++ quicksort.py"})
        self.handle_event({"type": "tool_start", "tool": "terminal.run", "kwargs": {"command": "pytest test_quicksort.py"}})
        self.handle_event({"type": "test_result", "command": "pytest test_quicksort.py", "passed": True, "output": "3 passed in 0.04s"})
        self.handle_event({"type": "turn_end", "summary": "Quicksort implemented and verified successfully"})

        # Select the patch engine node to show inspector details
        self.on_node_clicked(self.nodes["patch_engine"])

        # Force render
        QApplication.processEvents()
        time.sleep(0.1)
        QApplication.processEvents()

        # Capture screenshot
        pixmap = self.grab()
        pixmap.save(output_screenshot_path)
        print(f"[Panel Test] Headless screenshot captured successfully: {output_screenshot_path}")


def main():
    parser = argparse.ArgumentParser(description="LMMs Automation Canvas (/panel)")
    parser.add_argument("--test", action="store_true", help="Run synthetic headless test and capture screenshot")
    parser.add_argument("--output", type=str, default="panel_test.png", help="Path to save test screenshot")
    args = parser.parse_args()

    # Graceful degradation for headless environments without display
    if not args.test and "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ:
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            print("[bold yellow]Warning:[/bold yellow] No display available ($DISPLAY or $WAYLAND_DISPLAY not set).")
            print("The /panel GUI requires a graphical session (X11 or Wayland).")
            print("Tip: Run in headless mode using: QT_QPA_PLATFORM=offscreen python -m lmms.gui.panel --test")
            sys.exit(0)

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    window = PanelWindow(test_mode=args.test)

    if args.test:
        window.show()
        window.run_synthetic_test(output_screenshot_path=args.output)
        sys.exit(0)
    else:
        window.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
