"""
message_list.py

Chat message list with:
- Content-driven sizing (no fixed heights)
- Small consistent vertical gap between turns
- Intelligent auto-scroll (follows bottom unless user has scrolled up)
- "↓ Jump to latest" sticky button when user has scrolled up
- Minimal empty state
"""
from typing import Dict, List

from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from lmms.gui.state.chat_message import ChatMessage
from lmms.gui.widgets.chat.message_widget import MessageWidget


class MessageListWidget(QScrollArea):
    link_clicked = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    retry_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #374151;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        # Container holding the actual messages
        self._container = QWidget()
        self._container.setObjectName("MessageList")
        self._container.setStyleSheet("background: transparent;")
        
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(16, 16, 16, 20) # Add side margins here so it doesn't touch window edges
        self._layout.setSpacing(0)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state goes in _layout
        self._empty = QLabel("Start a conversation")
        self._empty.setStyleSheet("color: #6b7280; font-size: 14px;")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._empty)
        self._layout.addStretch()

        self.setWidget(self._container)

        # State
        self._widgets: Dict[str, MessageWidget] = {}
        self._ordered_ids: List[str] = []
        self._user_scrolled_up = False

        # Auto-scroll wiring
        self.verticalScrollBar().actionTriggered.connect(self._on_scroll_action)
        self.verticalScrollBar().rangeChanged.connect(self._on_range_changed)

        # "Jump to latest" button (overlay)
        self._jump_btn = QPushButton("↓ Jump to latest", self)
        self._jump_btn.setStyleSheet("""
            QPushButton {
                background: #1f2937;
                color: #9ca3af;
                border: 1px solid #374151;
                border-radius: 12px;
                font-size: 11px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background: #374151;
                color: #e5e7eb;
            }
        """)
        self._jump_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._jump_btn.clicked.connect(self._scroll_to_bottom)
        self._jump_btn.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_jump_btn()

    def _reposition_jump_btn(self):
        w = self._jump_btn.sizeHint().width()
        h = self._jump_btn.sizeHint().height()
        x = (self.width() - w) // 2
        y = self.height() - h - 60
        self._jump_btn.setGeometry(x, y, w, h)

    # ── Auto-scroll ───────────────────────────────────────────────────────────
    def _on_scroll_action(self, action):
        bar = self.verticalScrollBar()
        at_bottom = bar.value() >= bar.maximum() - 20
        self._user_scrolled_up = not at_bottom
        self._jump_btn.setVisible(self._user_scrolled_up)

    def _on_range_changed(self, _min, _max):
        if not self._user_scrolled_up:
            self.verticalScrollBar().setValue(_max)

    def _scroll_to_bottom(self):
        self._user_scrolled_up = False
        self._jump_btn.hide()
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    # ── Public API ────────────────────────────────────────────────────────────
    def clear(self):
        """Remove all message widgets."""
        for wid in list(self._widgets.values()):
            self._layout.removeWidget(wid)
            wid.deleteLater()
        self._widgets.clear()
        self._ordered_ids.clear()
        self._user_scrolled_up = False
        self._jump_btn.hide()
        self._empty.show()

    def add_message(self, message: ChatMessage):
        if message.id in self._widgets:
            return

        if self._empty.isVisible():
            self._empty.hide()

        widget = MessageWidget(message)
        widget.link_clicked.connect(self.link_clicked.emit)
        widget.edit_requested.connect(self.edit_requested.emit)
        widget.delete_requested.connect(self.delete_requested.emit)
        widget.retry_requested.connect(self.retry_requested.emit)

        # Insert before the trailing stretch
        self._layout.insertWidget(self._layout.count() - 1, widget)
        self._widgets[message.id] = widget
        self._ordered_ids.append(message.id)

        # Nudge auto-scroll
        bar = self.verticalScrollBar()
        if bar.value() >= bar.maximum() - 40:
            self._user_scrolled_up = False

    def update_message(self, message: ChatMessage):
        if message.id in self._widgets:
            self._widgets[message.id].update_content()

    def remove_message(self, message_id: str):
        if message_id not in self._widgets:
            return
        widget = self._widgets.pop(message_id)
        self._layout.removeWidget(widget)
        widget.deleteLater()
        if message_id in self._ordered_ids:
            self._ordered_ids.remove(message_id)
        if not self._ordered_ids:
            self._empty.show()
