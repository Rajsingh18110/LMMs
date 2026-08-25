"""
message_widget.py

Professional chat message rendering for LMMs.
Design target: LM Studio + Cursor visual quality.

Key design decisions:
- User messages: RIGHT-aligned, NO "You" label, bare text on dark background
- Assistant messages: LEFT-aligned, compact model name as dim header
- No heavy borders, no cartoon UI, no fixed heights
- Hover reveals action buttons — not always visible
- Thought panel: only shown when real model reasoning exists
"""
import re
import markdown
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextBrowser, QSizePolicy, QPushButton,
    QApplication, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize

from lmms.gui.state.chat_message import ChatMessage
from lmms.gui.widgets.chat.thought_panel import ThoughtPanelWidget
from lmms.gui.widgets.chat.code_block import CodeBlockWidget


# ─────────────────────────────────────────────────────────────────────────────
# ChatTextBrowser — auto-sizes to its document height, no scrollbar
# ─────────────────────────────────────────────────────────────────────────────
class ChatTextBrowser(QTextBrowser):
    """A read-only text browser that sizes itself to its content."""

    def __init__(self, is_user: bool = False, parent=None):
        super().__init__(parent)
        self._is_user = is_user
        self.setOpenExternalLinks(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumWidth(96 if is_user else 220)
        self.document().setDocumentMargin(0)
        self.setContentsMargins(0, 0, 0, 0)
        self.setFrameShape(QFrame.Shape.NoFrame)

        if is_user:
            fg = "#e5e7eb"
            bg = "background: #343434; border-radius: 18px; padding: 11px 15px; margin: 0;"
            border = "border: 1px solid #404040;"
        else:
            fg = "#d1d5db"
            bg = "background: transparent; border-radius: 0; padding: 0; margin: 0;"
            border = "border: none;"

        self.setStyleSheet(f"""
            QTextBrowser {{
                {bg}
                {border}
                color: {fg};
                font-size: 14px;
                line-height: 1.6;
                selection-background-color: #264f78;
            }}
        """)
        # Force HTML elements to inherit the text color
        self.document().setDefaultStyleSheet(f"""
            body {{
                color: {fg};
                margin: 0;
                font-size: 14px;
            }}
            p {{
                color: {fg};
                margin: 0 0 8px 0;
            }}
            strong {{
                color: #f3f4f6;
                font-weight: 600;
            }}
            ul, ol {{
                margin-top: 4px;
                margin-bottom: 8px;
                padding-left: 18px;
            }}
            li {{
                margin-bottom: 4px;
            }}
            table {{
                border-collapse: collapse;
                margin-top: 8px;
                margin-bottom: 8px;
            }}
            th {{
                color: #f3f4f6;
                font-weight: 600;
                background-color: #202020;
            }}
            th, td {{
                border: 1px solid #303030;
                padding: 5px 7px;
                vertical-align: top;
            }}
            code {{
                color: #e5e7eb;
                background-color: #111827;
            }}
        """)
        
        self.document().documentLayout().documentSizeChanged.connect(self._reheight)

    def _reheight(self, size):
        h = int(size.height())
        h += 24 # 12px top/bottom padding for both user and assistant bubbles
        self.setFixedHeight(max(h, 24))

    def sizeHint(self):
        h = int(self.document().size().height())
        h += 24
        return QSize(super().sizeHint().width(), max(h, 24))


# ─────────────────────────────────────────────────────────────────────────────
# HoverActionBar — appears on mouse-enter, hides on mouse-leave
# ─────────────────────────────────────────────────────────────────────────────
class _ActionBtn(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #6e7681;
                font-size: 11px;
                padding: 1px 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                color: #c9d1d9;
                background: #1f2937;
            }
        """)
        self.setFixedHeight(18)


# ─────────────────────────────────────────────────────────────────────────────
# Token stats bar — small single-line dim label under assistant response
# ─────────────────────────────────────────────────────────────────────────────
class TokenStatsBar(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "font-size: 10px; color: #4b5563; padding: 0; margin: 0;"
        )
        self.hide()

    def set_metrics(self, metrics: dict):
        parts = []
        if "tokens_per_sec" in metrics:
            parts.append(f"{metrics['tokens_per_sec']:.2f} tok/s")
        if "total_tokens" in metrics:
            parts.append(f"{metrics['total_tokens']} tokens")
        if "elapsed_s" in metrics:
            parts.append(f"{metrics['elapsed_s']:.2f}s")
        stop = metrics.get("stop_reason", "")
        if stop:
            parts.append(stop)
        if parts:
            self.setText("  ·  ".join(parts))
            self.show()


# ─────────────────────────────────────────────────────────────────────────────
# MessageWidget — one conversation turn
# ─────────────────────────────────────────────────────────────────────────────
class MessageWidget(QWidget):
    link_clicked = pyqtSignal(str)
    edit_requested = pyqtSignal(str)     # message.id
    delete_requested = pyqtSignal(str)   # message.id
    retry_requested = pyqtSignal(str)    # message.id

    def __init__(self, message: ChatMessage, parent=None):
        super().__init__(parent)
        self.message = message
        self._is_user = message.role == "user"
        self._rendered_content = ""
        self._copy_btn = None
        self._copy_timer = QTimer(self)
        self._copy_timer.setSingleShot(True)
        self._copy_timer.timeout.connect(self._reset_copy)
        self._action_bar = None    # populated in _build_ui
        self._stats_bar = None
        self.thought_panel = None
        self.status_label = None

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self._build_ui()
        self.update_content()

    # ─────────────────────────────────────────────────────────────────────────
    # Layout construction
    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Outer: horizontal row for left/right alignment
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 10, 0, 10)
        outer.setSpacing(0)

        # Inner content column
        self._content_col = QWidget()
        self._content_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        col_layout = QVBoxLayout(self._content_col)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.setSpacing(3)

        # ── Header (assistant only — model name) ──────────────────────────
        if not self._is_user and self.message.role == "assistant":
            raw = getattr(self.message, "model_name", "") or ""
            display = raw.replace(".gguf", "").replace(".bin", "").strip() or "LMMs Engine"
            hdr = QLabel(display)
            hdr.setStyleSheet(
                "font-size: 11px; font-weight: 600; color: #7b8494; padding: 0 0 2px 2px; margin: 0;"
            )
            hdr.setToolTip(raw)
            col_layout.addWidget(hdr)

        # ── Thought panel (assistant only, hidden until populated) ─────────
        if not self._is_user:
            self.thought_panel = ThoughtPanelWidget()
            col_layout.addWidget(self.thought_panel)
            self.thought_panel.hide()

        # ── Content parts (text + code blocks) ────────────────────────────
        self._parts_layout = QVBoxLayout()
        self._parts_layout.setContentsMargins(0, 0, 0, 0)
        self._parts_layout.setSpacing(4)
        col_layout.addLayout(self._parts_layout)

        # ── Status label (Generating… / Failed / Stopped) ─────────────────
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            "font-size: 11px; color: #8b949e; background: #111827; "
            "border: 1px solid #1f2937; border-radius: 8px; "
            "padding: 3px 8px; margin: 2px 0 0 2px;"
        )
        self.status_label.hide()
        col_layout.addWidget(self.status_label)

        # ── Token stats (assistant, shown after done) ──────────────────────
        if not self._is_user:
            self._stats_bar = TokenStatsBar()
            col_layout.addWidget(self._stats_bar)

        # ── Action bar (appears on hover) ─────────────────────────────────
        self._action_bar = self._make_action_bar()
        self._action_bar.hide()
        col_layout.addWidget(self._action_bar)

        # ── Place content column in outer layout ───────────────────────────
        if self._is_user:
            outer.addStretch(1)
            outer.addWidget(self._content_col)
        else:
            outer.addWidget(self._content_col, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        if w > 0:
            # User messages stay compact; assistant messages get more room for tables/lists.
            ratio = 0.74 if self._is_user else 0.96
            self._content_col.setMaximumWidth(int(w * ratio))
            if not self._is_user:
                self._content_col.setMinimumWidth(int(w * ratio))

    # ─────────────────────────────────────────────────────────────────────────
    # Action bar factory
    # ─────────────────────────────────────────────────────────────────────────
    def _make_action_bar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        if self._is_user:
            layout.addStretch()
            edit = _ActionBtn("Edit")
            edit.clicked.connect(lambda: self.edit_requested.emit(self.message.id))
            delete = _ActionBtn("Delete")
            delete.clicked.connect(self._confirm_delete)
            layout.addWidget(edit)
            layout.addWidget(delete)
        else:
            self._copy_btn = _ActionBtn("Copy")
            self._copy_btn.clicked.connect(self._copy_content)
            retry = _ActionBtn("Retry")
            retry.clicked.connect(lambda: self.retry_requested.emit(self.message.id))
            layout.addWidget(self._copy_btn)
            layout.addWidget(retry)
            layout.addStretch()

        return bar

    # ─────────────────────────────────────────────────────────────────────────
    # Hover: show / hide action bar
    # ─────────────────────────────────────────────────────────────────────────
    def enterEvent(self, event):
        super().enterEvent(event)
        if self._action_bar:
            self._action_bar.show()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if self._action_bar:
            self._action_bar.hide()

    # ─────────────────────────────────────────────────────────────────────────
    # Content update — called on every chunk flush
    # ─────────────────────────────────────────────────────────────────────────
    def update_content(self):
        msg = self.message
        content = msg.content or ""
        thought = msg.thought or ""
        has_content = bool(content.strip())
        has_thought = bool(thought.strip())

        # ── Thought panel ──────────────────────────────────────────────────
        if self.thought_panel is not None:
            if has_thought:
                self.thought_panel.show()
                self.thought_panel.set_content(thought)
                self.thought_panel.set_generating(msg.status == "generating")
            else:
                # Hide if still empty (may appear later as streaming progresses)
                if msg.status != "generating":
                    self.thought_panel.hide()

        # ── Status ────────────────────────────────────────────────────────
        if self.status_label is not None:
            status = msg.status
            if status == "generating" and not has_content and not has_thought:
                self.status_label.setText("Thinking...")
                self.status_label.setStyleSheet(
                    "font-size: 11px; color: #8b949e; background: #111827; "
                    "border: 1px solid #1f2937; border-radius: 8px; "
                    "padding: 3px 8px; margin: 2px 0 0 2px;"
                )
                self.status_label.show()
            elif status == "error":
                self.status_label.setText("Failed")
                self.status_label.setStyleSheet(
                    "font-size: 11px; color: #f87171; background: #241518; "
                    "border: 1px solid #4b1f28; border-radius: 8px; "
                    "padding: 3px 8px; margin: 2px 0 0 2px;"
                )
                self.status_label.show()
            elif status == "cancelled":
                self.status_label.setText("Stopped")
                self.status_label.setStyleSheet(
                    "font-size: 11px; color: #9ca3af; background: #171717; "
                    "border: 1px solid #2a2a2a; border-radius: 8px; "
                    "padding: 3px 8px; margin: 2px 0 0 2px;"
                )
                self.status_label.show()
            else:
                self.status_label.hide()

        # ── Token stats (after done) ───────────────────────────────────────
        if self._stats_bar is not None and msg.status == "done" and msg.metrics:
            self._stats_bar.set_metrics(msg.metrics)

        # ── Text content (skip if unchanged) ──────────────────────────────
        if content == self._rendered_content:
            return
        self._rendered_content = content

        # Clear previous parts
        while self._parts_layout.count():
            item = self._parts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not content:
            return

        # Split on fenced code blocks
        parts = re.split(r'(```[a-zA-Z0-9_.\-]*\n.*?```)', content, flags=re.DOTALL)
        for part in parts:
            if not part.strip():
                continue
            if part.startswith("```"):
                hdr, _, rest = part.partition("\n")
                lang = hdr[3:].strip()
                body = rest[:-3] if rest.endswith("```") else rest
                code_w = CodeBlockWidget(code=body.strip(), language=lang)
                self._parts_layout.addWidget(code_w)
            else:
                html = markdown.markdown(part, extensions=["tables", "fenced_code"])
                tb = ChatTextBrowser(is_user=self._is_user)
                tb.anchorClicked.connect(lambda url: self.link_clicked.emit(url.toString()))
                tb.setHtml(html)
                self._parts_layout.addWidget(tb)

    # ─────────────────────────────────────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────────────────────────────────────
    def _copy_content(self):
        text = self.message.content or ""
        thought = self.message.thought or ""
        if thought.strip():
            text = f"{text}\n\n[Thought]\n{thought}".strip()
        QApplication.clipboard().setText(text)
        if self._copy_btn:
            self._copy_btn.setText("Copied!")
            self._copy_timer.start(1500)

    def _reset_copy(self):
        if self._copy_btn:
            self._copy_btn.setText("Copy")

    def _confirm_delete(self):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete message")
        dlg.setText("Delete this message and its response?")
        ok_btn = dlg.addButton("Delete", QMessageBox.ButtonRole.DestructiveRole)
        dlg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        dlg.exec()
        if dlg.clickedButton() is ok_btn:
            self.delete_requested.emit(self.message.id)
