"""
lmms.gui.widgets.automation_drawer - n8n-style Trigger & Node Selection Drawer.
Provides a collapsible right-hand drawer with instant search filtering,
trigger templates, action nodes, and one-click insertion onto the canvas.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any

from lmms.gui.qt import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QFrame,
    Qt,
    QColor,
    QCursor,
    pyqtSignal,
)
from lmms.gui.branding import AutomationBranding


# Definition of trigger and node catalog
TRIGGER_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "lmms.triggers.ManualTriggerNode",
        "title": "Trigger manually",
        "description": "Runs the flow on clicking a button in LMMs. Good for getting started quickly",
        "category": "trigger",
        "icon": "🔘",
        "arrow": False,
    },
    {
        "id": "lmms.triggers.ChatMessageTriggerNode",
        "title": "On chat message",
        "description": "Runs the flow when a user sends a chat message. For use with AI nodes",
        "category": "trigger",
        "icon": "💬",
        "arrow": False,
    },
    {
        "id": "lmms.triggers.ScheduleTriggerNode",
        "title": "On a schedule",
        "description": "Runs the flow every day, hour, or custom cron interval",
        "category": "trigger",
        "icon": "⏱",
        "arrow": False,
    },
    {
        "id": "lmms.triggers.WebhookTriggerNode",
        "title": "On webhook call",
        "description": "Runs the flow on receiving an incoming HTTP webhook request",
        "category": "trigger",
        "icon": "🪝",
        "arrow": False,
    },
    {
        "id": "lmms.triggers.FileWatchTriggerNode",
        "title": "On file changes",
        "description": "Runs the flow when workspace files are created, modified, or deleted",
        "category": "trigger",
        "icon": "📁",
        "arrow": False,
    },
    {
        "id": "lmms.triggers.AppEventTriggerNode",
        "title": "On app event",
        "description": "Runs the flow when something happens in an app like Telegram, Git, or Engine",
        "category": "trigger",
        "icon": "📡",
        "arrow": True,
    },
    {
        "id": "lmms.triggers.FormTriggerNode",
        "title": "On form submission",
        "description": "Generate dynamic input forms in LMMs and pass responses to the workflow",
        "category": "trigger",
        "icon": "📋",
        "arrow": False,
    },
    {
        "id": "lmms.triggers.SubflowTriggerNode",
        "title": "When executed by another workflow",
        "description": "Runs the flow when called by Execute Workflow from a parent flow",
        "category": "trigger",
        "icon": "↳",
        "arrow": False,
    },
    {
        "id": "lmms.triggers.EvaluationTriggerNode",
        "title": "When running evaluation",
        "description": "Run a test dataset through your workflow to benchmark performance",
        "category": "trigger",
        "icon": "✓",
        "arrow": False,
    },
    # AI & Core Action Nodes
    {
        "id": "lmms.models.AIAgentNode",
        "title": "AI Agent",
        "description": "Autonomous reasoning agent connected to Chat Models, Memory, and Tools",
        "category": "model",
        "icon": "🤖",
        "arrow": False,
    },
    {
        "id": "lmms.models.ChatModelNode",
        "title": "Chat Model",
        "description": "Direct LLM inference with Ollama, vLLM, OpenAI, Anthropic, or DeepSeek",
        "category": "model",
        "icon": "🧠",
        "arrow": False,
    },
    {
        "id": "lmms.actions.MCPToolNode",
        "title": "MCP Tool Call",
        "description": "Execute Model Context Protocol tools from configured local or remote servers",
        "category": "action",
        "icon": "🛠",
        "arrow": False,
    },
    {
        "id": "lmms.actions.PythonCodeNode",
        "title": "Python Code",
        "description": "Execute sandboxed Python script with item input, output, and JSON transform",
        "category": "action",
        "icon": "🐍",
        "arrow": False,
    },
    {
        "id": "lmms.actions.HTTPRequestNode",
        "title": "HTTP Request",
        "description": "Send GET, POST, PUT, DELETE web API requests with headers and body",
        "category": "action",
        "icon": "🌐",
        "arrow": False,
    },
    {
        "id": "lmms.actions.SandboxedCommandNode",
        "title": "Sandboxed Command",
        "description": "Execute terminal commands with Bubblewrap / Landlock kernel isolation",
        "category": "action",
        "icon": "💻",
        "arrow": False,
    },
    {
        "id": "lmms.actions.ValidationGateNode",
        "title": "Validation & Test Gate",
        "description": "Run Python AST syntax checks and test suite validation before proceeding",
        "category": "action",
        "icon": "🛡",
        "arrow": False,
    },
    {
        "id": "lmms.actions.FilePatchNode",
        "title": "File & Patch Op",
        "description": "Safely read, write, or apply unified patches within workspace boundaries",
        "category": "action",
        "icon": "📝",
        "arrow": False,
    },
    {
        "id": "lmms.logic.ApprovalGateNode",
        "title": "Approval Gate",
        "description": "Human-in-the-loop review barrier. Pauses execution until approved in CLI or UI",
        "category": "logic",
        "icon": "🛑",
        "arrow": False,
    },
    {
        "id": "lmms.logic.IfElseNode",
        "title": "If / Else Condition",
        "description": "Route execution flow along true or false branch based on expression evaluation",
        "category": "logic",
        "icon": "⑂",
        "arrow": False,
    },
]


class TriggerCardItem(QFrame):
    """Clickable n8n-style card item inside the drawer."""
    clicked = pyqtSignal(dict)

    def __init__(self, item_data: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.item_data = item_data
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border-radius: 8px;
                padding: 4px;
            }
            QFrame:hover {
                background-color: #23242c;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Left Icon with Category Accent
        cat = self.item_data.get("category", "custom")
        cat_color = AutomationBranding.get_category_color(cat)

        icon_lbl = QLabel(self.item_data.get("icon", "⚡"))
        icon_lbl.setStyleSheet(f"""
            font-size: 16px;
            color: {cat_color};
            background: transparent;
        """)
        icon_lbl.setFixedWidth(24)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Center Text Box
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title_lbl = QLabel(self.item_data.get("title", ""))
        title_lbl.setStyleSheet("color: #f4f4f5; font-size: 13px; font-weight: 600; background: transparent;")

        desc_lbl = QLabel(self.item_data.get("description", ""))
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #9ca3af; font-size: 11px; line-height: 1.3; background: transparent;")

        text_layout.addWidget(title_lbl)
        text_layout.addWidget(desc_lbl)

        layout.addWidget(icon_lbl)
        layout.addLayout(text_layout)

        # Optional Right Arrow
        if self.item_data.get("arrow", False):
            arrow_lbl = QLabel("→")
            arrow_lbl.setStyleSheet("color: #71717a; font-size: 14px; background: transparent;")
            layout.addWidget(arrow_lbl)

    def mousePressEvent(self, event):
        self.clicked.emit(self.item_data)
        event.accept()


class AutomationDrawer(QWidget):
    """
    Right-side drawer panel: 'What triggers this workflow?'
    Features quick search, category filtering, and one-click node placement.
    """
    node_selected = pyqtSignal(dict)
    closed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("AutomationDrawer")
        self.setFixedWidth(360)
        self.setStyleSheet("""
            QWidget#AutomationDrawer {
                background-color: #16171d;
                border-left: 1px solid #282a35;
            }
        """)

        self.cards: List[TriggerCardItem] = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 14)
        main_layout.setSpacing(12)

        # Header with Title and Close Button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(3)

        self.lbl_title = QLabel("What triggers this workflow?")
        self.lbl_title.setStyleSheet("color: #f4f4f5; font-size: 15px; font-weight: 700;")

        self.lbl_subtitle = QLabel("A trigger is a step that starts your workflow")
        self.lbl_subtitle.setStyleSheet("color: #9ca3af; font-size: 12px;")

        title_vbox.addWidget(self.lbl_title)
        title_vbox.addWidget(self.lbl_subtitle)

        self.btn_close = QPushButton("✕")
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.setToolTip("Close drawer")
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #71717a;
                font-size: 14px;
                border: none;
                width: 24px;
                height: 24px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #272832;
                color: #ffffff;
            }
        """)
        self.btn_close.clicked.connect(self.closed)

        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_close)
        main_layout.addLayout(header_layout)

        # Search Bar
        search_box = QFrame()
        search_box.setStyleSheet("""
            QFrame {
                background-color: #1f2029;
                border: 1px solid #323544;
                border-radius: 8px;
            }
            QFrame:focus-within {
                border: 1px solid #8b5cf6;
            }
        """)
        search_layout = QHBoxLayout(search_box)
        search_layout.setContentsMargins(10, 4, 10, 4)
        search_layout.setSpacing(8)

        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("color: #71717a; font-size: 12px; border: none; background: transparent;")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search nodes...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #f4f4f5;
                font-size: 12px;
                selection-background-color: #8b5cf6;
            }
        """)
        self.search_input.textChanged.connect(self.filter_nodes)

        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input)
        main_layout.addWidget(search_box)

        # Category Filter Tabs
        cat_layout = QHBoxLayout()
        cat_layout.setContentsMargins(0, 4, 0, 4)
        cat_layout.setSpacing(6)

        self.filter_btns: Dict[str, QPushButton] = {}
        for cat_name, cat_id in (("All", "all"), ("Triggers", "trigger"), ("AI / Models", "model"), ("Actions", "action"), ("Logic", "logic")):
            btn = QPushButton(cat_name)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setCheckable(True)
            if cat_id == "all":
                btn.setChecked(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #20212a;
                    color: #9ca3af;
                    border: 1px solid #2d303e;
                    border-radius: 12px;
                    padding: 3px 10px;
                    font-size: 11px;
                }
                QPushButton:checked {
                    background-color: #8b5cf6;
                    color: #ffffff;
                    border-color: #8b5cf6;
                    font-weight: 600;
                }
                QPushButton:hover:!checked {
                    background-color: #2b2d39;
                    color: #f4f4f5;
                }
            """)
            btn.clicked.connect(lambda checked, c=cat_id: self._on_category_clicked(c))
            self.filter_btns[cat_id] = btn
            cat_layout.addWidget(btn)

        cat_layout.addStretch()
        main_layout.addLayout(cat_layout)

        # Scrollable Cards List
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #373948;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(4)

        for item in TRIGGER_CATALOG:
            card = TriggerCardItem(item)
            card.clicked.connect(self._on_card_clicked)
            self.cards.append(card)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()
        scroll.setWidget(self.cards_container)
        main_layout.addWidget(scroll)

    def _on_category_clicked(self, selected_cat: str):
        for cid, btn in self.filter_btns.items():
            btn.setChecked(cid == selected_cat)
        self.filter_nodes(self.search_input.text())

    def _on_card_clicked(self, item_data: dict):
        self.node_selected.emit(item_data)

    def filter_nodes(self, query: str):
        query = (query or "").strip().lower()
        active_cat = "all"
        for cid, btn in self.filter_btns.items():
            if btn.isChecked():
                active_cat = cid
                break

        for card in self.cards:
            data = card.item_data
            matches_cat = (active_cat == "all") or (data.get("category") == active_cat)
            matches_text = True
            if query:
                title = data.get("title", "").lower()
                desc = data.get("description", "").lower()
                matches_text = query in title or query in desc

            card.setVisible(matches_cat and matches_text)

    def focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()
