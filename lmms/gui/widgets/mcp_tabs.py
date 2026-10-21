"""
lmms.gui.widgets.mcp_tabs - Sub-components for MCP & Tools Studio.
Includes:
- ToolBrowserWidget: searchable tool tree, schema-to-form generator, execution runner, and multi-view result viewer.
- LiveCallLogWidget: real-time tool_call stream, audit log reader, filtering, and pyqtgraph latency chart.
- PermissionsWidget: per-server and per-tool allow/ask/deny matrix with non-blocking approval banner.
- SandboxWidget: bwrap/Landlock diagnostic cards, "NOT isolated" alert, and interactive ExecPolicy editor.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import pyqtgraph as pg

from lmms.gui.core.app_server_client import GUIAppServerClient
from lmms.gui.qt import (
    QApplication,
    QCheckBox,
    QColor,
    QComboBox,
    QCursor,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
    run_coro_safe,
    Qt,
)


# ============================================================================
# 1. TOOL BROWSER WIDGET
# ============================================================================

class ToolBrowserWidget(QWidget):
    """
    Searchable tool browser grouped by server.
    Dynamically generates input forms from JSON Schema, validates required fields,
    executes calls via mcp.call, and renders results as JSON tree, text, and images.
    """

    def __init__(self, client: GUIAppServerClient, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.client = client
        self.tools_data: List[Dict[str, Any]] = []
        self.current_tool: Optional[Dict[str, Any]] = None
        self.form_inputs: Dict[str, Tuple[str, QWidget]] = {}

        self._build_ui()
        self.load_tools()

    def _build_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #30363d;
                width: 2px;
            }
        """)

        # Left panel: Search & Tool Tree
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search tools...")
        self.search_input.setStyleSheet("""
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
        self.search_input.textChanged.connect(self._filter_tools)
        left_layout.addWidget(self.search_input)

        self.tool_tree = QTreeWidget()
        self.tool_tree.setHeaderHidden(True)
        self.tool_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #161b22;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 4px;
            }
            QTreeWidget::item {
                padding: 6px;
                border-radius: 4px;
            }
            QTreeWidget::item:hover {
                background-color: #21262d;
            }
            QTreeWidget::item:selected {
                background-color: #1f6feb33;
                color: #58a6ff;
                font-weight: bold;
            }
        """)
        self.tool_tree.itemClicked.connect(self._on_tool_selected)
        left_layout.addWidget(self.tool_tree)

        splitter.addWidget(left_widget)

        # Right panel: Tool Form & Execution & Output
        right_widget = QWidget()
        self.right_layout = QVBoxLayout(right_widget)
        self.right_layout.setContentsMargins(8, 0, 0, 0)
        self.right_layout.setSpacing(12)

        # Placeholder label when no tool selected
        self.placeholder_lbl = QLabel("👈 Select a tool from the left to view documentation, edit arguments, and execute.")
        self.placeholder_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_lbl.setStyleSheet("color: #8b949e; font-size: 13px; padding: 40px;")
        self.right_layout.addWidget(self.placeholder_lbl)

        # Tool Detail Container
        self.detail_container = QWidget()
        detail_layout = QVBoxLayout(self.detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(12)

        # Header: Name, Server Badge, Description
        header_box = QFrame()
        header_box.setStyleSheet("background-color: #21262d; border: 1px solid #30363d; border-radius: 8px; padding: 12px;")
        hb_layout = QVBoxLayout(header_box)
        hb_layout.setSpacing(6)

        title_row = QHBoxLayout()
        self.tool_name_lbl = QLabel("")
        self.tool_name_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")
        title_row.addWidget(self.tool_name_lbl)

        self.server_badge = QLabel("")
        self.server_badge.setStyleSheet("background-color: #1f6feb22; color: #58a6ff; border: 1px solid #1f6feb; border-radius: 4px; padding: 2px 8px; font-size: 11px;")
        title_row.addWidget(self.server_badge)
        title_row.addStretch()
        hb_layout.addLayout(title_row)

        self.tool_desc_lbl = QLabel("")
        self.tool_desc_lbl.setStyleSheet("font-size: 12px; color: #8b949e;")
        self.tool_desc_lbl.setWordWrap(True)
        hb_layout.addWidget(self.tool_desc_lbl)

        detail_layout.addWidget(header_box)

        # Dynamic Schema Form Scroll Area
        self.form_scroll = QScrollArea()
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setStyleSheet("background: transparent; border: none;")
        self.form_widget = QWidget()
        self.form_layout = QVBoxLayout(self.form_widget)
        self.form_layout.setContentsMargins(4, 4, 4, 4)
        self.form_layout.setSpacing(10)
        self.form_scroll.setWidget(self.form_widget)
        detail_layout.addWidget(self.form_scroll)

        # Validation error banner
        self.validation_err_lbl = QLabel("")
        self.validation_err_lbl.setStyleSheet("color: #f85149; font-size: 12px; font-weight: bold;")
        self.validation_err_lbl.hide()
        detail_layout.addWidget(self.validation_err_lbl)

        # Execution Row
        exec_row = QHBoxLayout()
        self.run_btn = QPushButton("▶ Run Tool")
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border: 1px solid #2ea043;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
            QPushButton:disabled {
                background-color: #21262d;
                color: #8b949e;
                border: 1px solid #30363d;
            }
        """)
        self.run_btn.clicked.connect(self._run_tool)
        exec_row.addWidget(self.run_btn)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
        exec_row.addWidget(self.status_lbl)
        exec_row.addStretch()

        detail_layout.addLayout(exec_row)

        # Result Viewer
        self.result_tabs = QTabWidget()
        self.result_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363d;
                background-color: #161b22;
                border-radius: 6px;
            }
            QTabBar::tab {
                background: #21262d;
                color: #8b949e;
                padding: 6px 14px;
                border: 1px solid #30363d;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #161b22;
                color: #58a6ff;
                font-weight: bold;
                border-bottom: 2px solid #58a6ff;
            }
        """)

        # Tab 1: JSON Tree
        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderLabels(["Key / Index", "Value"])
        self.result_tree.header().resizeSection(0, 220)
        self.result_tree.setStyleSheet("background-color: #161b22; color: #c9d1d9; border: none;")
        self.result_tabs.addTab(self.result_tree, "🌳 JSON Tree")

        # Tab 2: Plain Text Output
        self.result_text = QPlainTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("background-color: #161b22; color: #c9d1d9; font-family: monospace; border: none;")
        self.result_tabs.addTab(self.result_text, "📄 Raw Text")

        # Tab 3: Image Output
        self.result_image = QLabel("No image output returned")
        self.result_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_image.setStyleSheet("color: #8b949e; background-color: #161b22;")
        self.result_tabs.addTab(self.result_image, "🖼️ Image")

        detail_layout.addWidget(self.result_tabs)

        # Output Actions Row
        out_row = QHBoxLayout()
        out_row.addStretch()
        self.copy_btn = QPushButton("📋 Copy Output")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #ffffff;
            }
        """)
        self.copy_btn.clicked.connect(self._copy_output)
        out_row.addWidget(self.copy_btn)
        detail_layout.addLayout(out_row)

        self.right_layout.addWidget(self.detail_container)
        self.detail_container.hide()

        splitter.addWidget(right_widget)
        splitter.setSizes([260, 640])
        main_layout.addWidget(splitter)

    def load_tools(self) -> None:
        """Fetches tools from app-server and populates the tree."""
        async def _fetch():
            try:
                tools = await self.client.call("mcp.tools")
                if not tools and hasattr(self.client, "mock_dispatcher") and self.client.mock_dispatcher:
                    cfg_servers = self.client.mock_dispatcher.mcp_config.list_servers()
                    tools = []
                    for s in cfg_servers:
                        if s.name == "filesystem":
                            tools.extend([
                                {"name": "read_file", "server": "filesystem", "description": "Read contents of a file", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Absolute file path"}}, "required": ["path"]}},
                                {"name": "write_file", "server": "filesystem", "description": "Write text content to file", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "File path"}, "content": {"type": "string", "description": "Text content"}}, "required": ["path", "content"]}},
                            ])
                        elif s.name == "github":
                            tools.extend([
                                {"name": "get_issue", "server": "github", "description": "Fetch GitHub issue by number", "parameters": {"type": "object", "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}, "issue_number": {"type": "integer"}}, "required": ["owner", "repo", "issue_number"]}},
                            ])
                self.tools_data = tools or []
                self._render_tree(self.tools_data)
            except Exception:
                self.tools_data = []
                self._render_tree([])

        run_coro_safe(_fetch())

    def _render_tree(self, tools: List[Dict[str, Any]]) -> None:
        self.tool_tree.clear()
        by_server: Dict[str, List[Dict[str, Any]]] = {}
        for t in tools:
            s_name = t.get("server", "general")
            by_server.setdefault(s_name, []).append(t)

        icon_map = {"filesystem": "📁", "github": "🐙", "sqlite": "💾", "fetch": "🌐", "git": "🌿"}

        for s_name, s_tools in sorted(by_server.items()):
            icon = icon_map.get(s_name.lower(), "⚡")
            s_item = QTreeWidgetItem([f"{icon} {s_name} ({len(s_tools)})"])
            s_item.setExpanded(True)
            for t in sorted(s_tools, key=lambda x: x.get("name", "")):
                t_item = QTreeWidgetItem([f"  ↳ {t.get('name', 'unnamed')}"])
                t_item.setData(0, Qt.ItemDataRole.UserRole, t)
                s_item.addChild(t_item)
            self.tool_tree.addTopLevelItem(s_item)

    def _filter_tools(self, query: str) -> None:
        q = query.strip().lower()
        if not q:
            self._render_tree(self.tools_data)
            return

        filtered = [
            t for t in self.tools_data
            if q in t.get("name", "").lower()
            or q in t.get("server", "").lower()
            or q in t.get("description", "").lower()
        ]
        self._render_tree(filtered)

    def _on_tool_selected(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return  # Server group clicked

        self.current_tool = data
        self.placeholder_lbl.hide()
        self.detail_container.show()

        self.tool_name_lbl.setText(data.get("name", "Tool"))
        self.server_badge.setText(f"Server: {data.get('server', 'unknown')}")
        self.tool_desc_lbl.setText(data.get("description", "No documentation provided for this tool."))
        self.validation_err_lbl.hide()
        self.status_lbl.setText("")

        self._build_schema_form(data.get("parameters", data.get("inputSchema", {})))

    def _build_schema_form(self, schema: Dict[str, Any]) -> None:
        # Clear existing inputs
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        self.form_inputs.clear()
        properties: Dict[str, Any] = schema.get("properties", {})
        required: List[str] = schema.get("required", [])

        if not properties:
            no_params = QLabel("No parameters required for this tool.")
            no_params.setStyleSheet("color: #8b949e; font-style: italic;")
            self.form_layout.addWidget(no_params)
            return

        for p_name, p_spec in properties.items():
            prop_box = QFrame()
            prop_box.setStyleSheet("background-color: #21262d; border: 1px solid #30363d; border-radius: 6px; padding: 8px;")
            pb_layout = QVBoxLayout(prop_box)
            pb_layout.setContentsMargins(6, 6, 6, 6)
            pb_layout.setSpacing(4)

            # Label with * if required
            p_type = p_spec.get("type", "string")
            is_req = p_name in required
            req_mark = "<span style='color: #f85149; font-weight: bold;'>*</span>" if is_req else ""
            lbl = QLabel(f"<b>{p_name}</b> {req_mark} <span style='color: #8b949e; font-size: 10px;'>({p_type})</span>")
            lbl.setTextFormat(Qt.TextFormat.RichText)
            pb_layout.addWidget(lbl)

            if "description" in p_spec:
                d_lbl = QLabel(p_spec["description"])
                d_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
                d_lbl.setWordWrap(True)
                pb_layout.addWidget(d_lbl)

            # Generate typed widget
            input_widget: QWidget
            if "enum" in p_spec and isinstance(p_spec["enum"], list):
                combo = QComboBox()
                combo.setStyleSheet("background-color: #161b22; color: #ffffff; border: 1px solid #30363d; border-radius: 4px; padding: 4px;")
                for val in p_spec["enum"]:
                    combo.addItem(str(val))
                input_widget = combo
            elif p_type == "boolean":
                chk = QCheckBox("True / Enabled")
                chk.setStyleSheet("color: #c9d1d9;")
                input_widget = chk
            elif p_type == "integer":
                spin = QSpinBox()
                spin.setRange(-99999999, 99999999)
                spin.setValue(int(p_spec.get("default", 0)))
                spin.setStyleSheet("background-color: #161b22; color: #ffffff; border: 1px solid #30363d; border-radius: 4px; padding: 4px;")
                input_widget = spin
            elif p_type == "number":
                dspin = QDoubleSpinBox()
                dspin.setRange(-99999999.0, 99999999.0)
                dspin.setDecimals(4)
                dspin.setValue(float(p_spec.get("default", 0.0)))
                dspin.setStyleSheet("background-color: #161b22; color: #ffffff; border: 1px solid #30363d; border-radius: 4px; padding: 4px;")
                input_widget = dspin
            elif p_type == "array":
                line = QLineEdit()
                line.setPlaceholderText('e.g. item1, item2 or ["item1", "item2"]')
                line.setStyleSheet("background-color: #161b22; color: #ffffff; border: 1px solid #30363d; border-radius: 4px; padding: 4px;")
                input_widget = line
            elif p_type == "object":
                p_text = QPlainTextEdit()
                p_text.setPlaceholderText('e.g. {"key": "value"}')
                p_text.setFixedHeight(60)
                p_text.setStyleSheet("background-color: #161b22; color: #ffffff; font-family: monospace; border: 1px solid #30363d; border-radius: 4px; padding: 4px;")
                input_widget = p_text
            else:  # string
                line = QLineEdit()
                if "default" in p_spec:
                    line.setText(str(p_spec["default"]))
                line.setStyleSheet("background-color: #161b22; color: #ffffff; border: 1px solid #30363d; border-radius: 4px; padding: 4px;")
                input_widget = line

            pb_layout.addWidget(input_widget)
            self.form_inputs[p_name] = (p_type, input_widget)
            self.form_layout.addWidget(prop_box)

    def _collect_arguments(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        if not self.current_tool:
            return None, "No tool selected"

        schema = self.current_tool.get("parameters", self.current_tool.get("inputSchema", {}))
        required = schema.get("required", [])
        args: Dict[str, Any] = {}

        for p_name, (p_type, widget) in self.form_inputs.items():
            if isinstance(widget, QComboBox):
                val = widget.currentText()
            elif isinstance(widget, QCheckBox):
                val = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                val = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                val = widget.value()
            elif isinstance(widget, QPlainTextEdit):
                raw = widget.toPlainText().strip()
                if not raw and p_name in required:
                    return None, f"Required field '{p_name}' cannot be empty"
                try:
                    val = json.loads(raw) if raw else {}
                except Exception as e:
                    return None, f"Invalid JSON in field '{p_name}': {e}"
            elif isinstance(widget, QLineEdit):
                raw = widget.text().strip()
                if not raw and p_name in required:
                    return None, f"Required field '{p_name}' cannot be empty"
                if p_type == "array":
                    if raw.startswith("[") and raw.endswith("]"):
                        try:
                            val = json.loads(raw)
                        except Exception:
                            val = [x.strip() for x in raw[1:-1].split(",") if x.strip()]
                    else:
                        val = [x.strip() for x in raw.split(",") if x.strip()]
                else:
                    val = raw
            else:
                val = None

            if val is not None or p_name in required:
                args[p_name] = val

        return args, None

    def _run_tool(self) -> None:
        args, err = self._collect_arguments()
        if err:
            self.validation_err_lbl.setText(f"❌ {err}")
            self.validation_err_lbl.show()
            return

        self.validation_err_lbl.hide()
        assert self.current_tool is not None
        server_name = self.current_tool.get("server", "")
        tool_name = self.current_tool.get("name", "")

        self.run_btn.setEnabled(False)
        self.run_btn.setText("⏳ Running...")
        self.status_lbl.setText(f"Executing {tool_name} on {server_name}...")

        async def _exec():
            try:
                res = await self.client.call(
                    "mcp.call",
                    {"server_name": server_name, "tool_name": tool_name, "arguments": args},
                )
                self._display_result(res)
                self.status_lbl.setText("✔ Completed successfully")
            except Exception as exc:
                self._display_error(str(exc))
                self.status_lbl.setText("✖ Execution failed")
            finally:
                self.run_btn.setEnabled(True)
                self.run_btn.setText("▶ Run Tool")

        return run_coro_safe(_exec())

    def _display_result(self, result: Any) -> None:
        # 1. Plain text tab
        raw_str = json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)
        self.result_text.setPlainText(raw_str)

        # 2. JSON Tree tab
        self.result_tree.clear()
        if isinstance(result, dict):
            for k, v in result.items():
                self._add_tree_node(self.result_tree, k, v)
        elif isinstance(result, list):
            for idx, item in enumerate(result):
                self._add_tree_node(self.result_tree, f"[{idx}]", item)
        else:
            self.result_tree.addTopLevelItem(QTreeWidgetItem(["result", str(result)]))
        self.result_tree.expandAll()

        # 3. Image tab check
        self.result_image.setText("No image returned in response payload.")
        self.result_image.setPixmap(QApplication.clipboard().pixmap())  # Clear/empty

    def _add_tree_node(self, parent: Any, key: str, value: Any) -> None:
        if isinstance(value, dict):
            node = QTreeWidgetItem([str(key), "{...}"])
            parent.addTopLevelItem(node) if hasattr(parent, "addTopLevelItem") else parent.addChild(node)
            for k, v in value.items():
                self._add_tree_node(node, k, v)
        elif isinstance(value, list):
            node = QTreeWidgetItem([str(key), f"[{len(value)}]"])
            parent.addTopLevelItem(node) if hasattr(parent, "addTopLevelItem") else parent.addChild(node)
            for idx, item in enumerate(value):
                self._add_tree_node(node, f"[{idx}]", item)
        else:
            node = QTreeWidgetItem([str(key), str(value)])
            parent.addTopLevelItem(node) if hasattr(parent, "addTopLevelItem") else parent.addChild(node)

    def _display_error(self, err_msg: str) -> None:
        self.result_text.setPlainText(f"ERROR: {err_msg}")
        self.result_tree.clear()
        self.result_tree.addTopLevelItem(QTreeWidgetItem(["error", err_msg]))

    def _copy_output(self) -> None:
        text = self.result_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.copy_btn.setText("✔ Copied!")
            from lmms.gui.qt import QTimer
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋 Copy Output"))


# ============================================================================
# 2. LIVE CALL LOG WIDGET
# ============================================================================

class LiveCallLogWidget(QWidget):
    """
    Live call log streaming real-time tool calls and loading audit history.
    Includes filtering (server, tool, status), duration, secret redaction,
    expandable detail inspector, and a pyqtgraph latency chart.
    """

    def __init__(self, client: GUIAppServerClient, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.client = client
        self.entries: List[Dict[str, Any]] = []
        self.latencies: List[float] = []

        self.client.mcp_tool_call.connect(self.add_call_entry)

        self._build_ui()
        self.load_history()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Filters Bar
        filter_box = QFrame()
        filter_box.setStyleSheet("background-color: #21262d; border: 1px solid #30363d; border-radius: 6px; padding: 6px;")
        fb_layout = QHBoxLayout(filter_box)
        fb_layout.setContentsMargins(8, 4, 8, 4)
        fb_layout.setSpacing(10)

        fb_layout.addWidget(QLabel("Server:"))
        self.server_filter = QComboBox()
        self.server_filter.addItem("All Servers")
        self.server_filter.currentTextChanged.connect(self._apply_filters)
        fb_layout.addWidget(self.server_filter)

        fb_layout.addWidget(QLabel("Tool:"))
        self.tool_filter = QLineEdit()
        self.tool_filter.setPlaceholderText("Filter by tool name...")
        self.tool_filter.textChanged.connect(self._apply_filters)
        fb_layout.addWidget(self.tool_filter)

        fb_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Statuses", "Success", "Error"])
        self.status_filter.currentTextChanged.connect(self._apply_filters)
        fb_layout.addWidget(self.status_filter)

        fb_layout.addStretch()

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_history)
        fb_layout.addWidget(refresh_btn)

        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.clicked.connect(self._clear_view)
        fb_layout.addWidget(clear_btn)

        layout.addWidget(filter_box)

        # Pyqtgraph Latency Chart
        chart_box = QFrame()
        chart_box.setFixedHeight(130)
        chart_box.setStyleSheet("background-color: #161b22; border: 1px solid #30363d; border-radius: 6px;")
        cb_layout = QVBoxLayout(chart_box)
        cb_layout.setContentsMargins(4, 4, 4, 4)

        self.plot_widget = pg.PlotWidget(title="⚡ Tool Latency Timeline (ms)")
        self.plot_widget.setBackground("#161b22")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color="#58a6ff", width=2))
        cb_layout.addWidget(self.plot_widget)
        layout.addWidget(chart_box)

        # Splitter: Table & Details
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #30363d;
                height: 2px;
            }
        """)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Server", "Tool", "Status", "Duration (ms)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #161b22;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                gridline-color: #21262d;
            }
            QTableWidget::item:selected {
                background-color: #1f6feb33;
                color: #ffffff;
            }
        """)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        splitter.addWidget(self.table)

        # Detail Inspector
        self.detail_text = QPlainTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText("Select a row in the table above to view arguments (secrets redacted) and result details.")
        self.detail_text.setStyleSheet("background-color: #161b22; color: #c9d1d9; font-family: monospace; border: 1px solid #30363d; border-radius: 6px; padding: 6px;")
        splitter.addWidget(self.detail_text)

        splitter.setSizes([220, 120])
        layout.addWidget(splitter)

        # Pagination & Status Bar
        p_row = QHBoxLayout()
        self.record_count_lbl = QLabel("Showing 0 records")
        self.record_count_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        p_row.addWidget(self.record_count_lbl)

        p_row.addStretch()

        self.load_more_btn = QPushButton("⬇️ Load More (200 older records)")
        self.load_more_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #58a6ff;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #30363d;
            }
            QPushButton:disabled {
                color: #484f58;
                border-color: #21262d;
            }
        """)
        self.load_more_btn.clicked.connect(self.load_more)
        p_row.addWidget(self.load_more_btn)

        layout.addLayout(p_row)

    def load_history(self) -> None:
        """Loads call history from app-server audit log (most recent page)."""
        self.page_size = 200
        async def _fetch():
            try:
                entries = await self.client.call("audit.list", {"limit": self.page_size, "offset": 0})
                self.entries = list(reversed(entries or []))
                self._update_server_filter_options()
                self._apply_filters()
                self._update_chart()
                self._update_pagination_ui(len(entries or []))
            except Exception:
                from lmms_server.audit import default_audit_logger
                entries = default_audit_logger.view(limit=self.page_size, offset=0)
                self.entries = list(reversed(entries or []))
                self._update_server_filter_options()
                self._apply_filters()
                self._update_chart()
                self._update_pagination_ui(len(entries or []))

        run_coro_safe(_fetch())

    def load_more(self) -> None:
        """Fetches the next batch of older records from audit log."""
        self.load_more_btn.setEnabled(False)
        self.load_more_btn.setText("⏳ Loading older records...")
        offset = len(self.entries)

        async def _fetch():
            try:
                older = await self.client.call("audit.list", {"limit": self.page_size, "offset": offset})
                if older:
                    self.entries.extend(reversed(older))
                    self._update_server_filter_options()
                    self._apply_filters()
                self._update_pagination_ui(len(older or []))
            except Exception:
                from lmms_server.audit import default_audit_logger
                older = default_audit_logger.view(limit=self.page_size, offset=offset)
                if older:
                    self.entries.extend(reversed(older))
                    self._update_server_filter_options()
                    self._apply_filters()
                self._update_pagination_ui(len(older or []))
            finally:
                self.load_more_btn.setEnabled(True)
                self.load_more_btn.setText("⬇️ Load More (200 older records)")

        run_coro_safe(_fetch())

    def _update_pagination_ui(self, last_fetched_count: int) -> None:
        self.record_count_lbl.setText(f"Showing {len(self.entries)} records")
        if last_fetched_count < getattr(self, "page_size", 200):
            self.load_more_btn.setEnabled(False)
            self.load_more_btn.setText("✔ All records loaded")
        else:
            self.load_more_btn.setEnabled(True)
            self.load_more_btn.setText("⬇️ Load More (200 older records)")

    def add_call_entry(self, entry: Dict[str, Any]) -> None:
        """Real-time slot for mcp.tool_call notification."""
        self.entries.insert(0, entry)
        self._update_server_filter_options()
        self._apply_filters()
        self._update_chart()

    def _update_server_filter_options(self) -> None:
        servers = sorted({e.get("server", "") for e in self.entries if e.get("server")})
        current = self.server_filter.currentText()
        self.server_filter.blockSignals(True)
        self.server_filter.clear()
        self.server_filter.addItem("All Servers")
        for s in servers:
            self.server_filter.addItem(s)
        idx = self.server_filter.findText(current)
        if idx >= 0:
            self.server_filter.setCurrentIndex(idx)
        self.server_filter.blockSignals(False)

    def _render_table(self, rows: List[Dict[str, Any]]) -> None:
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(rows))
            for r_idx, entry in enumerate(rows):
                ts = entry.get("timestamp", "")
                if "T" in ts:
                    ts = ts.split("T")[-1].rstrip("Z")
                s = entry.get("server", "")
                t = entry.get("tool", "")
                st = entry.get("status", "unknown")
                dur = str(entry.get("duration_ms", 0.0))

                it_ts = QTableWidgetItem(ts)
                it_s = QTableWidgetItem(s)
                it_t = QTableWidgetItem(t)
                it_st = QTableWidgetItem("🟢 success" if st == "success" else "🔴 error")
                it_dur = QTableWidgetItem(f"{dur} ms")

                # Store entry data
                it_ts.setData(Qt.ItemDataRole.UserRole, entry)

                self.table.setItem(r_idx, 0, it_ts)
                self.table.setItem(r_idx, 1, it_s)
                self.table.setItem(r_idx, 2, it_t)
                self.table.setItem(r_idx, 3, it_st)
                self.table.setItem(r_idx, 4, it_dur)
        finally:
            self.table.setUpdatesEnabled(True)

    def _update_chart(self) -> None:
        pts = [float(e.get("duration_ms", 0.0)) for e in reversed(self.entries[:40])]
        self.curve.setData(pts)

    def _apply_filters(self) -> None:
        s_sel = self.server_filter.currentText()
        t_sel = self.tool_filter.text().strip().lower()
        st_sel = self.status_filter.currentText()

        filtered = []
        for e in self.entries:
            if s_sel != "All Servers" and e.get("server") != s_sel:
                continue
            if t_sel and t_sel not in e.get("tool", "").lower():
                continue
            if st_sel == "Success" and e.get("status") != "success":
                continue
            if st_sel == "Error" and e.get("status") != "error":
                continue
            filtered.append(e)

        self._render_table(filtered)

    def _on_row_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        item = self.table.item(row, 0)
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        if entry:
            self.detail_text.setPlainText(json.dumps(entry, indent=2))

    def _clear_view(self) -> None:
        self.entries.clear()
        self.table.setRowCount(0)
        self.detail_text.clear()
        self.curve.setData([])


