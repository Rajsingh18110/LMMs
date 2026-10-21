"""
lmms.gui.widgets.automation_card_item - Custom n8n-style QGraphicsItem for nodes.
Renders rounded cards with category color strips, status rings (idle, running, success, error),
and a top floating mini-toolbar [▶][⏻][🗑][✨][⋯].
"""

from __future__ import annotations

import math
from typing import Optional, Dict, Any

import lmms.gui.vendor_patches.nodegraph_pyqt6  # noqa: F401
from NodeGraphQt.qgraphics.node_base import NodeItem
from NodeGraphQt.constants import NodeEnum

from lmms.gui.qt import (
    QGraphicsItem,
    QGraphicsRectItem,
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QColor,
    QRectF,
    QPointF,
    QFont,
    Qt,
    QCursor,
)
from lmms.gui.branding import AutomationBranding


class NodeFloatingToolbarItem(QGraphicsItem):
    """
    Floating action toolbar rendered centered above the top edge of the node card:
    [▶ Test step] [⏻ Toggle active] [🗑 Delete] [✨ AI Assist] [⋯ More]
    """
    def __init__(self, parent_node_item: NodeItem):
        super().__init__(parent_node_item)
        self.node_item = parent_node_item
        self.setAcceptHoverEvents(True)
        self.setZValue(100.0)

        # 5 actions
        self.buttons = [
            {"id": "test", "label": "▶", "tooltip": "Test step"},
            {"id": "toggle", "label": "⏻", "tooltip": "Toggle active"},
            {"id": "delete", "label": "🗑", "tooltip": "Delete node"},
            {"id": "ai", "label": "✨", "tooltip": "AI Assist"},
            {"id": "more", "label": "⋯", "tooltip": "More options"},
        ]
        self.hovered_btn_idx = -1
        self.btn_w = 22.0
        self.btn_h = 22.0
        self.padding = 3.0
        self.total_w = len(self.buttons) * self.btn_w + (len(self.buttons) + 1) * self.padding
        self.total_h = self.btn_h + self.padding * 2

        self.update_position()
        self.hide()  # Hidden by default; visible on hover / selection

    def update_position(self):
        parent_rect = self.node_item.boundingRect()
        px = (parent_rect.width() - self.total_w) / 2.0
        py = -self.total_h - 4.0
        self.setPos(px, py)

    def boundingRect(self) -> QRectF:
        return QRectF(0.0, 0.0, self.total_w, self.total_h)

    def paint(self, painter: QPainter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Pill background
        pill_rect = self.boundingRect()
        path = QPainterPath()
        path.addRoundedRect(pill_rect, 7.0, 7.0)

        painter.fillPath(path, QBrush(QColor(24, 24, 28, 235)))
        painter.strokePath(path, QPen(QColor(56, 59, 74), 1.0))

        # Buttons
        font = QFont("Segoe UI", 9)
        painter.setFont(font)

        for i, btn in enumerate(self.buttons):
            bx = self.padding + i * (self.btn_w + self.padding)
            by = self.padding
            b_rect = QRectF(bx, by, self.btn_w, self.btn_h)

            if i == self.hovered_btn_idx:
                btn_path = QPainterPath()
                btn_path.addRoundedRect(b_rect, 4.0, 4.0)
                painter.fillPath(btn_path, QBrush(QColor(50, 52, 65)))

            # Button text color
            if btn["id"] == "ai":
                painter.setPen(QPen(QColor("#c084fc")))
            elif btn["id"] == "test":
                painter.setPen(QPen(QColor("#10b981")))
            elif btn["id"] == "delete" and i == self.hovered_btn_idx:
                painter.setPen(QPen(QColor("#ef4444")))
            else:
                painter.setPen(QPen(QColor("#d4d4d8")))

            painter.drawText(b_rect, int(Qt.AlignmentFlag.AlignCenter), btn["label"])

        painter.restore()

    def _get_button_at_pos(self, pos: QPointF) -> int:
        for i in range(len(self.buttons)):
            bx = self.padding + i * (self.btn_w + self.padding)
            by = self.padding
            if QRectF(bx, by, self.btn_w, self.btn_h).contains(pos):
                return i
        return -1

    def hoverMoveEvent(self, event):
        idx = self._get_button_at_pos(event.pos())
        if idx != self.hovered_btn_idx:
            self.hovered_btn_idx = idx
            self.update()
        event.accept()

    def hoverLeaveEvent(self, event):
        self.hovered_btn_idx = -1
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        idx = self._get_button_at_pos(event.pos())
        if idx >= 0:
            btn_id = self.buttons[idx]["id"]
            self._execute_action(btn_id)
            event.accept()
            return
        super().mousePressEvent(event)

    def _execute_action(self, action_id: str):
        node = getattr(self.node_item, "node", None)
        if not node:
            return

        if action_id == "delete":
            graph = node.graph
            if graph:
                graph.delete_node(node)
        elif action_id == "toggle":
            node.set_disabled(not node.disabled())
        elif action_id == "test":
            if hasattr(node, "test_step"):
                node.test_step()
            elif hasattr(self.node_item, "test_step"):
                self.node_item.test_step()
        elif action_id in ("ai", "more"):
            # Emit inspection / focus
            viewer = self.node_item.viewer()
            if viewer and hasattr(viewer, "node_double_clicked"):
                viewer.node_double_clicked.emit(self.node_item.id)


class N8nNodeItem(NodeItem):
    """
    n8n-style card graphics item.
    Renders rounded card geometry with category accent, warning badge, status glow ring,
    and attached floating toolbar.
    """
    def __init__(self, name="node", parent=None):
        super().__init__(name, parent)
        self.setAcceptHoverEvents(True)

        # Status tracking: 'idle' | 'running' | 'success' | 'error'
        self._status = "idle"
        self._pulse_step = 0.0
        self._hovered = False
        self._category = "action"
        self._subtitle = ""

        # Set default dimensions: generous n8n card size
        self._width = 190.0
        self._height = 72.0

        # Create attached floating toolbar
        self.toolbar = NodeFloatingToolbarItem(self)

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, val: str):
        self._status = val
        self.update()

    def test_step(self):
        """Runs single-step execution simulation with visual status progression."""
        self.status = "running"
        from PyQt6.QtCore import QTimer

        def _step_done():
            self.status = "success"
            QTimer.singleShot(2500, lambda: setattr(self, "status", "idle"))

        QTimer.singleShot(400, _step_done)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.toolbar.show()
        self.toolbar.update_position()
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        if not self.selected:
            self.toolbar.hide()
        self.update()
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if value:
                self.toolbar.show()
                self.toolbar.update_position()
            elif not self._hovered:
                self.toolbar.hide()
        return super().itemChange(change, value)

    def _paint_horizontal(self, painter: QPainter, option, widget):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        margin = 2.0
        card_rect = QRectF(margin, margin, self._width - margin * 2, self._height - margin * 2)
        radius = 12.0

        # 1. Status Ring / Outer Glow
        if self._status == "running":
            pulse_pen = QPen(QColor("#38bdf8"), 2.5)
            pulse_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pulse_pen)
            glow_path = QPainterPath()
            glow_path.addRoundedRect(card_rect.adjusted(-2, -2, 2, 2), radius + 2, radius + 2)
            painter.drawPath(glow_path)
        elif self._status == "success":
            painter.setPen(QPen(QColor("#10b981"), 2.0))
            glow_path = QPainterPath()
            glow_path.addRoundedRect(card_rect.adjusted(-1, -1, 1, 1), radius + 1, radius + 1)
            painter.drawPath(glow_path)
        elif self._status == "error":
            painter.setPen(QPen(QColor("#ef4444"), 2.0))
            glow_path = QPainterPath()
            glow_path.addRoundedRect(card_rect.adjusted(-1, -1, 1, 1), radius + 1, radius + 1)
            painter.drawPath(glow_path)

        # 2. Main Card Body
        card_path = QPainterPath()
        card_path.addRoundedRect(card_rect, radius, radius)

        # Background color
        bg_color = QColor("#282a36") if self.selected else QColor("#1e1f26")
        painter.fillPath(card_path, QBrush(bg_color))

        # Card Border
        if self.selected:
            border_pen = QPen(QColor("#8b5cf6"), 1.8)
        else:
            border_pen = QPen(QColor("#333645"), 1.0)
        painter.strokePath(card_path, border_pen)

        # 3. Category Accent Badge / Stripe on left
        node_obj = getattr(self, "node", None)
        cat = getattr(node_obj, "CATEGORY", self._category) if node_obj else self._category
        cat_color = QColor(AutomationBranding.get_category_color(cat))

        # Draw left icon background box
        icon_box = QRectF(card_rect.left() + 10, card_rect.top() + (card_rect.height() - 36) / 2, 36, 36)
        icon_path = QPainterPath()
        icon_path.addRoundedRect(icon_box, 8.0, 8.0)
        painter.fillPath(icon_path, QBrush(cat_color.darker(180)))
        painter.strokePath(icon_path, QPen(cat_color, 1.0))

        # Icon / Symbol inside box
        node_icon = getattr(node_obj, "NODE_ICON", "⚡") if node_obj else "⚡"
        painter.setPen(QPen(QColor("#ffffff")))
        painter.setFont(QFont("Segoe UI", 12))
        painter.drawText(icon_box, int(Qt.AlignmentFlag.AlignCenter), node_icon)

        # 4. Node Title Text
        text_x = icon_box.right() + 12
        text_w = card_rect.right() - text_x - 14
        title_rect = QRectF(text_x, card_rect.top() + 16, text_w, 20)

        painter.setPen(QPen(QColor("#f4f4f5")))
        title_font = QFont("Segoe UI", 11)
        title_font.setBold(True)
        painter.setFont(title_font)
        display_title = self.name or "Node"
        painter.drawText(title_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), display_title)

        # Subtitle or status
        sub_rect = QRectF(text_x, card_rect.top() + 36, text_w, 16)
        painter.setFont(QFont("Segoe UI", 9))
        if self._status != "idle":
            stat_color = QColor("#38bdf8") if self._status == "running" else (QColor("#10b981") if self._status == "success" else QColor("#ef4444"))
            painter.setPen(QPen(stat_color))
            painter.drawText(sub_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), self._status.upper())
        else:
            painter.setPen(QPen(QColor("#9ca3af")))
            sub_text = self._subtitle or cat.capitalize()
            painter.drawText(sub_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), sub_text)

        painter.restore()
