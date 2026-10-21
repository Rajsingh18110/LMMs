"""
lmms.gui.widgets.automation_canvas - Native Desktop Automation Canvas.
Integrates NodeGraphQt with n8n-style dark dotted aesthetics, floating controls,
empty-state quick triggers, and seamless zoom/pan navigation.
"""

from __future__ import annotations

import os
from typing import Optional, List, Dict, Any

# Ensure pure PyQt6 shims before NodeGraphQt import
import lmms.gui.vendor_patches.nodegraph_pyqt6  # noqa: F401
from NodeGraphQt import NodeGraph, BaseNode
from NodeGraphQt.constants import ViewerEnum, PipeLayoutEnum

from lmms.gui.qt import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QPoint,
    QSize,
    Qt,
    QColor,
    QCursor,
    pyqtSignal,
    QGraphicsDropShadowEffect,
)
from lmms.gui.branding import AutomationBranding


class EmptyStateWidget(QFrame):
    """
    n8n-style centered empty state when the canvas contains no nodes.
    Presents '[+] Add first step...' and '[✦] Build with AI' dashed cards.
    """
    add_step_clicked = pyqtSignal()
    build_ai_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("AutomationEmptyState")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Card 1: Add first step
        self.card_add = QFrame()
        self.card_add.setFixedSize(140, 120)
        self.card_add.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.card_add.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 24, 27, 0.75);
                border: 2px dashed #3f3f46;
                border-radius: 14px;
            }
            QFrame:hover {
                background-color: rgba(39, 39, 42, 0.9);
                border: 2px dashed #f97316;
            }
        """)
        add_layout = QVBoxLayout(self.card_add)
        add_layout.setContentsMargins(8, 12, 8, 12)
        add_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_add = QLabel("+")
        icon_add.setStyleSheet("color: #d4d4d8; font-size: 30px; font-weight: 300; background: transparent; border: none;")
        icon_add.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_add = QLabel("Add first step...")
        lbl_add.setStyleSheet("color: #e4e4e7; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        lbl_add.setAlignment(Qt.AlignmentFlag.AlignCenter)

        add_layout.addWidget(icon_add)
        add_layout.addWidget(lbl_add)

        # Separator: "or"
        lbl_or = QLabel("or")
        lbl_or.setStyleSheet("color: #71717a; font-size: 13px; font-weight: 500; background: transparent;")
        lbl_or.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Card 2: Build with AI
        self.card_ai = QFrame()
        self.card_ai.setFixedSize(140, 120)
        self.card_ai.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.card_ai.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 24, 27, 0.75);
                border: 2px dashed #3f3f46;
                border-radius: 14px;
            }
            QFrame:hover {
                background-color: rgba(39, 39, 42, 0.9);
                border: 2px dashed #8b5cf6;
            }
        """)
        ai_layout = QVBoxLayout(self.card_ai)
        ai_layout.setContentsMargins(8, 12, 8, 12)
        ai_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_ai = QLabel("✦")
        icon_ai.setStyleSheet("color: #c084fc; font-size: 26px; font-weight: 300; background: transparent; border: none;")
        icon_ai.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_ai = QLabel("Build with AI")
        lbl_ai.setStyleSheet("color: #e4e4e7; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        lbl_ai.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ai_layout.addWidget(icon_ai)
        ai_layout.addWidget(lbl_ai)

        layout.addWidget(self.card_add)
        layout.addWidget(lbl_or)
        layout.addWidget(self.card_ai)

    def mousePressEvent(self, event):
        pos = event.pos()
        if self.card_add.geometry().contains(pos):
            self.add_step_clicked.emit()
            event.accept()
            return
        elif self.card_ai.geometry().contains(pos):
            self.build_ai_clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class FloatingZoomControls(QFrame):
    """
    Bottom-left floating pill toolbar: [⛶ Fit] [− Zoom out] [+ Zoom in] [📍 Center].
    """
    fit_clicked = pyqtSignal()
    zoom_out_clicked = pyqtSignal()
    zoom_in_clicked = pyqtSignal()
    center_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("FloatingZoomControls")
        self.setStyleSheet("""
            QFrame#FloatingZoomControls {
                background-color: rgba(20, 20, 24, 0.88);
                border: 1px solid #2e2f38;
                border-radius: 8px;
            }
            QPushButton {
                background: transparent;
                color: #a1a1aa;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: 600;
                width: 28px;
                height: 28px;
            }
            QPushButton:hover {
                background-color: #32333d;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #27272a;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(2)

        self.btn_fit = QPushButton("⛶")
        self.btn_fit.setToolTip("Fit all nodes to view")
        self.btn_fit.clicked.connect(self.fit_clicked)

        self.btn_out = QPushButton("−")
        self.btn_out.setToolTip("Zoom out")
        self.btn_out.clicked.connect(self.zoom_out_clicked)

        self.btn_in = QPushButton("+")
        self.btn_in.setToolTip("Zoom in")
        self.btn_in.clicked.connect(self.zoom_in_clicked)

        self.btn_center = QPushButton("📍")
        self.btn_center.setToolTip("Reset & center canvas")
        self.btn_center.clicked.connect(self.center_clicked)

        for btn in (self.btn_fit, self.btn_out, self.btn_in, self.btn_center):
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            layout.addWidget(btn)

        self.setFixedSize(132, 36)


class FloatingToolPill(QFrame):
    """
    Top-right floating vertical pill: [+] Add node, [🔍] Search, [📁] Library, [✨] AI.
    """
    add_node_clicked = pyqtSignal()
    search_clicked = pyqtSignal()
    library_clicked = pyqtSignal()
    ai_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("FloatingToolPill")
        self.setStyleSheet("""
            QFrame#FloatingToolPill {
                background-color: rgba(20, 20, 24, 0.88);
                border: 1px solid #2e2f38;
                border-radius: 8px;
            }
            QPushButton {
                background: transparent;
                color: #a1a1aa;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                width: 28px;
                height: 28px;
            }
            QPushButton:hover {
                background-color: #32333d;
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 4, 3, 4)
        layout.setSpacing(3)

        self.btn_add = QPushButton("+")
        self.btn_add.setToolTip("Add node to workflow")
        self.btn_add.clicked.connect(self.add_node_clicked)

        self.btn_search = QPushButton("🔍")
        self.btn_search.setToolTip("Search nodes")
        self.btn_search.clicked.connect(self.search_clicked)

        self.btn_lib = QPushButton("📁")
        self.btn_lib.setToolTip("Workflow templates")
        self.btn_lib.clicked.connect(self.library_clicked)

        self.btn_ai = QPushButton("✨")
        self.btn_ai.setToolTip("AI Workflow Generator")
        self.btn_ai.setStyleSheet("color: #c084fc;")
        self.btn_ai.clicked.connect(self.ai_clicked)

        for btn in (self.btn_add, self.btn_search, self.btn_lib, self.btn_ai):
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            layout.addWidget(btn)

        self.setFixedSize(36, 136)


class AutomationCanvas(QWidget):
    """
    Main n8n-style Automation Canvas widget.
    Encapsulates NodeGraphQt, floating controls, empty-state cues, and overlays.
    """
    open_chat_requested = pyqtSignal()
    toggle_drawer_requested = pyqtSignal()
    node_selected = pyqtSignal(object)
    node_double_clicked = pyqtSignal(object)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("AutomationCanvas")

        self.init_graph()
        self.init_ui()
        self.init_overlays()

    def init_graph(self):
        """Configure NodeGraph with n8n visual tokens."""
        self.graph = NodeGraph()
        self.graph.set_grid_mode(ViewerEnum.GRID_DISPLAY_DOTS.value)
        self.graph.set_background_color(18, 18, 20)      # #121214
        self.graph.set_grid_color(42, 43, 48)            # #2a2b30
        self.graph.set_pipe_style(PipeLayoutEnum.CURVED.value)

        # Register custom nodes
        from lmms.gui.widgets.automation_nodes import register_all_nodes
        register_all_nodes(self.graph)

        # Wire node events
        self.graph.node_selected.connect(self._on_node_selected)
        self.graph.node_double_clicked.connect(self._on_node_double_clicked)
        self.graph.nodes_deleted.connect(lambda nodes: self.update_empty_state())

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Embed the NodeGraph widget
        self.graph_widget = self.graph.widget
        main_layout.addWidget(self.graph_widget)

    def init_overlays(self):
        """Construct floating overlay widgets on top of the graphics view."""
        # 1. Empty State
        self.empty_state = EmptyStateWidget(self)
        self.empty_state.add_step_clicked.connect(self.toggle_drawer_requested)
        self.empty_state.build_ai_clicked.connect(self._on_build_ai)
        self.empty_state.resize(340, 140)
        self.empty_state.raise_()

        # 2. Bottom-left Zoom Controls
        self.zoom_controls = FloatingZoomControls(self)
        self.zoom_controls.fit_clicked.connect(self.fit_view)
        self.zoom_controls.zoom_out_clicked.connect(self.zoom_out)
        self.zoom_controls.zoom_in_clicked.connect(self.zoom_in)
        self.zoom_controls.center_clicked.connect(self.reset_view)
        self.zoom_controls.raise_()

        # 3. Bottom-center Open Chat Button
        self.btn_open_chat = QPushButton("💬  Open chat", self)
        self.btn_open_chat.setObjectName("BtnOpenChat")
        self.btn_open_chat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_open_chat.setStyleSheet("""
            QPushButton#BtnOpenChat {
                background-color: #f97316;
                color: #ffffff;
                font-size: 13px;
                font-weight: 600;
                padding: 7px 18px;
                border: none;
                border-radius: 8px;
            }
            QPushButton#BtnOpenChat:hover {
                background-color: #ea580c;
            }
            QPushButton#BtnOpenChat:pressed {
                background-color: #c2410c;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self.btn_open_chat)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 4)
        self.btn_open_chat.setGraphicsEffect(shadow)
        self.btn_open_chat.clicked.connect(self.open_chat_requested)
        self.btn_open_chat.adjustSize()
        self.btn_open_chat.raise_()

        # 4. Top-right Floating Tool Pill
        self.tool_pill = FloatingToolPill(self)
        self.tool_pill.add_node_clicked.connect(self.toggle_drawer_requested)
        self.tool_pill.search_clicked.connect(self.toggle_drawer_requested)
        self.tool_pill.library_clicked.connect(self.toggle_drawer_requested)
        self.tool_pill.ai_clicked.connect(self._on_build_ai)
        self.tool_pill.raise_()

        self.update_empty_state()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()

        # Center empty state
        es_w, es_h = self.empty_state.width(), self.empty_state.height()
        self.empty_state.move(int((w - es_w) / 2), int((h - es_h) / 2))

        # Bottom-left controls
        self.zoom_controls.move(20, h - 52)

        # Bottom-center open chat button
        btn_w = self.btn_open_chat.width()
        self.btn_open_chat.move(int((w - btn_w) / 2), h - 50)

        # Top-right tool pill
        self.tool_pill.move(w - 52, 20)

    def update_empty_state(self):
        """Shows or hides the empty state based on whether canvas has nodes."""
        has_nodes = len(self.graph.all_nodes()) > 0
        self.empty_state.setVisible(not has_nodes)

    def fit_view(self):
        """Fits all nodes or selection into viewer."""
        viewer = self.graph.viewer()
        nodes = self.graph.selected_nodes() or self.graph.all_nodes()
        if nodes:
            viewer.zoom_to_nodes(nodes)
        else:
            self.reset_view()

    def zoom_in(self):
        viewer = self.graph.viewer()
        current = viewer.get_zoom()
        viewer.set_zoom(min(current + 0.15, 1.0))

    def zoom_out(self):
        viewer = self.graph.viewer()
        current = viewer.get_zoom()
        viewer.set_zoom(max(current - 0.15, -0.9))

    def reset_view(self):
        self.graph.reset_zoom()
        self.graph.clear_selection()

    def _on_node_selected(self, node):
        self.node_selected.emit(node)

    def _on_node_double_clicked(self, node):
        self.node_double_clicked.emit(node)

    def _on_build_ai(self):
        self.toggle_drawer_requested.emit()

    def add_node(self, node_type: str, name: Optional[str] = None, pos: Optional[List[float]] = None) -> Optional[BaseNode]:
        """Convenience helper to create and place a node on canvas."""
        viewer = self.graph.viewer()
        if pos is None:
            # Place near center of viewport
            c_pos = viewer.scene_center()
            offset = len(self.graph.all_nodes()) * 40
            cx = c_pos[0] if isinstance(c_pos, (list, tuple)) else getattr(c_pos, "x", lambda: 0)()
            cy = c_pos[1] if isinstance(c_pos, (list, tuple)) else getattr(c_pos, "y", lambda: 0)()
            pos = [float(cx + offset), float(cy)]

        try:
            node = self.graph.create_node(node_type, name=name, pos=pos)
            self.update_empty_state()
            return node
        except Exception as e:
            import sys
            sys.stderr.write(f"[AutomationCanvas] Failed to create node {node_type}: {e}\n")
            return None

    def clear_canvas(self):
        self.graph.clear_session()
        self.update_empty_state()