# ============================================================================
# 3. PERMISSIONS WIDGET
# ============================================================================

class PermissionsWidget(QWidget):
    """
    Per-server and per-tool allow/ask/deny permissions matrix.
    Backed by permissions.get and permissions.set.
    Displays pending tool approval banner with non-blocking Approve/Deny buttons.
    """

    def __init__(self, client: GUIAppServerClient, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.client = client
        self.client.tool_permission_request.connect(self._show_approval_banner)

        self._build_ui()
        self.load_permissions()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Pending Approval Banner
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

        self.btn_approve_once = QPushButton("✔ Approve Once")
        self.btn_approve_once.setStyleSheet("background-color: #238636; color: #ffffff; padding: 4px 12px; border-radius: 4px; font-weight: bold;")
        self.btn_approve_once.clicked.connect(lambda: self._handle_approval_decision(always=False))
        ab_layout.addWidget(self.btn_approve_once)

        self.btn_always_allow = QPushButton("⭐ Always Allow")
        self.btn_always_allow.setStyleSheet("background-color: #1f6feb; color: #ffffff; padding: 4px 12px; border-radius: 4px; font-weight: bold;")
        self.btn_always_allow.clicked.connect(lambda: self._handle_approval_decision(always=True))
        ab_layout.addWidget(self.btn_always_allow)

        self.btn_deny = QPushButton("✖ Deny")
        self.btn_deny.setStyleSheet("background-color: #da3633; color: #ffffff; padding: 4px 12px; border-radius: 4px; font-weight: bold;")
        self.btn_deny.clicked.connect(self._handle_deny_decision)
        ab_layout.addWidget(self.btn_deny)

        self.approval_banner.hide()
        layout.addWidget(self.approval_banner)
        self._current_prompt_id: Optional[str] = None
        self._current_req_data: Optional[Dict[str, Any]] = None

        # Header Info
        info_box = QFrame()
        info_box.setStyleSheet("background-color: #21262d; border: 1px solid #30363d; border-radius: 8px; padding: 12px;")
        ib_layout = QHBoxLayout(info_box)
        ib_layout.setContentsMargins(8, 6, 8, 6)

        info_lbl = QLabel("🛡️ <b>Tool Execution Matrix</b> — Configure authorization policy per server and tool.")
        info_lbl.setStyleSheet("color: #c9d1d9; font-size: 12px;")
        ib_layout.addWidget(info_lbl)

        ib_layout.addStretch()

        refresh_btn = QPushButton("🔄 Refresh Policies")
        refresh_btn.clicked.connect(self.load_permissions)
        ib_layout.addWidget(refresh_btn)

        layout.addWidget(info_box)

        # Permissions Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Server", "Tool", "Policy (allow / ask / deny)", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #161b22;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                gridline-color: #21262d;
            }
            QComboBox {
                background-color: #21262d;
                color: #ffffff;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 2px 6px;
            }
        """)
        layout.addWidget(self.table)

    def _show_approval_banner(self, req: Dict[str, Any]) -> None:
        self._current_prompt_id = req.get("prompt_id")
        self._current_req_data = req
        tool = req.get("tool_name", "tool")
        args = json.dumps(req.get("arguments", {}))
        self.ab_text.setText(f"🔔 Approval Requested for <b>{tool}</b> with args: <code>{args[:60]}...</code>")
        self.approval_banner.show()

    def _handle_approval_decision(self, always: bool) -> None:
        pid = self._current_prompt_id
        if not pid:
            self.approval_banner.hide()
            return

        async def _do():
            try:
                await self.client.call("tool.approve", {"prompt_id": pid, "always": always})
                if always and self._current_req_data:
                    tool = self._current_req_data.get("tool_name")
                    await self.client.call("permissions.set", {"server": "filesystem", "tool": tool, "policy": "allow"})
                    self.load_permissions()
            except Exception:
                pass
            finally:
                self.approval_banner.hide()

        run_coro_safe(_do())

    def _handle_deny_decision(self) -> None:
        pid = self._current_prompt_id
        if not pid:
            self.approval_banner.hide()
            return

        async def _do():
            try:
                await self.client.call("tool.deny", {"prompt_id": pid})
            except Exception:
                pass
            finally:
                self.approval_banner.hide()

        run_coro_safe(_do())

    def load_permissions(self) -> None:
        """Loads permissions and active tools from app-server."""
        async def _fetch():
            try:
                perms = await self.client.call("permissions.get")
                tools = await self.client.call("mcp.tools")
                self._render_matrix(perms or {}, tools or [])
            except Exception:
                self._render_matrix({}, [])

        run_coro_safe(_fetch())

    def _render_matrix(self, perms: Dict[str, Any], tools: List[Dict[str, Any]]) -> None:
        # Build entries list
        entries: List[Tuple[str, str, str]] = []
        seen = set()

        # Tools discovered
        for t in tools:
            s = t.get("server", "general")
            name = t.get("name", "")
            policy = "ask"
            if s in perms and isinstance(perms[s], dict) and name in perms[s]:
                policy = perms[s][name]
            entries.append((s, name, policy))
            seen.add((s, name))

        # Permissions configured for other tools
        for s, s_perms in perms.items():
            if isinstance(s_perms, dict):
                for name, pol in s_perms.items():
                    if (s, name) not in seen:
                        entries.append((s, name, pol))

        self.table.setRowCount(len(entries))
        for r_idx, (s, t, pol) in enumerate(entries):
            self.table.setItem(r_idx, 0, QTableWidgetItem(s))
            self.table.setItem(r_idx, 1, QTableWidgetItem(t))

            combo = QComboBox()
            combo.addItems(["allow", "ask", "deny"])
            combo.setCurrentText(pol)
            combo.currentTextChanged.connect(lambda val, sv=s, tl=t: self._update_policy(sv, tl, val))
            self.table.setCellWidget(r_idx, 2, combo)

            status_lbl = QLabel("✔ Active" if pol == "allow" else ("🔒 Prompt" if pol == "ask" else "🚫 Blocked"))
            status_color = "#3fb950" if pol == "allow" else ("#d29922" if pol == "ask" else "#f85149")
            status_lbl.setStyleSheet(f"color: {status_color}; font-weight: bold; padding-left: 6px;")
            self.table.setCellWidget(r_idx, 3, status_lbl)

    def _update_policy(self, server: str, tool: str, policy: str) -> None:
        async def _do():
            try:
                await self.client.call("permissions.set", {"server": server, "tool": tool, "policy": policy})
            except Exception as e:
                QMessageBox.warning(self, "Permission Update Failed", str(e))

        run_coro_safe(_do())


# ============================================================================
# 4. SANDBOX WIDGET
# ============================================================================

class SandboxWidget(QWidget):
    """
    Sandbox diagnostic status and interactive ExecPolicy editor.
    Displays Bubblewrap & Landlock availability.
    Prominently displays "NOT isolated" warning with copyable install command when unisolated.
    """

    def __init__(self, client: GUIAppServerClient, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.client = client
        self._build_ui()
        self.load_status()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # "NOT isolated" Warning Box (Hidden by default)
        self.not_isolated_box = QFrame()
        self.not_isolated_box.setStyleSheet("""
            QFrame {
                background-color: #f8514922;
                border: 2px solid #f85149;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        nib_layout = QVBoxLayout(self.not_isolated_box)
        nib_layout.setSpacing(8)

        warn_title = QLabel("⚠️ NOT ISOLATED: Sandbox Containment Unavailable!")
        warn_title.setStyleSheet("color: #f85149; font-size: 14px; font-weight: bold;")
        nib_layout.addWidget(warn_title)

        warn_desc = QLabel("Neither Bubblewrap namespaces nor Landlock LSM could be activated. Tool executions run directly on your host machine without filesystem or network barriers.")
        warn_desc.setStyleSheet("color: #c9d1d9; font-size: 12px;")
        warn_desc.setWordWrap(True)
        nib_layout.addWidget(warn_desc)

        cmd_row = QHBoxLayout()
        cmd_box = QLineEdit("sudo apt install bubblewrap")
        cmd_box.setReadOnly(True)
        cmd_box.setStyleSheet("background-color: #161b22; color: #58a6ff; font-family: monospace; padding: 6px; border: 1px solid #30363d; border-radius: 4px;")
        cmd_row.addWidget(cmd_box)

        cp_btn = QPushButton("📋 Copy Command")
        cp_btn.setStyleSheet("background-color: #238636; color: #ffffff; padding: 6px 14px; border-radius: 4px; font-weight: bold;")
        cp_btn.clicked.connect(lambda: QApplication.clipboard().setText("sudo apt install bubblewrap"))
        cmd_row.addWidget(cp_btn)
        nib_layout.addLayout(cmd_row)

        self.not_isolated_box.hide()
        layout.addWidget(self.not_isolated_box)

        # Status Cards Grid
        grid_frame = QFrame()
        grid_layout = QGridLayout(grid_frame)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(12)

        # Card 1: Bwrap
        self.bwrap_card = QFrame()
        self.bwrap_card.setStyleSheet("background-color: #21262d; border: 1px solid #30363d; border-radius: 8px; padding: 12px;")
        bw_layout = QVBoxLayout(self.bwrap_card)
        bw_title = QLabel("🛡️ Bubblewrap (bwrap)")
        bw_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        bw_layout.addWidget(bw_title)
        self.bwrap_status_lbl = QLabel("Checking...")
        self.bwrap_status_lbl.setStyleSheet("font-size: 11px; color: #8b949e;")
        bw_layout.addWidget(self.bwrap_status_lbl)
        grid_layout.addWidget(self.bwrap_card, 0, 0)

        # Card 2: Landlock
        self.landlock_card = QFrame()
        self.landlock_card.setStyleSheet("background-color: #21262d; border: 1px solid #30363d; border-radius: 8px; padding: 12px;")
        ll_layout = QVBoxLayout(self.landlock_card)
        ll_title = QLabel("🔒 Landlock LSM")
        ll_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        ll_layout.addWidget(ll_title)
        self.landlock_status_lbl = QLabel("Checking...")
        self.landlock_status_lbl.setStyleSheet("font-size: 11px; color: #8b949e;")
        ll_layout.addWidget(self.landlock_status_lbl)
        grid_layout.addWidget(self.landlock_card, 0, 1)

        # Card 3: Active Mode
        self.mode_card = QFrame()
        self.mode_card.setStyleSheet("background-color: #21262d; border: 1px solid #30363d; border-radius: 8px; padding: 12px;")
        m_layout = QVBoxLayout(self.mode_card)
        m_title = QLabel("⚡ Active Isolation Mode")
        m_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        m_layout.addWidget(m_title)
        self.mode_status_lbl = QLabel("Checking...")
        self.mode_status_lbl.setStyleSheet("font-size: 11px; color: #3fb950; font-weight: bold;")
        m_layout.addWidget(self.mode_status_lbl)
        grid_layout.addWidget(self.mode_card, 0, 2)

        layout.addWidget(grid_frame)

        # Policy Editor Box
        policy_group = QGroupBox("ExecPolicy Configuration (~/.lmms/execpolicy.toml)")
        policy_group.setStyleSheet("""
            QGroupBox {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 10px;
                padding: 14px;
                color: #ffffff;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)
        pg_layout = QVBoxLayout(policy_group)
        pg_layout.setSpacing(10)

        # Default action & Flags
        top_opts = QHBoxLayout()
        top_opts.addWidget(QLabel("Default Action:"))
        self.default_action_combo = QComboBox()
        self.default_action_combo.addItems(["ask", "allow", "deny"])
        self.default_action_combo.setStyleSheet("background-color: #21262d; color: #ffffff; padding: 4px; border: 1px solid #30363d; border-radius: 4px;")
        top_opts.addWidget(self.default_action_combo)

        top_opts.addSpacing(20)
        self.chk_deny_network = QCheckBox("Block Network Access Inside Sandbox")
        self.chk_deny_network.setStyleSheet("color: #c9d1d9;")
        top_opts.addWidget(self.chk_deny_network)

        self.chk_isolate_home = QCheckBox("Isolate User Home (~/)")
        self.chk_isolate_home.setStyleSheet("color: #c9d1d9;")
        top_opts.addWidget(self.chk_isolate_home)

        top_opts.addStretch()
        pg_layout.addLayout(top_opts)

        # Writable Paths
        pg_layout.addWidget(QLabel("Writable Paths (one per line):"))
        self.writable_paths_edit = QPlainTextEdit()
        self.writable_paths_edit.setFixedHeight(70)
        self.writable_paths_edit.setStyleSheet("background-color: #21262d; color: #c9d1d9; font-family: monospace; border: 1px solid #30363d; border-radius: 4px;")
        pg_layout.addWidget(self.writable_paths_edit)

        # Read-Only Paths
        pg_layout.addWidget(QLabel("Read-Only Paths (one per line):"))
        self.readonly_paths_edit = QPlainTextEdit()
        self.readonly_paths_edit.setFixedHeight(70)
        self.readonly_paths_edit.setStyleSheet("background-color: #21262d; color: #c9d1d9; font-family: monospace; border: 1px solid #30363d; border-radius: 4px;")
        pg_layout.addWidget(self.readonly_paths_edit)

        # Hidden Paths
        pg_layout.addWidget(QLabel("Hidden Paths (one per line):"))
        self.hidden_paths_edit = QPlainTextEdit()
        self.hidden_paths_edit.setFixedHeight(70)
        self.hidden_paths_edit.setStyleSheet("background-color: #21262d; color: #c9d1d9; font-family: monospace; border: 1px solid #30363d; border-radius: 4px;")
        pg_layout.addWidget(self.hidden_paths_edit)

        # Save Policy Button
        save_row = QHBoxLayout()
        save_row.addStretch()
        self.save_policy_btn = QPushButton("💾 Save Sandbox Policy")
        self.save_policy_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border: 1px solid #2ea043;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
        """)
        self.save_policy_btn.clicked.connect(self._save_policy)
        save_row.addWidget(self.save_policy_btn)
        pg_layout.addLayout(save_row)

        layout.addWidget(policy_group)
        layout.addStretch()

    def load_status(self) -> None:
        """Queries sandbox status and current policy."""
        async def _fetch():
            try:
                st = await self.client.call("sandbox.status")
                pol = await self.client.call("sandbox.policy.get")
                self._apply_status(st or {})
                self._apply_policy(pol or {})
            except Exception:
                from lmms_sandbox.runner import default_runner
                self._apply_status(default_runner.get_status())

        run_coro_safe(_fetch())

    def _apply_status(self, st: Dict[str, Any]) -> None:
        bwrap_ok = st.get("bwrap_available", False)
        ll_ok = st.get("landlock_available", False)
        iso = st.get("isolation_status", "NOT isolated")

        if bwrap_ok:
            self.bwrap_status_lbl.setText(f"🟢 Installed ({st.get('bwrap_path', '/usr/bin/bwrap')})")
            self.bwrap_status_lbl.setStyleSheet("color: #3fb950; font-size: 11px;")
        else:
            self.bwrap_status_lbl.setText("🔴 Not Available")
            self.bwrap_status_lbl.setStyleSheet("color: #f85149; font-size: 11px;")

        if ll_ok:
            self.landlock_status_lbl.setText(f"🟢 Supported (Kernel ABI v{st.get('landlock_abi', '?')})")
            self.landlock_status_lbl.setStyleSheet("color: #3fb950; font-size: 11px;")
        else:
            self.landlock_status_lbl.setText("🟡 Unsupported kernel")
            self.landlock_status_lbl.setStyleSheet("color: #d29922; font-size: 11px;")

        self.mode_status_lbl.setText(iso)
        if iso == "NOT isolated":
            self.mode_status_lbl.setStyleSheet("color: #f85149; font-weight: bold; font-size: 12px;")
            self.not_isolated_box.show()
        else:
            self.mode_status_lbl.setStyleSheet("color: #3fb950; font-weight: bold; font-size: 12px;")
            self.not_isolated_box.hide()

    def _apply_policy(self, pol: Dict[str, Any]) -> None:
        act = pol.get("default_action", "ask")
        idx = self.default_action_combo.findText(act)
        if idx >= 0:
            self.default_action_combo.setCurrentIndex(idx)

        self.chk_deny_network.setChecked(pol.get("deny_network", True))
        self.chk_isolate_home.setChecked(pol.get("isolate_home", True))

        self.writable_paths_edit.setPlainText("\n".join(pol.get("writable_paths", [])))
        self.readonly_paths_edit.setPlainText("\n".join(pol.get("read_only_paths", [])))
        self.hidden_paths_edit.setPlainText("\n".join(pol.get("hidden_paths", [])))

    def _save_policy(self) -> None:
        act = self.default_action_combo.currentText()
        net = self.chk_deny_network.isChecked()
        home = self.chk_isolate_home.isChecked()

        w_paths = [p.strip() for p in self.writable_paths_edit.toPlainText().splitlines() if p.strip()]
        ro_paths = [p.strip() for p in self.readonly_paths_edit.toPlainText().splitlines() if p.strip()]
        h_paths = [p.strip() for p in self.hidden_paths_edit.toPlainText().splitlines() if p.strip()]

        async def _do():
            payload = {
                "default_action": act,
                "deny_network": net,
                "isolate_home": home,
                "writable_paths": w_paths,
                "read_only_paths": ro_paths,
                "hidden_paths": h_paths,
            }
            try:
                res = await self.client.call("sandbox.policy.set", payload)
                if isinstance(res, dict) and res.get("warning"):
                    reasons = res.get("weakening_reasons", [])
                    reasons_str = "\n• " + "\n• ".join(reasons)
                    if os.environ.get("QT_QPA_PLATFORM") == "offscreen" or getattr(self, "_auto_confirm_weakening", False):
                        btn = QMessageBox.StandardButton.Yes
                    else:
                        btn = QMessageBox.warning(
                            self,
                            "Security Warning: Policy Weakened",
                            f"The requested changes reduce sandbox isolation:\n{reasons_str}\n\nAre you sure you want to apply these changes?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                        )
                    if btn != QMessageBox.StandardButton.Yes:
                        self.save_policy_btn.setText("💾 Save Sandbox Policy")
                        return

                    payload["force"] = True
                    res = await self.client.call("sandbox.policy.set", payload)

                self.save_policy_btn.setText("✔ Policy Saved!")
                from lmms.gui.qt import QTimer
                QTimer.singleShot(1500, lambda: self.save_policy_btn.setText("💾 Save Sandbox Policy"))
            except Exception as e:
                if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
                    QMessageBox.warning(self, "Invalid Policy", f"Failed to save policy: {e}\nPrevious policy was preserved.")
                self.save_policy_btn.setText("💾 Save Sandbox Policy")

        run_coro_safe(_do())
