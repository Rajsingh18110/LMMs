"""
agent_activity_indicator.py

Persistent, animated Live Agent Activity Indicator for LMMs GUI.
Displays real-time agent execution state (thinking, browser navigation,
DOM inspection, clicking, typing, waiting for page, verification, success, failure, cancellation)
with a pulsing electric blue activity light and concise human-readable activity labels.
"""

from __future__ import annotations

import math
from typing import Optional
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPaintEvent


class _PulsingDot(QWidget):
    """
    Renders an animated glowing dot with smooth sinusoidal opacity/pulse modulation.
    Blue when active; green on success; red on error; gray when idle/cancelled.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self._color = QColor("#38bdf8")       # Electric sky blue
        self._glow_color = QColor("#0284c7")  # Deep blue glow
        self._is_animating = False
        self._phase = 0.0

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(40)      # ~25 fps
        self._anim_timer.timeout.connect(self._on_tick)

    def set_mode(self, mode: str):
        mode = mode.lower()
        if mode in ("active", "thinking", "navigating", "inspecting", "clicking", "typing", "waiting", "verifying", "executing"):
            self._color = QColor("#38bdf8")       # Blue
            self._glow_color = QColor("#0284c7")
            if not self._is_animating:
                self._is_animating = True
                self._anim_timer.start()
        elif mode == "success":
            self._is_animating = False
            self._anim_timer.stop()
            self._color = QColor("#22c55e")       # Emerald green
            self._glow_color = QColor("#16a34a")
            self._phase = 1.0
            self.update()
        elif mode == "error":
            self._is_animating = False
            self._anim_timer.stop()
            self._color = QColor("#ef4444")       # Ruby red
            self._glow_color = QColor("#dc2626")
            self._phase = 1.0
            self.update()
        else: # idle, cancelled
            self._is_animating = False
            self._anim_timer.stop()
            self._color = QColor("#64748b")       # Muted slate gray
            self._glow_color = QColor("#475569")
            self._phase = 0.0
            self.update()

    def _on_tick(self):
        self._phase = (self._phase + 0.12) % (2 * math.pi)
        self.update()

    def paintEvent(self, a0: Optional[QPaintEvent]):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() / 2.0
        center_y = self.height() / 2.0

        if self._is_animating:
            # Pulsing outer aura
            intensity = 0.4 + 0.6 * ((math.sin(self._phase) + 1.0) / 2.0)
            glow = QColor(self._glow_color)
            glow.setAlphaF(0.35 * intensity)
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            radius_outer = 4.0 + 2.0 * intensity
            painter.drawEllipse(int(center_x - radius_outer), int(center_y - radius_outer),
                               int(radius_outer * 2), int(radius_outer * 2))

            # Inner core
            core = QColor(self._color)
            core.setAlphaF(0.85 + 0.15 * intensity)
            painter.setBrush(QBrush(core))
            painter.drawEllipse(int(center_x - 3.5), int(center_y - 3.5), 7, 7)
        else:
            # Static dot
            painter.setBrush(QBrush(self._color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(center_x - 3.5), int(center_y - 3.5), 7, 7)


class AgentActivityIndicator(QFrame):
    """
    Compact, persistent agent activity badge.
    Displays an animated blue LED when agent is active with distinct states:
      - thinking
      - navigating (browser.open_url)
      - inspecting (DOM inspection)
      - clicking (DOM or pointer click)
      - typing / filling (form interaction)
      - waiting (network / page load)
      - verifying (state verification)
      - success (completed)
      - error (failed)
      - cancelled (stopped by user)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("AgentActivityIndicator")
        self._current_state = "idle"
        self._current_label = "Ready"

        self.setStyleSheet("""
            QFrame#AgentActivityIndicator {
                background: #111827;
                border: 1px solid #1f2937;
                border-radius: 12px;
                padding: 1px 8px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 8, 2)
        layout.setSpacing(6)

        self.dot = _PulsingDot(self)
        self.label = QLabel("Ready")
        self.label.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 11px;
                font-weight: 500;
                background: transparent;
                border: none;
            }
        """)

        layout.addWidget(self.dot)
        layout.addWidget(self.label)

        self.reset()

    # ─────────────────────────────────────────────────────────────────────────
    # State Setters
    # ─────────────────────────────────────────────────────────────────────────
    def set_state(self, state: str, label: str = ""):
        self._current_state = state.lower()
        clean_label = label.strip()

        default_labels = {
            "idle": "Ready",
            "thinking": "Thinking...",
            "navigating": "Navigating to page...",
            "inspecting": "Inspecting page DOM...",
            "clicking": "Clicking element...",
            "typing": "Typing text...",
            "filling": "Filling form...",
            "waiting": "Waiting for navigation...",
            "verifying": "Verifying result...",
            "file_op": "Accessing workspace files...",
            "success": "Task completed",
            "error": "Operation failed",
            "cancelled": "Cancelled"
        }

        self._current_label = clean_label or default_labels.get(self._current_state, self._current_state.capitalize())
        self.label.setText(self._current_label)

        # Update text styling according to state
        if self._current_state in ("thinking", "navigating", "inspecting", "clicking", "typing", "filling", "waiting", "verifying", "file_op"):
            self.dot.set_mode(self._current_state)
            self.label.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 600; background: transparent; border: none;")
            self.setStyleSheet("""
                QFrame#AgentActivityIndicator {
                    background: #0b192c;
                    border: 1px solid #1e3a5f;
                    border-radius: 12px;
                    padding: 1px 8px;
                }
            """)
        elif self._current_state == "success":
            self.dot.set_mode("success")
            self.label.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: 500; background: transparent; border: none;")
            self.setStyleSheet("""
                QFrame#AgentActivityIndicator {
                    background: #052e16;
                    border: 1px solid #14532d;
                    border-radius: 12px;
                    padding: 1px 8px;
                }
            """)
        elif self._current_state == "error":
            self.dot.set_mode("error")
            self.label.setStyleSheet("color: #f87171; font-size: 11px; font-weight: 500; background: transparent; border: none;")
            self.setStyleSheet("""
                QFrame#AgentActivityIndicator {
                    background: #450a0a;
                    border: 1px solid #7f1d1d;
                    border-radius: 12px;
                    padding: 1px 8px;
                }
            """)
        else: # idle or cancelled
            self.dot.set_mode("idle")
            self.label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 500; background: transparent; border: none;")
            self.setStyleSheet("""
                QFrame#AgentActivityIndicator {
                    background: #111827;
                    border: 1px solid #1f2937;
                    border-radius: 12px;
                    padding: 1px 8px;
                }
            """)

    def set_thinking(self, details: str = ""):
        self.set_state("thinking", f"Thinking... {details}".strip())

    def set_navigating(self, url: str = ""):
        url_display = url.split("?")[0] if url else "page"
        if len(url_display) > 35:
            url_display = url_display[:32] + "..."
        self.set_state("navigating", f"Navigating to {url_display}")

    def set_inspecting(self, details: str = ""):
        self.set_state("inspecting", f"Inspecting page {details}".strip())

    def set_clicking(self, target: str = ""):
        target_display = target[:25] + "..." if len(target) > 25 else target
        self.set_state("clicking", f"Clicking {target_display}" if target_display else "Clicking element...")

    def set_typing(self, details: str = ""):
        self.set_state("typing", f"Filling form / typing {details}".strip())

    def set_verifying(self, details: str = ""):
        self.set_state("verifying", f"Verifying result {details}".strip())

    def set_success(self, message: str = "Task completed"):
        self.set_state("success", message)

    def set_error(self, message: str = "Operation failed"):
        self.set_state("error", message)

    def set_cancelled(self, message: str = "Cancelled"):
        self.set_state("cancelled", message)

    def reset(self):
        self.set_state("idle", "Ready")

    def get_state(self) -> str:
        return self._current_state

    def get_label(self) -> str:
        return self._current_label
