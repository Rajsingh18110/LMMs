"""
lmms.gui.pages.mcp_page - MCP & Tools Studio Page.
Displays a responsive grid of MCP server cards, real-time status telemetry,
pulsing status indicators, quick add templates, and interactive server controls.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from lmms.gui.core.app_server_client import GUIAppServerClient, default_gui_client
from lmms.gui.dialogs.add_mcp_server_dialog import AddMCPServerDialog
from lmms.gui.qt import (
    QAction,
    QColor,
    QCursor,
    QEasingCurve,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QIcon,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPoint,
    QPropertyAnimation,
    QPushButton,
    QRect,
    QScrollArea,
    QSizePolicy,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
    run_coro_safe,
)


class PulsingDot(QWidget):
    """Status dot widget that pulses opacity when server is starting."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._color = QColor("#8b949e")
        self._opacity = 1.0

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(800)
        self.anim.setStartValue(0.3)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.setLoopCount(-1)

    def set_status(self, status: str) -> None:
        """Sets the dot color and pulse state."""
        if status == "connected":
            self.anim.stop()
            self.opacity_effect.setOpacity(1.0)
            self._color = QColor("#3fb950")  # Green
        elif status == "error":
            self.anim.stop()
            self.opacity_effect.setOpacity(1.0)
            self._color = QColor("#f85149")  # Red
        elif status == "starting":
            self._color = QColor("#d29922")  # Yellow
            if self.anim.state() != QPropertyAnimation.State.Running:
                self.anim.start()
        else:
            self.anim.stop()
            self.opacity_effect.setOpacity(0.6)
            self._color = QColor("#8b949e")  # Gray (disabled / stopped)

        self.update()

    def paintEvent(self, a0: Any) -> None:
        from lmms.gui.qt import QBrush, QPainter, QPen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._color))
        painter.drawEllipse(0, 0, 12, 12)


