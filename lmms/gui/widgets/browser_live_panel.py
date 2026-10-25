"""
browser_live_panel.py

Integrated Live Browser Automation Panel for LMMs GUI.
Displays synchronized viewport snapshots from the active Playwright browser session,
a dynamic blue activity glow effect around the viewport during agent execution,
a real-time status overlay pill reflecting authentic browser events, and session controls.
"""

from __future__ import annotations

import os
import math
import time
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QFont


class _GlowingViewport(QFrame):
    """
    Viewport container with an animated soft light-blue glow border during agent activity,
    switching to emerald on verification, amber on wait, and neutral when idle.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._state = "idle"
        self._glow_phase = 0.0
        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(40)  # 25 fps smooth breathing
        self._glow_timer.timeout.connect(self._on_glow_tick)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(240)

    def set_state(self, state: str):
        self._state = state.lower()
        if self._state in ("thinking", "active", "navigating", "inspecting", "clicking", "typing", "filling"):
            if not self._glow_timer.isActive():
                self._glow_timer.start()
        else:
            self._glow_timer.stop()
            self._glow_phase = 0.0
        self.update()

    def _on_glow_tick(self):
        self._glow_phase = (self._glow_phase + 0.1) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        rect_f = self.rect().adjusted(1, 1, -1, -1)

        if self._state in ("thinking", "active", "navigating", "inspecting", "clicking", "typing", "filling"):
            # Active light-blue glowing border with subtle sinusoidal breathing
            intensity = 0.5 + 0.5 * ((math.sin(self._glow_phase) + 1.0) / 2.0)
            glow_color = QColor("#38bdf8")
            glow_color.setAlphaF(0.4 + 0.5 * intensity)
            pen = QPen(glow_color, 2.0)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect_f, 6.0, 6.0)

            # Outer subtle aura
            aura_color = QColor("#0284c7")
            aura_color.setAlphaF(0.15 * intensity)
            painter.setPen(QPen(aura_color, 4.0))
            painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 6.0, 6.0)

        elif self._state in ("verified", "success"):
            # Emerald green border on verified success
            pen = QPen(QColor("#10b981"), 2.0)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect_f, 6.0, 6.0)

        elif self._state == "waiting":
            # Amber border on waiting for navigation/observation
            pen = QPen(QColor("#f59e0b"), 2.0)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect_f, 6.0, 6.0)

        elif self._state == "error":
            # Crimson red border on error
            pen = QPen(QColor("#ef4444"), 2.0)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect_f, 6.0, 6.0)

        else:
            # Neutral dark border when idle or cancelled
            pen = QPen(QColor("#27272a"), 1.0)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect_f, 6.0, 6.0)


class AgentBrowserLivePanel(QFrame):
    """
    Integrated Browser Automation Panel embedded inside LMMs ChatPage.
    Provides a synchronized Playwright browser preview with a light-blue glowing activity effect,
    a floating status overlay pill, and controls to inspect or open in a visible browser.
    """

    close_requested = pyqtSignal()
    open_visible_browser_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("AgentBrowserLivePanel")
        self._current_url = ""
        self._current_title = ""
        self._current_screenshot_path = ""
        self._current_state = "idle"
        self._current_status_label = "Ready"

        self.setStyleSheet("""
            QFrame#AgentBrowserLivePanel {
                background-color: #0d1117;
                border-left: 1px solid #30363d;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ── Header Bar ────────────────────────────────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        title_icon = QLabel("🌐")
        title_icon.setStyleSheet("font-size: 13px; background: transparent;")

        title_lbl = QLabel("Agent Browser")
        title_lbl.setStyleSheet("color: #f0f6fc; font-size: 12px; font-weight: 600; background: transparent;")

        self.badge = QLabel("Synchronized Preview")
        self.badge.setStyleSheet("""
            background: #1e3a5f;
            color: #38bdf8;
            font-size: 9px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid #0284c7;
        """)

        self.btn_close = QPushButton("✕")
        self.btn_close.setToolTip("Hide Browser Panel")
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: #8b949e; font-size: 11px; }
            QPushButton:hover { background: #21262d; color: #f0f6fc; border-radius: 3px; }
        """)
        self.btn_close.clicked.connect(self.close_requested.emit)

        header_layout.addWidget(title_icon)
        header_layout.addWidget(title_lbl)
        header_layout.addWidget(self.badge)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_close)
        layout.addLayout(header_layout)

        # ── URL bar & Session Controls ────────────────────────────────────────
        url_container = QFrame()
        url_container.setStyleSheet("background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 2px 6px;")
        url_box = QHBoxLayout(url_container)
        url_box.setContentsMargins(4, 2, 4, 2)
        url_box.setSpacing(6)

        url_icon = QLabel("🔗")
        url_icon.setStyleSheet("font-size: 11px; background: transparent;")
        url_box.addWidget(url_icon)

        self.url_label = QLabel("No active browser session")
        self.url_label.setStyleSheet("color: #8b949e; font-family: monospace; font-size: 11px; background: transparent; border: none;")
        self.url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        url_box.addWidget(self.url_label, 1)

        self.btn_refresh = QPushButton("⟳")
        self.btn_refresh.setToolTip("Refresh Snapshot")
        self.btn_refresh.setFixedSize(22, 22)
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
            QPushButton { background: #21262d; color: #c9d1d9; border-radius: 4px; border: 1px solid #30363d; font-size: 12px; }
            QPushButton:hover { background: #30363d; color: #ffffff; }
        """)
        self.btn_refresh.clicked.connect(self.refresh_snapshot)
        url_box.addWidget(self.btn_refresh)

        self.btn_launch_visible = QPushButton("Open in Visible Window ↗")
        self.btn_launch_visible.setToolTip("Open this test session in a visible Playwright browser window")
        self.btn_launch_visible.setFixedHeight(22)
        self.btn_launch_visible.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_launch_visible.setStyleSheet("""
            QPushButton { background: #1e3a5f; color: #38bdf8; border-radius: 4px; border: 1px solid #0284c7; font-size: 10px; padding: 2px 8px; font-weight: 500; }
            QPushButton:hover { background: #0369a1; color: #ffffff; }
        """)
        self.btn_launch_visible.clicked.connect(self._on_open_visible_clicked)
        url_box.addWidget(self.btn_launch_visible)

        layout.addWidget(url_container)

        # ── Session Management Toolbar ────────────────────────────────────────
        session_toolbar = QFrame()
        session_toolbar.setStyleSheet("background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 2px 6px;")
        session_box = QHBoxLayout(session_toolbar)
        session_box.setContentsMargins(4, 2, 4, 2)
        session_box.setSpacing(6)

        self.session_mode_badge = QLabel("○ Isolated Profile")
        self.session_mode_badge.setStyleSheet("""
            background: #21262d;
            color: #8b949e;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid #30363d;
        """)
        session_box.addWidget(self.session_mode_badge)

        session_box.addStretch()

        self.btn_use_existing = QPushButton("Use Existing Browser Session")
        self.btn_use_existing.setToolTip("Attach to desktop Chrome session via Chrome DevTools Protocol (CDP port 9222)")
        self.btn_use_existing.setFixedHeight(22)
        self.btn_use_existing.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_use_existing.setStyleSheet("""
            QPushButton { background: #1e3a5f; color: #38bdf8; border-radius: 4px; border: 1px solid #0284c7; font-size: 10px; padding: 2px 8px; font-weight: 500; }
            QPushButton:hover { background: #0369a1; color: #ffffff; }
        """)
        self.btn_use_existing.clicked.connect(self._on_use_existing_session_clicked)
        session_box.addWidget(self.btn_use_existing)

        self.btn_open_persistent = QPushButton("Open Persistent Agent Browser")
        self.btn_open_persistent.setToolTip("Launch LMMs's persistent visible browser. Retains your authenticated session across tasks.")
        self.btn_open_persistent.setFixedHeight(22)
        self.btn_open_persistent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_persistent.setStyleSheet("""
            QPushButton { background: #064e3b; color: #34d399; border-radius: 4px; border: 1px solid #059669; font-size: 10px; padding: 2px 8px; font-weight: 500; }
            QPushButton:hover { background: #047857; color: #ffffff; }
        """)
        self.btn_open_persistent.clicked.connect(self._on_open_persistent_clicked)
        session_box.addWidget(self.btn_open_persistent)

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setToolTip("Disconnect browser session while preserving profile and cookies")
        self.btn_disconnect.setFixedHeight(22)
        self.btn_disconnect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_disconnect.setStyleSheet("""
            QPushButton { background: #21262d; color: #8b949e; border-radius: 4px; border: 1px solid #30363d; font-size: 10px; padding: 2px 6px; }
            QPushButton:hover { background: #30363d; color: #f0f6fc; }
        """)
        self.btn_disconnect.clicked.connect(self._on_disconnect_clicked)
        session_box.addWidget(self.btn_disconnect)

        layout.addWidget(session_toolbar)

        # ── Viewport Container with Soft Blue Glow & Status Pill ──────────────
        self.viewport_container = _GlowingViewport(self)
        viewport_layout = QVBoxLayout(self.viewport_container)
        viewport_layout.setContentsMargins(6, 6, 6, 6)
        viewport_layout.setSpacing(0)

        # Status Overlay Pill (Floating treatment over viewport)
        status_pill_container = QHBoxLayout()
        status_pill_container.setContentsMargins(8, 6, 8, 0)
        self.status_pill = QFrame()
        self.status_pill.setStyleSheet("""
            QFrame {
                background: rgba(13, 17, 23, 0.90);
                border: 1px solid #30363d;
                border-radius: 12px;
                padding: 2px 10px;
            }
        """)
        pill_layout = QHBoxLayout(self.status_pill)
        pill_layout.setContentsMargins(6, 2, 8, 2)
        pill_layout.setSpacing(6)

        self.pill_dot = QLabel("●")
        self.pill_dot.setStyleSheet("color: #64748b; font-size: 10px; background: transparent;")
        self.pill_label = QLabel("Agent idle")
        self.pill_label.setStyleSheet("color: #8b949e; font-size: 10px; font-weight: 600; background: transparent;")

        pill_layout.addWidget(self.pill_dot)
        pill_layout.addWidget(self.pill_label)

        status_pill_container.addWidget(self.status_pill)
        status_pill_container.addStretch()
        viewport_layout.addLayout(status_pill_container)

        # Main Browser Snapshot Viewer
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background: #090d13; color: #8b949e; font-size: 11px; border-radius: 4px;")
        self.image_label.setText("No page loaded yet.\nWhen the agent performs browser actions, live snapshots appear here.")
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        viewport_layout.addWidget(self.image_label, stretch=1)

        layout.addWidget(self.viewport_container, stretch=1)

        # ── Bottom Verified Action Banner ─────────────────────────────────────
        self.action_banner = QFrame()
        self.action_banner.setStyleSheet("background: #161b22; border: 1px solid #30363d; border-radius: 5px; padding: 3px 8px;")
        banner_layout = QHBoxLayout(self.action_banner)
        banner_layout.setContentsMargins(6, 3, 6, 3)
        banner_layout.setSpacing(6)

        action_icon = QLabel("⚡")
        action_icon.setStyleSheet("font-size: 11px; background: transparent;")
        banner_layout.addWidget(action_icon)

        self.action_label = QLabel("Waiting for agent activity...")
        self.action_label.setStyleSheet("color: #8b949e; font-size: 10px; font-family: monospace; background: transparent;")
        banner_layout.addWidget(self.action_label, 1)

        layout.addWidget(self.action_banner)

    # ─────────────────────────────────────────────────────────────────────────
    # Public API & State Management
    # ─────────────────────────────────────────────────────────────────────────
    def set_status_overlay(self, state: str, label: str = ""):
        """Update viewport glow and status pill to reflect authentic agent execution state."""
        self._current_state = state.lower()
        clean_label = label.strip()

        default_labels = {
            "idle": "Agent idle",
            "thinking": "Agent running",
            "navigating": "Navigating to page...",
            "inspecting": "Inspecting DOM...",
            "clicking": "Clicking element...",
            "typing": "Entering credentials...",
            "filling": "Submitting login form...",
            "waiting": "Waiting for navigation...",
            "verifying": "Verifying authenticated session...",
            "verified": "Action verified",
            "success": "Task completed",
            "error": "Action failed",
            "cancelled": "Task cancelled"
        }

        self._current_status_label = clean_label or default_labels.get(self._current_state, "Agent running")
        self.pill_label.setText(self._current_status_label)
        self.viewport_container.set_state(self._current_state)

        # Update pill styling according to state
        if self._current_state in ("thinking", "active", "navigating", "inspecting", "clicking", "typing", "filling"):
            self.pill_dot.setStyleSheet("color: #38bdf8; font-size: 10px; background: transparent;")
            self.pill_label.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 600; background: transparent;")
            self.status_pill.setStyleSheet("""
                QFrame {
                    background: rgba(14, 30, 50, 0.95);
                    border: 1px solid #0284c7;
                    border-radius: 12px;
                    padding: 2px 10px;
                }
            """)
        elif self._current_state in ("verified", "success"):
            self.pill_dot.setStyleSheet("color: #10b981; font-size: 10px; background: transparent;")
            self.pill_label.setStyleSheet("color: #10b981; font-size: 10px; font-weight: 600; background: transparent;")
            self.status_pill.setStyleSheet("""
                QFrame {
                    background: rgba(6, 40, 25, 0.95);
                    border: 1px solid #059669;
                    border-radius: 12px;
                    padding: 2px 10px;
                }
            """)
        elif self._current_state == "error":
            self.pill_dot.setStyleSheet("color: #ef4444; font-size: 10px; background: transparent;")
            self.pill_label.setStyleSheet("color: #ef4444; font-size: 10px; font-weight: 600; background: transparent;")
            self.status_pill.setStyleSheet("""
                QFrame {
                    background: rgba(50, 15, 15, 0.95);
                    border: 1px solid #dc2626;
                    border-radius: 12px;
                    padding: 2px 10px;
                }
            """)
        else: # idle or cancelled
            self.pill_dot.setStyleSheet("color: #64748b; font-size: 10px; background: transparent;")
            self.pill_label.setStyleSheet("color: #8b949e; font-size: 10px; font-weight: 600; background: transparent;")
            self.status_pill.setStyleSheet("""
                QFrame {
                    background: rgba(13, 17, 23, 0.90);
                    border: 1px solid #30363d;
                    border-radius: 12px;
                    padding: 2px 10px;
                }
            """)

    @pyqtSlot(str, str, str, str)
    def update_frame(self, url: str, title: str, screenshot_path: str, action: str = ""):
        """Update live preview with newly captured screenshot and log observable action."""
        self._current_url = url
        self._current_title = title
        self._current_screenshot_path = screenshot_path

        display_url = url if url else "about:blank"
        if title:
            display_url = f"{title} — {display_url}"
        self.url_label.setText(display_url[:65] + ("..." if len(display_url) > 65 else ""))
        self.url_label.setToolTip(f"{title}\n{url}")

        if screenshot_path and os.path.exists(screenshot_path):
            pixmap = QPixmap(screenshot_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(scaled)

        if action:
            self.add_timeline_event(action)

    def add_timeline_event(self, text: str):
        """Display the most recent observable browser action in the bottom action banner."""
        ts = time.strftime("%H:%M:%S")
        clean_text = text.strip()
        self.action_label.setText(f"[{ts}] {clean_text}")

        # Derive overlay state automatically if suitable
        if "NAVIGATE" in clean_text or "open_url" in clean_text:
            self.set_status_overlay("navigating", "Waiting for navigation...")
        elif "INSPECT" in clean_text:
            self.set_status_overlay("inspecting", "Inspecting DOM...")
        elif "CLICK" in clean_text:
            self.set_status_overlay("clicking", f"Clicking element...")
        elif "FORM" in clean_text or "FILL" in clean_text:
            self.set_status_overlay("typing", "Entering credentials...")
        elif "VERIFIED" in clean_text:
            self.set_status_overlay("verified", "Action verified")
        elif "FAILED" in clean_text or "error" in clean_text.lower():
            self.set_status_overlay("error", "Action failed")

    @pyqtSlot()
    def refresh_snapshot(self):
        """Request a fresh snapshot from the active BrowserTool instance."""
        try:
            from lmms.backend.tools.browser import get_browser_tool
            bt = get_browser_tool()
            path = bt._capture_preview_snapshot(action="Manual Refresh")
            if path and bt.page:
                self.update_frame(bt.page.url, bt.page.title(), path, "Refreshed live frame")
                self.set_status_overlay("verified", "Frame refreshed")
        except Exception as e:
            self.add_timeline_event(f"Refresh failed: {e}")

    def _on_open_visible_clicked(self):
        """Launch the current session in a visible browser window."""
        try:
            from lmms.backend.tools.browser import get_browser_tool
            bt = get_browser_tool()
            target_url = self._current_url or (bt.page.url if bt.page else "about:blank")
            bt.open_persistent_browser(url=target_url, headless=False)
            self.set_session_mode("persistent_profile")
            self.add_timeline_event(f"Opened visible browser at {target_url}")
            self.open_visible_browser_requested.emit()
            self.refresh_snapshot()
        except Exception as e:
            self.add_timeline_event(f"Failed to open visible window: {e}")

    def set_session_mode(self, mode: str, endpoint_or_info: str = ""):
        """Update session mode badge display."""
        if mode == "cdp":
            self.session_mode_badge.setText(f"● Chrome CDP ({endpoint_or_info or ':9222'})")
            self.session_mode_badge.setStyleSheet("""
                background: #064e3b; color: #34d399; font-size: 10px; font-weight: 600;
                padding: 2px 6px; border-radius: 4px; border: 1px solid #059669;
            """)
        elif mode == "existing_chrome":
            info_str = f" ({endpoint_or_info})" if endpoint_or_info else ""
            self.session_mode_badge.setText(f"● Existing Chrome{info_str}")
            self.session_mode_badge.setStyleSheet("""
                background: #064e3b; color: #34d399; font-size: 10px; font-weight: 600;
                padding: 2px 6px; border-radius: 4px; border: 1px solid #059669;
            """)
        elif mode == "persistent_profile":
            self.session_mode_badge.setText("● Persistent Profile")
            self.session_mode_badge.setStyleSheet("""
                background: #1e3a5f; color: #38bdf8; font-size: 10px; font-weight: 600;
                padding: 2px 6px; border-radius: 4px; border: 1px solid #0284c7;
            """)
        else:
            self.session_mode_badge.setText("○ Disconnected (Data Preserved)")
            self.session_mode_badge.setStyleSheet("""
                background: #21262d; color: #8b949e; font-size: 10px; font-weight: 600;
                padding: 2px 6px; border-radius: 4px; border: 1px solid #30363d;
            """)

    def _on_use_existing_session_clicked(self):
        """Attaches to desktop Chrome via CDP or safe Chrome session bridge."""
        try:
            from lmms.backend.tools.browser import get_browser_tool
            bt = get_browser_tool()
            url = self._current_url or (bt.page.url if bt.page else "about:blank")
            res = bt.attach_existing_chrome_session(url=url, headless=False)
            if res.get("status") == "connected":
                mode = res.get("mode", "existing_chrome")
                info = res.get("profile", "") if mode == "existing_chrome" else res.get("endpoint", ":9222")
                self.set_session_mode(mode, info)
                self.set_status_overlay("verified", f"Attached to Chrome ({mode}: {info})")
                self.add_timeline_event(f"Attached to desktop Chrome session ({mode}: {info})")
                self.refresh_snapshot()
            else:
                self.set_status_overlay("error", "Failed to attach existing Chrome session")
                self.add_timeline_event(f"Chrome attach error: {res.get('message', '')}")
        except Exception as e:
            self.add_timeline_event(f"Attach error: {e}")

    def _on_open_persistent_clicked(self):
        """Launches LMMs's persistent visible browser."""
        try:
            from lmms.backend.tools.browser import get_browser_tool
            bt = get_browser_tool()
            url = self._current_url or "about:blank"
            res = bt.open_persistent_browser(url=url, headless=False)
            if res.get("status") == "connected":
                self.set_session_mode("persistent_profile")
                self.set_status_overlay("navigating", "Opened persistent browser")
                self.add_timeline_event("Launched persistent visible browser (~/.lmms/browser_profile)")
                self.refresh_snapshot()
            else:
                self.set_status_overlay("error", "Failed to launch browser")
                self.add_timeline_event(f"Persistent launch error: {res.get('message', '')}")
        except Exception as e:
            self.add_timeline_event(f"Persistent launch failed: {e}")

    def _on_disconnect_clicked(self):
        """Explicitly disconnects session while preserving profile and cookies."""
        try:
            from lmms.backend.tools.browser import get_browser_tool
            bt = get_browser_tool()
            bt.disconnect_session(preserve_data=True)
            self.set_session_mode("none")
            self.set_status_overlay("idle", "Session disconnected")
            self.add_timeline_event("Disconnected active session (Profile and cookies preserved)")
        except Exception as e:
            self.add_timeline_event(f"Disconnect error: {e}")

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        # Re-scale active screenshot on panel resize
        if self._current_screenshot_path and os.path.exists(self._current_screenshot_path):
            pixmap = QPixmap(self._current_screenshot_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(scaled)
