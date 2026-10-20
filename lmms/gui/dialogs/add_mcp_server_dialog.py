"""
lmms.gui.dialogs.add_mcp_server_dialog - Add MCP Server Dialog.
Features a 9-item Curated Template Gallery and a Custom Server Configuration form
with transport selector, environment variables editor, sandbox toggle, and connection testing.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from lmms.gui.core.app_server_client import GUIAppServerClient
from lmms.gui.qt import (
    QBrush,
    QColor,
    QComboBox,
    QCursor,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QIcon,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    Qt,
    QVBoxLayout,
    QWidget,
    run_coro_safe,
)
from lmms_mcp.config import CURATED_TEMPLATES


class TemplateCard(QFrame):
    """Clickable preset card in the template gallery."""

    def __init__(self, key: str, tmpl: Dict[str, Any], on_select: Any, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.key = key
        self.tmpl = tmpl
        self.on_select = on_select

        self.setObjectName("TemplateCard")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            QFrame#TemplateCard {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 10px;
            }
            QFrame#TemplateCard:hover {
                background-color: #2d2d30;
                border: 1px solid #007fd4;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

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
        icon_str = icon_map.get(key.lower(), "⚡")

        title_lbl = QLabel(f"{icon_str}  {key.replace('_', ' ').title()}")
        title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(tmpl.get("description", ""))
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 11px; color: #8b949e;")
        layout.addWidget(desc_lbl)

        cmd = tmpl.get("command", tmpl.get("url", ""))
        badge = QLabel(f"Transport: {tmpl.get('transport', 'stdio')} · {cmd}")
        badge.setStyleSheet("font-size: 10px; color: #58a6ff; font-family: monospace;")
        layout.addWidget(badge)

    def mousePressEvent(self, a0: Any) -> None:
        if a0 is not None and a0.button() == Qt.MouseButton.LeftButton:
            self.on_select(self.key, self.tmpl)
        super().mousePressEvent(a0)


class AddMCPServerDialog(QDialog):
    """Dialog for adding or configuring an MCP server."""

    def __init__(self, client: GUIAppServerClient, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.client = client
        self.created_server: Optional[Dict[str, Any]] = None

        self.setWindowTitle("Add MCP Server")
        self.resize(680, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #cccccc;
            }
            QTabWidget::pane {
                border: 1px solid #30363d;
                background-color: #1e1e1e;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #252526;
                color: #8b949e;
                padding: 8px 16px;
                border: 1px solid #30363d;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #1e1e1e;
                color: #58a6ff;
                border-bottom: 2px solid #58a6ff;
                font-weight: bold;
            }
            QLabel {
                font-size: 12px;
                color: #cccccc;
            }
            QLineEdit, QComboBox {
                background-color: #252526;
                color: #ffffff;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #58a6ff;
            }
            QPushButton {
                background-color: #30363d;
                color: #c9d1d9;
                border: 1px solid #484f58;
                border-radius: 4px;
                padding: 7px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3c444d;
            }
            QPushButton#PrimaryBtn {
                background-color: #238636;
                color: #ffffff;
                border: 1px solid #2ea043;
            }
            QPushButton#PrimaryBtn:hover {
                background-color: #2ea043;
            }
            QTableWidget {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                gridline-color: #30363d;
                color: #ffffff;
            }
        """)

        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        header = QLabel("🔌 Add Model Context Protocol (MCP) Server")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        main_layout.addWidget(header)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Template Gallery
        self.gallery_tab = QWidget()
        gallery_layout = QVBoxLayout(self.gallery_tab)
        gallery_layout.setContentsMargins(12, 12, 12, 12)

        info_lbl = QLabel("Choose a curated offline-ready template or switch to the Custom tab:")
        info_lbl.setStyleSheet("color: #8b949e; margin-bottom: 8px;")
        gallery_layout.addWidget(info_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll_content = QWidget()
        self.grid = QGridLayout(scroll_content)
        self.grid.setSpacing(10)

        templates_list = list(CURATED_TEMPLATES.items())
        for idx, (t_key, t_data) in enumerate(templates_list):
            card = TemplateCard(t_key, t_data, on_select=self._apply_template)
            row = idx // 2
            col = idx % 2
            self.grid.addWidget(card, row, col)

        scroll.setWidget(scroll_content)
        gallery_layout.addWidget(scroll)
        self.tabs.addTab(self.gallery_tab, "Template Gallery")

        # Tab 2: Custom Server Form
        self.custom_tab = QWidget()
        form_layout = QVBoxLayout(self.custom_tab)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(10)

        # Server Name
        name_row = QHBoxLayout()
        name_lbl = QLabel("Server Name:")
        name_lbl.setFixedWidth(110)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. github, filesystem, my-db")
        name_row.addWidget(name_lbl)
        name_row.addWidget(self.name_edit)
        form_layout.addLayout(name_row)

        # Transport
        trans_row = QHBoxLayout()
        trans_lbl = QLabel("Transport:")
        trans_lbl.setFixedWidth(110)
        self.trans_combo = QComboBox()
        self.trans_combo.addItems(["stdio", "sse", "http"])
        self.trans_combo.currentTextChanged.connect(self._on_transport_changed)
        trans_row.addWidget(trans_lbl)
        trans_row.addWidget(self.trans_combo)
        form_layout.addLayout(trans_row)

        # Command or URL
        self.cmd_row = QHBoxLayout()
        self.cmd_lbl = QLabel("Command:")
        self.cmd_lbl.setFixedWidth(110)
        self.cmd_edit = QLineEdit()
        self.cmd_edit.setPlaceholderText("e.g. npx, uvx, python3, /usr/bin/tool")
        self.cmd_row.addWidget(self.cmd_lbl)
        self.cmd_row.addWidget(self.cmd_edit)
        form_layout.addLayout(self.cmd_row)

        # Arguments
        self.args_row = QHBoxLayout()
        args_lbl = QLabel("Arguments:")
        args_lbl.setFixedWidth(110)
        self.args_edit = QLineEdit()
        self.args_edit.setPlaceholderText("Space-separated arguments, e.g. -y @modelcontextprotocol/server-filesystem /path")
        self.args_row.addWidget(args_lbl)
        self.args_row.addWidget(self.args_edit)
        form_layout.addLayout(self.args_row)

        # Sandbox Profile
        sand_row = QHBoxLayout()
        sand_lbl = QLabel("Sandbox Profile:")
        sand_lbl.setFixedWidth(110)
        self.sand_combo = QComboBox()
        self.sand_combo.addItems(["bwrap (Bubblewrap Isolated)", "none (Host Execution)"])
        sand_row.addWidget(sand_lbl)
        sand_row.addWidget(self.sand_combo)
        form_layout.addLayout(sand_row)

        # Environment Table
        env_header_row = QHBoxLayout()
        env_lbl = QLabel("Environment Variables:")
        env_lbl.setStyleSheet("font-weight: bold; color: #ffffff;")
        add_env_btn = QPushButton("+ Add Variable")
        add_env_btn.clicked.connect(self._add_env_row)
        del_env_btn = QPushButton("- Remove Selected")
        del_env_btn.clicked.connect(self._remove_env_row)
        env_header_row.addWidget(env_lbl)
        env_header_row.addStretch()
        env_header_row.addWidget(add_env_btn)
        env_header_row.addWidget(del_env_btn)
        form_layout.addLayout(env_header_row)

        self.env_table = QTableWidget(0, 2)
        self.env_table.setHorizontalHeaderLabels(["Variable Name", "Value"])
        table_hdr = self.env_table.horizontalHeader()
        if table_hdr is not None:
            table_hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.env_table.setFixedHeight(120)
        form_layout.addWidget(self.env_table)

        # Test Status Label
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size: 11px;")
        form_layout.addWidget(self.status_lbl)

        self.tabs.addTab(self.custom_tab, "Custom Server Form")

        # Dialog Buttons
        btn_layout = QHBoxLayout()
        test_btn = QPushButton("🔍 Test Connection")
        test_btn.clicked.connect(self._test_connection)
        btn_layout.addWidget(test_btn)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        add_btn = QPushButton("✔ Add Server")
        add_btn.setObjectName("PrimaryBtn")
        add_btn.clicked.connect(self._submit)
        btn_layout.addWidget(add_btn)

        main_layout.addLayout(btn_layout)

    def _apply_template(self, key: str, tmpl: Dict[str, Any]) -> None:
        """Loads a chosen curated template into custom form and focuses it."""
        self.name_edit.setText(key)
        transport = tmpl.get("transport", "stdio")
        self.trans_combo.setCurrentText(transport)
        self.cmd_edit.setText(tmpl.get("command", tmpl.get("url", "")))
        self.args_edit.setText(" ".join(tmpl.get("args", [])))

        sandbox_val = tmpl.get("sandbox", "none")
        if sandbox_val == "bwrap":
            self.sand_combo.setCurrentIndex(0)
        else:
            self.sand_combo.setCurrentIndex(1)

        # Populate environment
        self.env_table.setRowCount(0)
        for k, v in tmpl.get("env", {}).items():
            r = self.env_table.rowCount()
            self.env_table.insertRow(r)
            self.env_table.setItem(r, 0, QTableWidgetItem(k))
            self.env_table.setItem(r, 1, QTableWidgetItem(str(v)))

        self.status_lbl.setText(f"Template '{key}' applied. Ready to test or add.")
        self.status_lbl.setStyleSheet("color: #58a6ff;")
        self.tabs.setCurrentIndex(1)

    def _on_transport_changed(self, transport: str) -> None:
        if transport == "stdio":
            self.cmd_lbl.setText("Command:")
            self.cmd_edit.setPlaceholderText("e.g. npx, uvx, python3")
            self.args_row.setEnabled(True)
        else:
            self.cmd_lbl.setText("URL:")
            self.cmd_edit.setPlaceholderText("e.g. http://localhost:8080/sse")
            self.args_row.setEnabled(False)

    def _add_env_row(self) -> None:
        r = self.env_table.rowCount()
        self.env_table.insertRow(r)
        self.env_table.setItem(r, 0, QTableWidgetItem("KEY"))
        self.env_table.setItem(r, 1, QTableWidgetItem(""))

    def _remove_env_row(self) -> None:
        r = self.env_table.currentRow()
        if r >= 0:
            self.env_table.removeRow(r)

    def _get_form_payload(self) -> Dict[str, Any]:
        name = self.name_edit.text().strip()
        transport = self.trans_combo.currentText()
        cmd_or_url = self.cmd_edit.text().strip()
        args = [a for a in self.args_edit.text().strip().split() if a]
        sandbox = "bwrap" if self.sand_combo.currentIndex() == 0 else "none"

        env: Dict[str, str] = {}
        for r in range(self.env_table.rowCount()):
            k_item = self.env_table.item(r, 0)
            v_item = self.env_table.item(r, 1)
            if k_item and k_item.text().strip():
                env[k_item.text().strip()] = v_item.text() if v_item else ""

        payload = {
            "name": name,
            "transport": transport,
            "env": env,
            "sandbox": sandbox,
            "enabled": True,
        }
        if transport == "stdio":
            payload["command"] = cmd_or_url
            payload["args"] = args
        else:
            payload["url"] = cmd_or_url

        return payload

    def _test_connection(self) -> None:
        payload = self._get_form_payload()
        if not payload["name"] or not (payload.get("command") or payload.get("url")):
            self.status_lbl.setText("Error: Server name and command/URL are required to test.")
            self.status_lbl.setStyleSheet("color: #f85149;")
            return

        self.status_lbl.setText("Testing connection...")
        self.status_lbl.setStyleSheet("color: #d29922;")

        async def _do_test():
            try:
                # Add server temporarily then test
                await self.client.call("mcp.add", payload)
                res = await self.client.call("mcp.test", {"name": payload["name"]})
                if res.get("connected"):
                    tool_cnt = len(res.get("tools", []))
                    self.status_lbl.setText(f"✔ Connection successful! Discovered {tool_cnt} tools.")
                    self.status_lbl.setStyleSheet("color: #3fb950;")
                else:
                    err = res.get("error", "Unknown error")
                    self.status_lbl.setText(f"✖ Test failed: {err}")
                    self.status_lbl.setStyleSheet("color: #f85149;")
            except Exception as e:
                self.status_lbl.setText(f"✖ Error: {e}")
                self.status_lbl.setStyleSheet("color: #f85149;")

        run_coro_safe(_do_test())

    def _submit(self) -> None:
        payload = self._get_form_payload()
        if not payload["name"]:
            QMessageBox.warning(self, "Validation Error", "Server name is required.")
            return

        if payload["transport"] == "stdio" and not payload.get("command"):
            QMessageBox.warning(self, "Validation Error", "Command is required for stdio transport.")
            return
        elif payload["transport"] != "stdio" and not payload.get("url"):
            QMessageBox.warning(self, "Validation Error", "URL is required for network transport.")
            return

        async def _do_add():
            try:
                res = await self.client.call("mcp.add", payload)
                self.created_server = res
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Failed to Add Server", str(e))

        run_coro_safe(_do_add())