class ServerCard(QFrame):
    """Interactive card representing a single configured MCP server."""

    def __init__(
        self,
        server_data: Dict[str, Any],
        client: GUIAppServerClient,
        on_refresh: Any,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.server = server_data
        self.client = client
        self.on_refresh = on_refresh

        self.setObjectName("ServerCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(175)

        self.setStyleSheet("""
            QFrame#ServerCard {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 12px;
            }
            QFrame#ServerCard:hover {
                background-color: #272c35;
                border: 1px solid #58a6ff;
            }
            QLabel {
                color: #c9d1d9;
            }
            QPushButton {
                background-color: #30363d;
                color: #c9d1d9;
                border: 1px solid #484f58;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3c444d;
                border: 1px solid #58a6ff;
            }
            QPushButton#MenuBtn {
                font-weight: bold;
                padding: 2px 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header: Icon, Name, Pulsing Dot, Menu Button
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        icon_map = {
            "filesystem": "📁",
            "git": "🌿",
            "github": "🐙",
            "postgres": "🐘",
            "sqlite": "💾",
            "brave_search": "🔍",
            "fetch": "🌐",
            "memory": "🧠",
            "playwright": "🎭",
        }
        icon_str = icon_map.get(self.server.get("name", "").lower(), "⚡")

        icon_lbl = QLabel(icon_str)
        icon_lbl.setStyleSheet("font-size: 18px;")
        top_row.addWidget(icon_lbl)

        name_lbl = QLabel(self.server.get("name", "Unknown"))
        name_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        top_row.addWidget(name_lbl)

        self.dot = PulsingDot()
        self.dot.set_status("connected" if self.server.get("enabled", True) else "disabled")
        top_row.addWidget(self.dot)

        top_row.addStretch()

        self.menu_btn = QPushButton("•••")
        self.menu_btn.setObjectName("MenuBtn")
        self.menu_btn.setToolTip("Actions Menu")
        self.menu_btn.clicked.connect(self._show_context_menu)
        top_row.addWidget(self.menu_btn)

        layout.addLayout(top_row)

        # Command / Transport target
        cmd_text = self.server.get("command") or self.server.get("url") or "n/a"
        target_lbl = QLabel(cmd_text)
        target_lbl.setStyleSheet("font-size: 11px; color: #8b949e; font-family: monospace;")
        target_lbl.setWordWrap(True)
        layout.addWidget(target_lbl)

        # Badges row (Transport badge, Sandbox badge, Tool count badge)
        badges_row = QHBoxLayout()
        badges_row.setSpacing(6)

        transport = self.server.get("transport", "stdio").upper()
        tb = QLabel(f" {transport} ")
        tb.setStyleSheet("background-color: #1f6feb22; color: #58a6ff; border: 1px solid #1f6feb; border-radius: 4px; font-size: 10px; font-weight: bold;")
        badges_row.addWidget(tb)

        sandbox = self.server.get("sandbox", "none")
        sb_text = "🛡️ bwrap" if sandbox in ("bwrap", "sandboxed") else "🔓 host"
        sb = QLabel(f" {sb_text} ")
        sb_color = "#3fb950" if "bwrap" in sb_text else "#d29922"
        sb.setStyleSheet(f"background-color: {sb_color}1a; color: {sb_color}; border: 1px solid {sb_color}; border-radius: 4px; font-size: 10px; font-weight: bold;")
        badges_row.addWidget(sb)

        tools_cnt = len(self.server.get("tools", []))
        self.tools_badge = QLabel(f" ⚡ {tools_cnt} tools ")
        self.tools_badge.setStyleSheet("background-color: #30363d; color: #c9d1d9; border-radius: 4px; font-size: 10px;")
        badges_row.addWidget(self.tools_badge)

        badges_row.addStretch()
        layout.addLayout(badges_row)

        layout.addStretch()

        # Footer row: Enable/Disable Toggle button
        bottom_row = QHBoxLayout()
        self.is_enabled = self.server.get("enabled", True)
        self.toggle_btn = QPushButton("Enabled" if self.is_enabled else "Disabled")
        self._update_toggle_style()
        self.toggle_btn.clicked.connect(self._toggle_enabled)
        bottom_row.addWidget(self.toggle_btn)

        restart_btn = QPushButton("Restart")
        restart_btn.clicked.connect(self._restart_server)
        bottom_row.addWidget(restart_btn)

        bottom_row.addStretch()
        layout.addLayout(bottom_row)

    def _update_toggle_style(self) -> None:
        if self.is_enabled:
            self.toggle_btn.setText("✔ Enabled")
            self.toggle_btn.setStyleSheet("background-color: #238636; color: #ffffff; border: 1px solid #2ea043; border-radius: 4px; font-weight: bold;")
        else:
            self.toggle_btn.setText("✖ Disabled")
            self.toggle_btn.setStyleSheet("background-color: #21262d; color: #8b949e; border: 1px solid #30363d; border-radius: 4px;")

    def _toggle_enabled(self) -> None:
        name = self.server.get("name", "")
        self.is_enabled = not self.is_enabled
        self._update_toggle_style()
        self.dot.set_status("connected" if self.is_enabled else "disabled")

        async def _do_toggle():
            try:
                method = "mcp.enable" if self.is_enabled else "mcp.disable"
                await self.client.call(method, {"name": name})
                self.on_refresh()
            except Exception as e:
                QMessageBox.warning(self, "Action Failed", str(e))

        run_coro_safe(_do_toggle())

    def _restart_server(self) -> None:
        name = self.server.get("name", "")
        self.dot.set_status("starting")

        async def _do_restart():
            try:
                await self.client.call("mcp.restart", {"name": name})
                self.dot.set_status("connected")
                self.on_refresh()
            except Exception as e:
                self.dot.set_status("error")
                QMessageBox.warning(self, "Restart Failed", str(e))

        run_coro_safe(_do_restart())

    def _show_context_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #252526;
                color: #cccccc;
                border: 1px solid #454545;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #094771;
                color: #ffffff;
            }
        """)

        act_restart = QAction("Restart Server", self)
        act_restart.triggered.connect(self._restart_server)
        menu.addAction(act_restart)

        act_logs = QAction("View Logs", self)
        act_logs.triggered.connect(self._view_logs)
        menu.addAction(act_logs)

        menu.addSeparator()

        act_remove = QAction("Remove Server", self)
        act_remove.triggered.connect(self._remove_server)
        menu.addAction(act_remove)

        menu.exec(self.menu_btn.mapToGlobal(QPoint(0, self.menu_btn.height())))

    def _view_logs(self) -> None:
        name = self.server.get("name", "")

        async def _fetch():
            try:
                logs = await self.client.call("mcp.logs", {"name": name, "limit": 100})
                msg = "\n".join(logs) if logs else "No log messages recorded yet."
                QMessageBox.information(self, f"Logs: {name}", msg)
            except Exception as e:
                QMessageBox.warning(self, "Log Retrieval Error", str(e))

        run_coro_safe(_fetch())

    def _remove_server(self) -> None:
        name = self.server.get("name", "")
        reply = QMessageBox.question(
            self,
            "Confirm Server Removal",
            f"Are you sure you want to remove MCP server '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            async def _do_rm():
                try:
                    await self.client.call("mcp.remove", {"name": name})
                    self.on_refresh()
                except Exception as e:
                    QMessageBox.warning(self, "Removal Failed", str(e))

            run_coro_safe(_do_rm())


class MCPToolsPage(QWidget):
    """Main MCP & Tools studio view for PyQt6 desktop GUI."""

    def __init__(self, client: Optional[GUIAppServerClient] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.client = client or default_gui_client
        self.client.mcp_status_changed.connect(lambda _: self.load_servers())

        self.servers_data: List[Dict[str, Any]] = []
        self._is_light_theme = False

        self._build_ui()
        self.load_servers()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header Area
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title_lbl = QLabel("🛠️ MCP & Tools")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        header_row.addWidget(title_lbl)

        header_row.addStretch()

        # Search Bar
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search servers and tools...")
        self.search_box.setFixedWidth(240)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #21262d;
                color: #ffffff;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #58a6ff;
            }
        """)
        self.search_box.textChanged.connect(self._filter_servers)
        header_row.addWidget(self.search_box)

        # Add Server Button
        self.add_btn = QPushButton("+ Add Server")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border: 1px solid #2ea043;
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
        """)
        self.add_btn.clicked.connect(self._open_add_dialog)
        header_row.addWidget(self.add_btn)

        layout.addLayout(header_row)

        # Summary Chips Bar
        chips_row = QHBoxLayout()
        chips_row.setSpacing(10)

        self.chip_connected = QLabel("🟢 0 Connected")
        self.chip_connected.setStyleSheet("background-color: #3fb95022; color: #3fb950; border: 1px solid #3fb950; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: bold;")
        chips_row.addWidget(self.chip_connected)

        self.chip_errors = QLabel("🔴 0 Errors")
        self.chip_errors.setStyleSheet("background-color: #f8514922; color: #f85149; border: 1px solid #f85149; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: bold;")
        chips_row.addWidget(self.chip_errors)

        self.chip_total = QLabel("⚡ 0 Tools Total")
        self.chip_total.setStyleSheet("background-color: #30363d; color: #c9d1d9; border: 1px solid #484f58; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: bold;")
        chips_row.addWidget(self.chip_total)

        chips_row.addStretch()
        layout.addLayout(chips_row)

        # Main Scroll Content (Server Cards Grid & States)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.scroll_content = QWidget()
        self.grid = QGridLayout(self.scroll_content)
        self.grid.setSpacing(14)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        # Empty State Container
        self.empty_state_widget = QFrame()
        self.empty_state_widget.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 2px dashed #30363d;
                border-radius: 10px;
                padding: 40px;
            }
        """)
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(12)

        e_icon = QLabel("🔌")
        e_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        e_icon.setStyleSheet("font-size: 48px;")
        empty_layout.addWidget(e_icon)

        e_title = QLabel("No MCP Servers Configured Yet")
        e_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        e_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        empty_layout.addWidget(e_title)

        e_sub = QLabel("Supercharge your agents with local and offline tools using Model Context Protocol.")
        e_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        e_sub.setStyleSheet("font-size: 12px; color: #8b949e;")
        empty_layout.addWidget(e_sub)

        e_btn = QPushButton("+ Add Your First Server")
        e_btn.setStyleSheet("background-color: #238636; color: #ffffff; padding: 8px 18px; border-radius: 6px; font-weight: bold;")
        e_btn.clicked.connect(self._open_add_dialog)
        empty_layout.addWidget(e_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.empty_state_widget)
        self.empty_state_widget.hide()

    def set_theme(self, is_light: bool) -> None:
        """Dynamically applies light or dark theme styling to the page."""
        self._is_light_theme = is_light
        bg = "#ffffff" if is_light else "#1e1e1e"
        fg = "#1f2328" if is_light else "#ffffff"
        self.setStyleSheet(f"background-color: {bg}; color: {fg};")
        self.load_servers()

    def _open_add_dialog(self) -> None:
        dlg = AddMCPServerDialog(client=self.client, parent=self)
        if dlg.exec():
            self.load_servers()

    def load_servers(self) -> None:
        """Queries app-server for configured servers and updates card grid."""
        async def _fetch():
            try:
                # Query templates & active tools
                tools = await self.client.call("mcp.tools")
                perms = await self.client.call("permissions.get")

                # Reconstruct servers from dispatcher config
                if hasattr(self.client, "mock_dispatcher") and self.client.mock_dispatcher:
                    cfg_servers = self.client.mock_dispatcher.mcp_config.list_servers()
                    servers = [s.to_dict() for s in cfg_servers]
                else:
                    # In live app-server, query tools and construct active list
                    servers = []
                    seen_servers = set()
                    for t in (tools or []):
                        s_name = t.get("server")
                        if s_name and s_name not in seen_servers:
                            seen_servers.add(s_name)
                            servers.append({
                                "name": s_name,
                                "command": "active stdio",
                                "transport": "stdio",
                                "enabled": True,
                                "sandbox": "bwrap",
                                "tools": [x for x in tools if x.get("server") == s_name],
                            })

                self.servers_data = servers
                self._render_cards(self.servers_data)

            except Exception as e:
                # If server not yet running, display mock fallback or clean empty state
                self._render_cards([])

        run_coro_safe(_fetch())

    def _render_cards(self, servers: List[Dict[str, Any]]) -> None:
        # Clear existing items
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        if not servers:
            self.empty_state_widget.show()
            self.scroll_area.hide()
            self._update_chips(0, 0, 0)
            return

        self.empty_state_widget.hide()
        self.scroll_area.show()

        connected_cnt = sum(1 for s in servers if s.get("enabled", True))
        error_cnt = sum(1 for s in servers if s.get("status") == "error")
        total_tools = sum(len(s.get("tools", [])) for s in servers)
        self._update_chips(connected_cnt, error_cnt, total_tools)

        cols = 2
        for idx, s in enumerate(servers):
            card = ServerCard(server_data=s, client=self.client, on_refresh=self.load_servers)
            row = idx // cols
            col = idx % cols
            self.grid.addWidget(card, row, col)

    def _update_chips(self, connected: int, errors: int, total_tools: int) -> None:
        self.chip_connected.setText(f"🟢 {connected} Connected")
        self.chip_errors.setText(f"🔴 {errors} Errors")
        self.chip_total.setText(f"⚡ {total_tools} Tools Total")

    def _filter_servers(self, query: str) -> None:
        q = query.strip().lower()
        if not q:
            self._render_cards(self.servers_data)
            return

        filtered = [
            s for s in self.servers_data
            if q in s.get("name", "").lower()
            or q in str(s.get("command", "")).lower()
            or any(q in t.get("name", "").lower() for t in s.get("tools", []))
        ]
        self._render_cards(filtered)
