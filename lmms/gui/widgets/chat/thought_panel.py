"""
thought_panel.py

LM Studio-style collapsible thought process panel.

Behaviour:
  - Auto-expands when the model starts generating reasoning
  - Shows live elapsed time during generation: "Thinking… 3.2s"
  - Auto-collapses to "› Thought for 3.2s" when done
  - User can click toggle at any time to expand/collapse
  - NEVER shown unless real model reasoning content exists
  - Uses QToolButton (not HTML links) — no Chrome-opening bug
"""
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel,
    QSizePolicy, QFrame, QTextBrowser
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot


class ThoughtPanelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self._is_expanded = False
        self._is_generating = False
        self._start_time: float | None = None
        self._elapsed_s: float = 0.0

        # Ticks every 200ms to update "Thinking… Xs" label during generation
        self._tick = QTimer(self)
        self._tick.setInterval(200)
        self._tick.timeout.connect(self._update_header_text)

        self._build_ui()

    # ── Public properties / methods ───────────────────────────────────────────
    @property
    def is_expanded(self) -> bool:
        """Public accessor kept for test/external compatibility."""
        return self._is_expanded

    @property
    def content_label(self):
        """Public alias for the content container widget (test compatibility)."""
        return self._content_widget

    def toggle_expansion(self):
        """Toggle expanded / collapsed state."""
        self._toggle_btn.toggle()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 4)
        outer.setSpacing(0)

        self._box_frame = QFrame()
        self._box_frame.setStyleSheet("""
            QFrame {
                background-color: #212121;
                border: 1px solid #333333;
                border-radius: 8px;
            }
        """)
        box_layout = QVBoxLayout(self._box_frame)
        box_layout.setContentsMargins(12, 10, 12, 10)
        box_layout.setSpacing(8)

        # Header row: [arrow] [label]
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        self._toggle_btn = QToolButton()
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(False)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setArrowType(Qt.ArrowType.RightArrow)
        self._toggle_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                color: #6b7280;
                padding: 0;
            }
            QToolButton:hover { color: #9ca3af; }
        """)
        self._toggle_btn.setFixedSize(14, 14)
        self._toggle_btn.toggled.connect(self._on_toggle)

        self._header_label = QLabel("Thinking…")
        self._header_label.setStyleSheet(
            "font-size: 11px; color: #a1a1aa; padding: 0; border: none; background: transparent;"
        )
        self._header_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header_label.mousePressEvent = lambda _e: self._toggle_btn.toggle()

        header_row.addWidget(self._toggle_btn)
        header_row.addWidget(self._header_label)
        header_row.addStretch()
        box_layout.addLayout(header_row)

        # Content area
        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("border: none; background: transparent;")
        self._content_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        content_layout = QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(20, 4, 0, 0)
        content_layout.setSpacing(0)

        self._content_label = QTextBrowser()
        self._content_label.setOpenExternalLinks(False)
        self._content_label.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content_label.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self._content_label.setFrameShape(QFrame.Shape.NoFrame)
        self._content_label.setStyleSheet("""
            QTextBrowser {
                background: transparent;
                border: none;
                color: #d1d5db;
                font-size: 12px;
                line-height: 1.5;
                padding: 0;
                margin: 0;
            }
        """)
        self._content_label.document().documentLayout().documentSizeChanged.connect(
            self._reheight
        )
        content_layout.addWidget(self._content_label)

        self._content_widget.hide()
        box_layout.addWidget(self._content_widget)
        outer.addWidget(self._box_frame)

    def _reheight(self, size):
        h = int(size.height()) + 2
        self._content_label.setFixedHeight(max(h, 4))

    # ── Public API ────────────────────────────────────────────────────────────
    def set_content(self, text: str):
        """Set the reasoning text content."""
        self._content_label.setPlainText(text)

    def set_generating(self, generating: bool):
        """
        Call with True when reasoning is streaming.
        Call with False when the message is complete.
        """
        if generating and not self._is_generating:
            self._is_generating = True
            if self._start_time is None:
                self._start_time = time.monotonic()
            self._expand()
            self._tick.start()
        elif not generating and self._is_generating:
            self._is_generating = False
            self._tick.stop()
            if self._start_time is not None:
                self._elapsed_s = time.monotonic() - self._start_time
            self._collapse()
            self._update_header_text()

    # ── Internal ─────────────────────────────────────────────────────────────
    @pyqtSlot(bool)
    def _on_toggle(self, checked: bool):
        if checked:
            self._expand()
        else:
            self._collapse()

    def _expand(self):
        self._is_expanded = True
        self._toggle_btn.setChecked(True)
        self._toggle_btn.setArrowType(Qt.ArrowType.DownArrow)
        self._content_widget.show()

    def _collapse(self):
        self._is_expanded = False
        self._toggle_btn.setChecked(False)
        self._toggle_btn.setArrowType(Qt.ArrowType.RightArrow)
        self._content_widget.hide()

    @pyqtSlot()
    def _update_header_text(self):
        if self._is_generating and self._start_time is not None:
            elapsed = time.monotonic() - self._start_time
            self._header_label.setText(f"Thinking… {elapsed:.1f}s")
        elif self._elapsed_s > 0:
            self._header_label.setText(f"Thought for {self._elapsed_s:.1f}s")
        else:
            self._header_label.setText("Thought process")
