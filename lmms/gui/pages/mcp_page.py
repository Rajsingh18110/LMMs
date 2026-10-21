"""
lmms.gui.pages.mcp_page - MCP & Tools Studio Page.
Includes:
- Top Reconnect/Offline Banner with automatic backoff updates and manual Retry button.
- 5 Unified Studio Tabs:
  1. Servers: Responsive card grid, telemetry chips, templates, enable/disable/restart/edit/remove.
  2. Tool Browser: Searchable grouped tree, dynamic JSON schema form generator, execution runner, JSON tree/raw text/image viewer.
  3. Live Call Log: Real-time mcp.tool_call stream, audit log history, filters, duration, secret redaction, and pyqtgraph latency chart.
  4. Permissions: Per-server and per-tool allow/ask/deny matrix, and non-blocking approval banner.
  5. Sandbox: bwrap/Landlock diagnostic status, prominent "NOT isolated" warning, and ExecPolicy editor.
- Empty, Loading, and Error States.
- Dark and Light Theme support.
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
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPoint,
    QProgressBar,
    QPropertyAnimation,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
    run_coro_safe,
    Qt,
)
from lmms.gui.widgets.mcp_tabs import (
    LiveCallLogWidget,
    PermissionsWidget,
    SandboxWidget,
    ToolBrowserWidget,
)


class PulsingDot(QWidget):
    """Status dot widget that pulses opacity when server is starting."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._color = QColor("#8b949e")

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
            self._color = QColor("#8b949e")  # Gray

        self.update()

    def paintEvent(self, a0: Any) -> None:
        from lmms.gui.qt import QBrush, QPainter
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

        # Badges row
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

        # Footer row: Toggle & Restart
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

        act_edit = QAction("Edit Server...", self)
        act_edit.triggered.connect(self._edit_server)
        menu.addAction(act_edit)

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

    def _edit_server(self) -> None:
        dlg = AddMCPServerDialog(client=self.client, server_data=self.server, parent=self)
        if dlg.exec():
            self.on_refresh()

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

        self.servers_data: List[Dict[str, Any]] = []
        self._is_light_theme = False

        self._build_ui()
        self._wire_client_signals()
        self.load_servers()

    def _wire_client_signals(self) -> None:
        self.client.mcp_status_changed.connect(lambda _: self.load_servers())
        self.client.reconnecting.connect(self._on_reconnecting)
        self.client.connected.connect(self._on_connected)
        self.client.disconnected.connect(self._on_disconnected)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(14)

        # 1. Top Reconnect / Status Banner (Hidden by default)
        self.reconnect_banner = QFrame()
        self.reconnect_banner.setStyleSheet("""
            QFrame {
                background-color: #d2992222;
                border: 1px solid #d29922;
                border-radius: 6px;
                padding: 8px 12px;
            }
        """)
        rb_layout = QHBoxLayout(self.reconnect_banner)
        rb_layout.setContentsMargins(8, 4, 8, 4)

        self.banner_icon = QLabel("⚠️")
        self.banner_icon.setStyleSheet("font-size: 14px;")
        rb_layout.addWidget(self.banner_icon)

        self.banner_text = QLabel("Connecting to LMMs App-Server...")
        self.banner_text.setStyleSheet("color: #d29922; font-weight: bold; font-size: 12px;")
        rb_layout.addWidget(self.banner_text)

        rb_layout.addStretch()

        self.banner_retry_btn = QPushButton("Retry Now")
        self.banner_retry_btn.setStyleSheet("""
            QPushButton {
                background-color: #d29922;
                color: #000000;
                font-weight: bold;
                padding: 4px 12px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #e3b341;
            }
        """)
        self.banner_retry_btn.clicked.connect(self._manual_retry_connection)
        rb_layout.addWidget(self.banner_retry_btn)

        self.reconnect_banner.hide()
        layout.addWidget(self.reconnect_banner)

        # 1.5 Studio-wide Tool Approval Banner
        self.approval_banner = QFrame()
        self.approval_banner.setStyleSheet("""
            QFrame {
                background-color: #1f6feb22;
                border: 1px solid #58a6ff;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        ab_layout = QHBoxLayout(self.approval_banner)
        ab_layout.setContentsMargins(12, 8, 12, 8)
        ab_layout.setSpacing(12)

        self.ab_text = QLabel("🔔 Pending Tool Approval")
        self.ab_text.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold;")
        ab_layout.addWidget(self.ab_text)

        ab_layout.addStretch()

        self.btn_banner_approve_once = QPushButton("✔ Approve Once")
        self.btn_banner_approve_once.setStyleSheet("background-color: #238636; color: #ffffff; padding: 4px 12px; border-radius: 4px; font-weight: bold;")
        self.btn_banner_approve_once.clicked.connect(lambda: self._handle_approval_decision(always=False))
        ab_layout.addWidget(self.btn_banner_approve_once)

        self.btn_banner_always_allow = QPushButton("⭐ Always Allow")
        self.btn_banner_always_allow.setStyleSheet("background-color: #1f6feb; color: #ffffff; padding: 4px 12px; border-radius: 4px; font-weight: bold;")
        self.btn_banner_always_allow.clicked.connect(lambda: self._handle_approval_decision(always=True))
        ab_layout.addWidget(self.btn_banner_always_allow)

        self.btn_banner_deny = QPushButton("✖ Deny")
        self.btn_banner_deny.setStyleSheet("background-color: #da3633; color: #ffffff; padding: 4px 12px; border-radius: 4px; font-weight: bold;")
        self.btn_banner_deny.clicked.connect(self._handle_deny_decision)
        ab_layout.addWidget(self.btn_banner_deny)

        self.approval_banner.hide()
        layout.addWidget(self.approval_banner)
        self.client.tool_permission_request.connect(self._show_approval_banner)

        # 2. Main Page Header
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        self.title_lbl = QLabel("🛠️ MCP & Tools Studio")
        self.title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        header_row.addWidget(self.title_lbl)

        header_row.addStretch()

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

        # 3. Studio Tabs (Servers, Tool Browser, Live Call Log, Permissions, Sandbox)
        self.main_tabs = QTabWidget()
        self.main_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363d;
                background-color: #161b22;
                border-radius: 8px;
                padding: 10px;
            }
            QTabBar::tab {
                background: #21262d;
                color: #8b949e;
                padding: 8px 18px;
                border: 1px solid #30363d;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
                font-size: 12px;
                font-weight: 500;
            }
            QTabBar::tab:hover {
                background: #272c35;
                color: #c9d1d9;
            }
            QTabBar::tab:selected {
                background: #161b22;
                color: #58a6ff;
                font-weight: bold;
                border-bottom: 2px solid #58a6ff;
            }
        """)

        # Tab 0: Servers Tab
        self.servers_tab = QWidget()
        self._build_servers_tab()
        self.main_tabs.addTab(self.servers_tab, "🛠️ Servers")

        # Tab 1: Tool Browser Tab
        self.tool_browser_tab = ToolBrowserWidget(client=self.client)
        self.main_tabs.addTab(self.tool_browser_tab, "⚡ Tool Browser")

        # Tab 2: Live Call Log Tab
        self.call_log_tab = LiveCallLogWidget(client=self.client)
        self.main_tabs.addTab(self.call_log_tab, "📜 Live Call Log")

        # Tab 3: Permissions Tab
        self.permissions_tab = PermissionsWidget(client=self.client)
        self.main_tabs.addTab(self.permissions_tab, "🛡️ Permissions")

        # Tab 4: Sandbox Tab
        self.sandbox_tab = SandboxWidget(client=self.client)
        self.main_tabs.addTab(self.sandbox_tab, "📦 Sandbox")

        layout.addWidget(self.main_tabs)

    def _build_servers_tab(self) -> None:
        st_layout = QVBoxLayout(self.servers_tab)
        st_layout.setContentsMargins(8, 8, 8, 8)
        st_layout.setSpacing(12)

        # Search Bar & Telemetry Row
        telemetry_row = QHBoxLayout()
        telemetry_row.setSpacing(10)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search servers and tools...")
        self.search_box.setFixedWidth(260)
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
        telemetry_row.addWidget(self.search_box)

        self.chip_connected = QLabel("🟢 0 Connected")
        self.chip_connected.setStyleSheet("background-color: #3fb95022; color: #3fb950; border: 1px solid #3fb950; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: bold;")
        telemetry_row.addWidget(self.chip_connected)

        self.chip_errors = QLabel("🔴 0 Errors")
        self.chip_errors.setStyleSheet("background-color: #f8514922; color: #f85149; border: 1px solid #f85149; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: bold;")
        telemetry_row.addWidget(self.chip_errors)

        self.chip_total = QLabel("⚡ 0 Tools Total")
        self.chip_total.setStyleSheet("background-color: #30363d; color: #c9d1d9; border: 1px solid #484f58; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: bold;")
        telemetry_row.addWidget(self.chip_total)

        telemetry_row.addStretch()
        st_layout.addLayout(telemetry_row)

        # Loading Indicator State
        self.loading_widget = QFrame()
        self.loading_widget.setStyleSheet("background: transparent;")
        lw_layout = QVBoxLayout(self.loading_widget)
        lw_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setFixedWidth(200)
        lw_layout.addWidget(self.loading_bar)
        loading_text = QLabel("Querying MCP servers and health status...")
        loading_text.setStyleSheet("color: #8b949e; font-size: 12px;")
        lw_layout.addWidget(loading_text, alignment=Qt.AlignmentFlag.AlignCenter)
        self.loading_widget.hide()
        st_layout.addWidget(self.loading_widget)

        # Server Cards Grid Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.scroll_content = QWidget()
        self.grid = QGridLayout(self.scroll_content)
        self.grid.setSpacing(14)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.scroll_content)
        st_layout.addWidget(self.scroll_area)

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

        st_layout.addWidget(self.empty_state_widget)
        self.empty_state_widget.hide()

        # Error State Container
        self.error_state_widget = QFrame()
        self.error_state_widget.setStyleSheet("""
            QFrame {
                background-color: #f851491a;
                border: 2px solid #f85149;
                border-radius: 10px;
                padding: 30px;
            }
        """)
        err_layout = QVBoxLayout(self.error_state_widget)
        err_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        err_layout.setSpacing(10)

        err_icon = QLabel("⚠️")
        err_icon.setStyleSheet("font-size: 40px;")
        err_layout.addWidget(err_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        self.err_title = QLabel("Cannot Connect to LMMs App-Server")
        self.err_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f85149;")
        err_layout.addWidget(self.err_title, alignment=Qt.AlignmentFlag.AlignCenter)

        self.err_sub = QLabel("The daemon socket is unreachable. The server may have stopped or is starting.")
        self.err_sub.setStyleSheet("font-size: 12px; color: #c9d1d9;")
        err_layout.addWidget(self.err_sub, alignment=Qt.AlignmentFlag.AlignCenter)

        err_retry_btn = QPushButton("🔄 Start App-Server & Retry")
        err_retry_btn.setStyleSheet("background-color: #238636; color: #ffffff; padding: 8px 20px; border-radius: 6px; font-weight: bold;")
        err_retry_btn.clicked.connect(self._manual_retry_connection)
        err_layout.addWidget(err_retry_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        st_layout.addWidget(self.error_state_widget)
        self.error_state_widget.hide()

    def _on_reconnecting(self, attempt: int, delay: float) -> None:
        self.banner_icon.setText("⚠️")
        self.banner_text.setText(f"Reconnecting to app-server (attempt {attempt} in {delay:.1f}s)...")
        self.reconnect_banner.setStyleSheet("background-color: #d2992222; border: 1px solid #d29922; border-radius: 6px; padding: 8px 12px;")
        self.reconnect_banner.show()

    def _on_connected(self) -> None:
        self.reconnect_banner.hide()
        self.error_state_widget.hide()
        self.load_servers()
        self.tool_browser_tab.load_tools()
        self.call_log_tab.load_history()
        self.permissions_tab.load_permissions()
        self.sandbox_tab.load_status()

    def _on_disconnected(self) -> None:
        self.banner_icon.setText("🔴")
        self.banner_text.setText("App-Server connection dropped. Attempting automatic reconnection...")
        self.reconnect_banner.setStyleSheet("background-color: #f8514922; border: 1px solid #f85149; border-radius: 6px; padding: 8px 12px;")
        self.reconnect_banner.show()

    def _manual_retry_connection(self) -> None:
        self.banner_text.setText("Connecting to app-server...")

        async def _do_retry():
            ok = await self.client.ensure_server_running()
            if ok:
                self.reconnect_banner.hide()
                self.error_state_widget.hide()
                self.load_servers()
            else:
                self.error_state_widget.show()
                self.scroll_area.hide()
                self.empty_state_widget.hide()

        run_coro_safe(_do_retry())

    def set_theme(self, is_light: bool) -> None:
        """Dynamically applies light or dark theme styling to the page."""
        self._is_light_theme = is_light
        bg = "#f6f8fa" if is_light else "#0d1117"
        fg = "#1f2328" if is_light else "#ffffff"
        self.setStyleSheet(f"background-color: {bg}; color: {fg};")
        if hasattr(self, "title_lbl"):
            self.title_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {fg};")
        self.load_servers()

    def _open_add_dialog(self) -> None:
        dlg = AddMCPServerDialog(client=self.client, parent=self)
        if dlg.exec():
            self.load_servers()

    def load_servers(self) -> None:
        """Queries app-server for configured servers and updates card grid."""
        async def _fetch():
            try:
                tools = await self.client.call("mcp.tools")
                if hasattr(self.client, "mock_dispatcher") and self.client.mock_dispatcher:
                    cfg_servers = self.client.mock_dispatcher.mcp_config.list_servers()
                    servers = [s.to_dict() for s in cfg_servers]
                else:
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
                self.error_state_widget.hide()
                self._render_cards(self.servers_data)

            except Exception:
                if not self.client.mock_dispatcher:
                    self.scroll_area.hide()
                    self.empty_state_widget.hide()
                    self.error_state_widget.show()
                else:
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

    def _show_approval_banner(self, req: Dict[str, Any]) -> None:
        self._current_permission_request = req
        tool = req.get("tool_name", "tool")
        server = req.get("server_name", "server")
        self.ab_text.setText(f"🔔 Permission Request: Execute '{tool}' on '{server}'?")
        self.approval_banner.show()

    def _handle_approval_decision(self, always: bool = False) -> None:
        if not hasattr(self, "_current_permission_request") or not self._current_permission_request:
            return
        req = self._current_permission_request
        pid = req.get("prompt_id")
        server = req.get("server_name")
        tool = req.get("tool_name")
        self.approval_banner.hide()

        async def _do():
            if always and server and tool:
                await self.client.call("permissions.set", {"server": server, "tool": tool, "policy": "allow"})
            if pid:
                await self.client.call("tool.approve", {"prompt_id": pid})

        run_coro_safe(_do())
        self._current_permission_request = None

    def _handle_deny_decision(self) -> None:
        if not hasattr(self, "_current_permission_request") or not self._current_permission_request:
            return
        pid = self._current_permission_request.get("prompt_id")
        self.approval_banner.hide()

        async def _do():
            if pid:
                await self.client.call("tool.deny", {"prompt_id": pid})

        run_coro_safe(_do())
        self._current_permission_request = None
