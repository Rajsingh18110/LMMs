# Copyright 2026 LMMs Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
LMMs Online Model & Custom Webhook Hub Dialog (PyQt6).
World-class desktop interface to discover, configure, test, and manage online LLM
providers (Anthropic, OpenAI, Gemini, Sarvam AI, Krutrim, DeepSeek, Groq, and Custom Webhooks).
"""

from __future__ import annotations

import sys
import json
import re
import time
from typing import Dict, Any, Optional, List

from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QBrush, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from lmms.backend.core.registry.online_models import OnlineModelRegistry
from lmms.backend.core.registry.provider_presets import PROVIDER_PRESETS
from lmms.backend.providers.online_client import OnlineModelClient


# ==============================================================================
# WORLD-CLASS DESIGN SYSTEM: Dark Obsidian & Cyberpunk Slate Tokens
# ==============================================================================
STYLESHEET = """
/* Global Dialog Canvas */
QDialog {
    background-color: #0b0c10;
    color: #f8fafc;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* ScrollBars */
QScrollBar:vertical {
    background: #0f1117;
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}
QScrollBar::thumb:vertical {
    background: #25283a;
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::thumb:vertical:hover {
    background: #3b4261;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Sidebar Shell */
QFrame#sidebarFrame {
    background-color: #10121a;
    border-right: 1px solid #1e2233;
    border-radius: 8px;
}

/* Elevated Card Surfaces */
QFrame#cardFrame {
    background-color: #131520;
    border: 1px solid #202436;
    border-radius: 8px;
}

/* Inner Banner Surfaces */
QFrame#bannerFrame {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #171a2b, stop:1 #121422);
    border: 1px solid #242940;
    border-radius: 8px;
}

/* Metric Stats Cards */
QFrame#statCard {
    background-color: #11131c;
    border: 1px solid #1d2133;
    border-radius: 6px;
    padding: 6px 12px;
}

/* Inputs, Combos & TextEdits */
QLineEdit, QComboBox, QTextEdit {
    background-color: #161825;
    border: 1px solid #282d42;
    border-radius: 6px;
    padding: 7px 12px;
    color: #f8fafc;
    font-size: 13px;
    selection-background-color: #0284c7;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #38bdf8;
    background-color: #1a1d2c;
}
QLineEdit:read-only {
    background-color: #111219;
    color: #94a3b8;
}
QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}
QComboBox QAbstractItemView {
    background-color: #161825;
    color: #f8fafc;
    border: 1px solid #282d42;
    selection-background-color: #0284c7;
    outline: none;
}

/* Checkbox */
QCheckBox {
    color: #cbd5e1;
    font-size: 12px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #38415c;
    background: #161825;
}
QCheckBox::indicator:checked {
    background-color: #0284c7;
    border-color: #38bdf8;
}

/* Buttons System */
QPushButton {
    border-radius: 6px;
    font-weight: 600;
    font-size: 12px;
    padding: 7px 14px;
    outline: none;
}
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #0ea5e9);
    color: #ffffff;
    border: 1px solid #38bdf8;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #0284c7);
}
QPushButton#primaryBtn:pressed {
    background-color: #075985;
}
QPushButton#secondaryBtn {
    background-color: #1b1e2c;
    color: #e2e8f0;
    border: 1px solid #2a3045;
}
QPushButton#secondaryBtn:hover {
    background-color: #23273a;
    border-color: #3b4360;
}
QPushButton#accentActionBtn {
    background-color: #12304d;
    color: #38bdf8;
    border: 1px solid #0284c7;
}
QPushButton#accentActionBtn:hover {
    background-color: #163d63;
}
QPushButton#dangerBtn {
    background-color: #2b1417;
    color: #fca5a5;
    border: 1px solid #4f1c21;
}
QPushButton#dangerBtn:hover {
    background-color: #40191e;
    border-color: #7a232b;
}
QPushButton#pillBtn {
    background-color: #161926;
    color: #94a3b8;
    border: 1px solid #262b40;
    border-radius: 11px;
    padding: 3px 9px;
    font-size: 11px;
}
QPushButton#pillBtn:hover {
    background-color: #1e2235;
    color: #38bdf8;
    border-color: #38bdf8;
}
QPushButton#pillBtnActive {
    background-color: #14324f;
    color: #38bdf8;
    border: 1px solid #0284c7;
    border-radius: 11px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: 600;
}

/* Provider List Widget */
QListWidget#providerList {
    background-color: transparent;
    border: none;
    color: #cbd5e1;
    font-size: 13px;
    outline: none;
}
QListWidget#providerList::item {
    padding: 7px 10px;
    border-radius: 5px;
    margin-bottom: 2px;
}
QListWidget#providerList::item:hover {
    background-color: #181b28;
    color: #f8fafc;
}
QListWidget#providerList::item:selected {
    background-color: #1c2032;
    color: #38bdf8;
    font-weight: 600;
    border-left: 3px solid #38bdf8;
}

/* Models & Headers Tables */
QTableWidget {
    background-color: #10111a;
    border: 1px solid #1e2133;
    border-radius: 6px;
    gridline-color: #191b29;
    color: #f1f5f9;
    font-size: 12px;
    selection-background-color: #1b2033;
}
QHeaderView::section {
    background-color: #141622;
    color: #94a3b8;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 7px 10px;
    border: none;
    border-bottom: 1px solid #1e2133;
}
"""


class TestWorker(QThread):
    """Background thread to perform non-blocking connection tests."""
    finished = pyqtSignal(dict)

    def __init__(self, p_type: str, base_url: str, api_key: str, model_id: str, custom_headers: dict):
        super().__init__()
        self.p_type = p_type
        self.base_url = base_url
        self.api_key = api_key
        self.model_id = model_id
        self.custom_headers = custom_headers

    def run(self):
        start_time = time.time()
        res = OnlineModelClient.test_connection(
            p_type=self.p_type,
            base_url=self.base_url,
            api_key=self.api_key,
            model_id=self.model_id,
            custom_headers=self.custom_headers
        )
        latency_ms = int((time.time() - start_time) * 1000)
        res["latency_ms"] = latency_ms
        self.finished.emit(res)


class ModelManagerDialog(QDialog):
    """World-Class Native Desktop Dialog for Managing Online LLMs and Webhooks."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("LMMs · AI Models & Custom Webhook Hub")
        self.resize(1180, 800)
        self.setMinimumSize(940, 640)
        self.setStyleSheet(STYLESHEET)

        self._active_preset_key = "sarvam"
        self._test_thread: Optional[TestWorker] = None
        self._current_provider_badge = "🇮🇳 Indian Sovereign AI"
        self._preset_buttons: List[QPushButton] = []

        self._init_ui()
        self._load_registered_models()
        self._select_provider("sarvam")

    # ==========================================================================
    # UI CONSTRUCTION
    # ==========================================================================
    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 14, 16, 14)
        root_layout.setSpacing(12)

        # ----------------------------------------------------------------------
        # 1. TOP APPLICATION HEADER
        # ----------------------------------------------------------------------
        header_bar = QHBoxLayout()
        header_bar.setSpacing(12)

        # Brand icon badge
        icon_badge = QLabel("🧠")
        icon_badge.setStyleSheet(
            "background-color: #172554; border: 1px solid #1d4ed8; border-radius: 8px; "
            "font-size: 19px; padding: 5px 9px;"
        )
        header_bar.addWidget(icon_badge)

        # Title & Subtitle block
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_label = QLabel("<span style='font-size: 16px; font-weight: 700; color: #f8fafc;'>AI Models & Custom Webhook Hub</span>")
        sub_label = QLabel(
            "<span style='font-size: 12px; color: #94a3b8;'>"
            "Configure sovereign Indian AI, global flagships, and custom webhooks with complete tool & agent parity."
            "</span>"
        )
        title_box.addWidget(title_label)
        title_box.addWidget(sub_label)
        header_bar.addLayout(title_box)

        header_bar.addStretch()

        # Active status pill
        self.lbl_header_active = QLabel("● Active: Offline Engine")
        self.lbl_header_active.setStyleSheet(
            "background-color: #152238; border: 1px solid #1e3a8a; border-radius: 14px; "
            "color: #38bdf8; font-size: 11px; font-weight: 600; padding: 5px 12px;"
        )
        header_bar.addWidget(self.lbl_header_active)

        # Close button
        btn_close = QPushButton("✕ Close")
        btn_close.setObjectName("secondaryBtn")
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.clicked.connect(self.close)
        header_bar.addWidget(btn_close)

        root_layout.addLayout(header_bar)

        # ----------------------------------------------------------------------
        # 2. TOP SPLITTER: Left Provider Explorer & Right Configuration Workspace
        # ----------------------------------------------------------------------
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.setHandleWidth(4)

        # ======================================================================
        # LEFT: PROVIDER EXPLORER
        # ======================================================================
        sidebar_frame = QFrame()
        sidebar_frame.setObjectName("sidebarFrame")
        side_layout = QVBoxLayout(sidebar_frame)
        side_layout.setContentsMargins(10, 10, 10, 10)
        side_layout.setSpacing(8)

        # Search bar container
        search_box = QHBoxLayout()
        search_box.setSpacing(6)
        self.provider_search = QLineEdit()
        self.provider_search.setPlaceholderText("🔍 Search providers, models...")
        self.provider_search.textChanged.connect(self._filter_providers)
        search_box.addWidget(self.provider_search)

        self.btn_clear_search = QPushButton("✕")
        self.btn_clear_search.setObjectName("secondaryBtn")
        self.btn_clear_search.setFixedSize(28, 28)
        self.btn_clear_search.setToolTip("Clear search")
        self.btn_clear_search.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold; padding: 0;")
        self.btn_clear_search.clicked.connect(lambda: self.provider_search.setText(""))
        self.btn_clear_search.setVisible(False)
        search_box.addWidget(self.btn_clear_search)
        side_layout.addLayout(search_box)

        # Provider list
        self.provider_list = QListWidget()
        self.provider_list.setObjectName("providerList")
        self.provider_list.currentItemChanged.connect(self._on_provider_item_changed)
        side_layout.addWidget(self.provider_list)

        self._populate_provider_list()
        top_splitter.addWidget(sidebar_frame)

        # ======================================================================
        # RIGHT: CONFIGURATION WORKSPACE
        # ======================================================================
        right_frame = QFrame()
        right_frame.setObjectName("cardFrame")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(10)

        # --- A. Provider Identity Banner ---
        banner = QFrame()
        banner.setObjectName("bannerFrame")
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(14, 9, 14, 9)

        banner_text = QVBoxLayout()
        banner_text.setSpacing(3)
        self.prov_title = QLabel("<h3>Sarvam AI (India 🇮🇳)</h3>")
        self.prov_title.setStyleSheet("color: #f8fafc; margin: 0;")
        self.prov_desc = QLabel("Foundational Indian language AI models built by Sarvam AI.")
        self.prov_desc.setStyleSheet("color: #94a3b8; font-size: 12px; margin: 0;")
        banner_text.addWidget(self.prov_title)
        banner_text.addWidget(self.prov_desc)
        banner_layout.addLayout(banner_text)

        banner_layout.addStretch()

        self.prov_tag = QLabel("🇮🇳 Indian Sovereign AI")
        self.prov_tag.setStyleSheet(
            "background-color: #2a1f10; border: 1px solid #78350f; color: #fbbf24; "
            "font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 12px;"
        )
        banner_layout.addWidget(self.prov_tag)
        right_layout.addWidget(banner)

        # --- B. Form Fields (Direct Grid, no excessive nested scroll) ---
        form_grid = QGridLayout()
        form_grid.setSpacing(9)
        form_grid.setColumnStretch(1, 1)

        # Row 0: Model / Identifier
        lbl_m = QLabel("<b>Model Identifier:</b>")
        lbl_m.setStyleSheet("color: #e2e8f0; font-size: 12px;")
        form_grid.addWidget(lbl_m, 0, 0, Qt.AlignmentFlag.AlignTop)

        model_box = QVBoxLayout()
        model_box.setSpacing(5)
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setToolTip("Select from curated models or type your custom identifier")
        self.model_combo.currentTextChanged.connect(self._on_model_text_changed)
        model_box.addWidget(self.model_combo)

        # Quick model preset pills container
        self.pills_container = QWidget()
        self.pills_layout = QHBoxLayout(self.pills_container)
        self.pills_layout.setContentsMargins(0, 0, 0, 0)
        self.pills_layout.setSpacing(6)
        model_box.addWidget(self.pills_container)

        form_grid.addLayout(model_box, 0, 1)

        # Row 1: Base URL / Webhook Endpoint
        lbl_u = QLabel("<b>Endpoint URL:</b>")
        lbl_u.setStyleSheet("color: #e2e8f0; font-size: 12px;")
        form_grid.addWidget(lbl_u, 1, 0)

        url_box = QHBoxLayout()
        url_box.setSpacing(6)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://api.provider.com/v1")
        self.url_edit.textChanged.connect(self._validate_url_indicator)
        url_box.addWidget(self.url_edit)

        self.btn_reset_url = QPushButton("Reset URL")
        self.btn_reset_url.setObjectName("secondaryBtn")
        self.btn_reset_url.setToolTip("Reset to official default API endpoint")
        self.btn_reset_url.clicked.connect(self._reset_default_url)
        url_box.addWidget(self.btn_reset_url)

        self.url_status_indicator = QLabel("✓")
        self.url_status_indicator.setStyleSheet("color: #10b981; font-weight: bold; font-size: 14px; padding: 0 4px;")
        url_box.addWidget(self.url_status_indicator)

        form_grid.addLayout(url_box, 1, 1)

        # Row 2: API Key Management
        lbl_k = QLabel("<b>API Key:</b>")
        lbl_k.setStyleSheet("color: #e2e8f0; font-size: 12px;")
        form_grid.addWidget(lbl_k, 2, 0)

        key_box = QHBoxLayout()
        key_box.setSpacing(6)
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("Enter API Key (Encrypted in local vault; optional for local webhooks)")
        self.key_edit.textChanged.connect(self._update_key_badge)
        key_box.addWidget(self.key_edit)

        self.btn_toggle_key = QPushButton("👁 Show")
        self.btn_toggle_key.setObjectName("secondaryBtn")
        self.btn_toggle_key.setFixedWidth(82)
        self.btn_toggle_key.clicked.connect(self._toggle_key_visibility)
        key_box.addWidget(self.btn_toggle_key)

        self.lbl_key_status = QLabel("○ Optional")
        self.lbl_key_status.setStyleSheet(
            "background-color: #1a1e2d; border: 1px solid #2d344d; border-radius: 10px; "
            "color: #94a3b8; font-size: 11px; padding: 4px 8px;"
        )
        key_box.addWidget(self.lbl_key_status)

        form_grid.addLayout(key_box, 2, 1)

        # Row 3: Custom Headers Editor
        lbl_h = QLabel("<b>Custom Headers:</b>")
        lbl_h.setStyleSheet("color: #e2e8f0; font-size: 12px;")
        form_grid.addWidget(lbl_h, 3, 0, Qt.AlignmentFlag.AlignTop)

        headers_container = QWidget()
        headers_layout = QVBoxLayout(headers_container)
        headers_layout.setContentsMargins(0, 0, 0, 0)
        headers_layout.setSpacing(5)

        # Top row: Switcher and quick preset buttons
        headers_toolbar = QHBoxLayout()
        headers_toolbar.setSpacing(6)

        self.btn_add_header = QPushButton("+ Add Header")
        self.btn_add_header.setObjectName("secondaryBtn")
        self.btn_add_header.setStyleSheet("padding: 3px 8px; font-size: 11px;")
        self.btn_add_header.clicked.connect(self._add_header_row)
        headers_toolbar.addWidget(self.btn_add_header)

        btn_add_bearer = QPushButton("+ Bearer Token")
        btn_add_bearer.setObjectName("pillBtn")
        btn_add_bearer.clicked.connect(lambda: self._insert_quick_header("Authorization", "Bearer <YOUR_TOKEN>"))
        headers_toolbar.addWidget(btn_add_bearer)

        btn_add_ct = QPushButton("+ Content-Type")
        btn_add_ct.setObjectName("pillBtn")
        btn_add_ct.clicked.connect(lambda: self._insert_quick_header("Content-Type", "application/json"))
        headers_toolbar.addWidget(btn_add_ct)

        headers_toolbar.addStretch()

        self.btn_toggle_headers_view = QPushButton("Toggle JSON Mode")
        self.btn_toggle_headers_view.setObjectName("secondaryBtn")
        self.btn_toggle_headers_view.setStyleSheet("padding: 3px 8px; font-size: 11px;")
        self.btn_toggle_headers_view.clicked.connect(self._toggle_headers_editor_mode)
        headers_toolbar.addWidget(self.btn_toggle_headers_view)

        headers_layout.addLayout(headers_toolbar)

        # Stack: Empty view (0) vs Table view (1) vs Raw JSON view (2)
        self.headers_stack = QStackedWidget()

        # View 0: Clean Empty State Placeholder
        empty_h_frame = QFrame()
        empty_h_frame.setStyleSheet("background-color: #10121b; border: 1px dashed #202436; border-radius: 6px;")
        empty_h_layout = QHBoxLayout(empty_h_frame)
        empty_h_layout.setContentsMargins(10, 6, 10, 6)
        lbl_empty_h = QLabel("○ No custom headers attached. Standard authentication and JSON formats are handled automatically.")
        lbl_empty_h.setStyleSheet("color: #64748b; font-size: 11px;")
        empty_h_layout.addWidget(lbl_empty_h)
        empty_h_layout.addStretch()
        self.headers_stack.addWidget(empty_h_frame)

        # View 1: Interactive Key-Value Table
        self.headers_table = QTableWidget()
        self.headers_table.setColumnCount(3)
        self.headers_table.setHorizontalHeaderLabels(["Header Key", "Header Value", "Action"])
        self.headers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.headers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.headers_table.verticalHeader().setVisible(False)
        self.headers_table.setColumnWidth(0, 160)
        self.headers_table.setColumnWidth(2, 54)
        self.headers_table.setFixedHeight(82)
        self.headers_stack.addWidget(self.headers_table)

        # View 2: Raw JSON Text Area
        self.headers_json_edit = QTextEdit()
        self.headers_json_edit.setPlaceholderText('{\n  "X-Custom-Auth": "secret-value"\n}')
        self.headers_json_edit.setFixedHeight(82)
        self.headers_stack.addWidget(self.headers_json_edit)

        headers_layout.addWidget(self.headers_stack)
        form_grid.addWidget(headers_container, 3, 1)

        # Row 4: Activation check & Tool Support Notice
        lbl_opts = QLabel("<b>Model Options:</b>")
        lbl_opts.setStyleSheet("color: #e2e8f0; font-size: 12px;")
        form_grid.addWidget(lbl_opts, 4, 0)

        opts_box = QHBoxLayout()
        opts_box.setSpacing(10)
        self.chk_set_active = QCheckBox("Set as Active Model immediately upon saving")
        self.chk_set_active.setChecked(True)
        opts_box.addWidget(self.chk_set_active)

        lbl_tools_notice = QLabel("⚡ Tool Calling & Bash Execution Parity Enabled")
        lbl_tools_notice.setStyleSheet(
            "background-color: #0f2e24; border: 1px solid #065f46; color: #34d399; "
            "font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 10px;"
        )
        opts_box.addWidget(lbl_tools_notice)
        opts_box.addStretch()

        form_grid.addLayout(opts_box, 4, 1)
        right_layout.addLayout(form_grid)

        # --- C. Live Status Banner ---
        self.status_bar = QFrame()
        self.status_bar.setStyleSheet("background-color: #10121b; border: 1px solid #1c1f2e; border-radius: 6px; padding: 4px 8px;")
        status_bar_layout = QHBoxLayout(self.status_bar)
        status_bar_layout.setContentsMargins(6, 2, 6, 2)
        self.status_label = QLabel("<span style='color: #64748b;'>Ready to test connection or save configuration.</span>")
        self.status_label.setStyleSheet("font-size: 12px; font-weight: 500;")
        status_bar_layout.addWidget(self.status_label)
        status_bar_layout.addStretch()
        right_layout.addWidget(self.status_bar)

        # --- D. Action Toolbar ---
        act_box = QHBoxLayout()
        act_box.setSpacing(10)

        self.btn_test = QPushButton("⚡ Test Connection")
        self.btn_test.setObjectName("secondaryBtn")
        self.btn_test.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_test.clicked.connect(self._test_connection)
        act_box.addWidget(self.btn_test)

        act_box.addStretch()

        self.btn_save_only = QPushButton("💾 Save Configuration")
        self.btn_save_only.setObjectName("secondaryBtn")
        self.btn_save_only.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_save_only.clicked.connect(lambda: self._save_model(set_active_override=False))
        act_box.addWidget(self.btn_save_only)

        self.btn_save_active = QPushButton("⭐ Save & Set Active")
        self.btn_save_active.setObjectName("primaryBtn")
        self.btn_save_active.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_save_active.clicked.connect(lambda: self._save_model(set_active_override=True))
        act_box.addWidget(self.btn_save_active)

        right_layout.addLayout(act_box)

        top_splitter.addWidget(right_frame)
        top_splitter.setSizes([320, 820])
        root_layout.addWidget(top_splitter, 3)

        # ----------------------------------------------------------------------
        # 3. BOTTOM PANEL: Configured Models Dashboard
        # ----------------------------------------------------------------------
        bot_frame = QFrame()
        bot_frame.setObjectName("cardFrame")
        bot_layout = QVBoxLayout(bot_frame)
        bot_layout.setContentsMargins(14, 10, 14, 10)
        bot_layout.setSpacing(8)

        # Top Metric Stat Cards Row
        stat_bar = QHBoxLayout()
        stat_bar.setSpacing(10)

        # Stat 1: Total Models
        card_total = QFrame()
        card_total.setObjectName("statCard")
        c1_layout = QHBoxLayout(card_total)
        c1_layout.setContentsMargins(8, 3, 8, 3)
        self.lbl_stat_count = QLabel("<b>0</b> Models Configured")
        self.lbl_stat_count.setStyleSheet("color: #e2e8f0; font-size: 12px;")
        c1_layout.addWidget(self.lbl_stat_count)
        stat_bar.addWidget(card_total)

        # Stat 2: Active Model
        card_active = QFrame()
        card_active.setObjectName("statCard")
        c2_layout = QHBoxLayout(card_active)
        c2_layout.setContentsMargins(8, 3, 8, 3)
        self.lbl_stat_active = QLabel("Active: <span style='color: #a78bfa;'>Offline Engine</span>")
        self.lbl_stat_active.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        c2_layout.addWidget(self.lbl_stat_active)
        stat_bar.addWidget(card_active)

        # Stat 3: Security & Storage
        card_sec = QFrame()
        card_sec.setObjectName("statCard")
        c3_layout = QHBoxLayout(card_sec)
        c3_layout.setContentsMargins(8, 3, 8, 3)
        lbl_sec = QLabel("🔒 Local Vault: <span style='color: #10b981;'>Masked & Encrypted</span>")
        lbl_sec.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        c3_layout.addWidget(lbl_sec)
        stat_bar.addWidget(card_sec)

        stat_bar.addStretch()

        btn_refresh = QPushButton("↻ Refresh List")
        btn_refresh.setObjectName("secondaryBtn")
        btn_refresh.setStyleSheet("padding: 3px 9px; font-size: 11px;")
        btn_refresh.clicked.connect(self._load_registered_models)
        stat_bar.addWidget(btn_refresh)

        bot_layout.addLayout(stat_bar)

        # Configured Models Table (with hidden row numbers for a modern look)
        self.models_table = QTableWidget()
        self.models_table.setColumnCount(6)
        self.models_table.setHorizontalHeaderLabels([
            "Status", "Provider", "Model ID", "Endpoint / Webhook", "API Key", "Actions"
        ])
        self.models_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.models_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.models_table.verticalHeader().setVisible(False)
        self.models_table.setColumnWidth(0, 105)
        self.models_table.setColumnWidth(1, 150)
        self.models_table.setColumnWidth(3, 270)
        self.models_table.setColumnWidth(4, 130)
        self.models_table.setColumnWidth(5, 195)
        self.models_table.setMinimumHeight(130)
        bot_layout.addWidget(self.models_table)

        root_layout.addWidget(bot_frame, 2)

    # ==========================================================================
    # PROVIDER EXPLORER LOGIC
    # ==========================================================================
    def _populate_provider_list(self):
        self.provider_list.clear()

        # Count configured models per provider
        configured_counts = {}
        for m in OnlineModelRegistry.list_models(safe=True):
            p_id = m.get("provider_id", "")
            configured_counts[p_id] = configured_counts.get(p_id, 0) + 1

        categories = [
            ("🇮🇳 Indian Sovereign AI", "indian_ai", [
                ("sarvam", "Sarvam AI (India 🇮🇳)"),
                ("krutrim", "Krutrim Cloud (India 🇮🇳)"),
                ("two_ai", "Two AI (SUTRA 🇮🇳)"),
                ("bharatgpt", "BharatGPT / Hanooman (🇮🇳)"),
            ]),
            ("🌐 Global Flagship Providers", "cloud", [
                ("anthropic", "Anthropic Claude"),
                ("openai", "OpenAI"),
                ("gemini", "Google Gemini"),
                ("deepseek", "DeepSeek AI"),
                ("mistral", "Mistral AI"),
                ("xai", "xAI Grok"),
                ("cohere", "Cohere Command"),
                ("perplexity", "Perplexity Sonar"),
            ]),
            ("⚡ Ultra-Fast Cloud & LPUs", "cloud_fast", [
                ("groq", "Groq Fast LPU"),
                ("cerebras", "Cerebras CS-3"),
                ("sambanova", "SambaNova Systems"),
                ("together", "Together AI"),
                ("fireworks", "Fireworks AI"),
                ("openrouter", "OpenRouter Multi-Hub"),
            ]),
            ("🔌 Custom Webhooks & Self-Hosted", "custom", [
                ("custom_webhook", "Custom Webhook & Event API"),
                ("custom_openai", "Custom OpenAI-Compatible API"),
                ("ollama", "Ollama Local Engine"),
                ("vllm", "vLLM High-Throughput Server"),
            ]),
        ]

        for cat_title, cat_type, provs in categories:
            header_item = QListWidgetItem(f"▾ {cat_title}")
            header_item.setFlags(Qt.ItemFlag.NoItemFlags)
            header_item.setForeground(QColor("#717b9b"))
            font = header_item.font()
            font.setBold(True)
            font.setPointSize(10)
            header_item.setFont(font)
            self.provider_list.addItem(header_item)

            for key, display_name in provs:
                count = configured_counts.get(key, 0)
                label = f"{display_name}  [{count}]" if count > 0 else display_name
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, key)
                item.setData(Qt.ItemDataRole.UserRole + 1, cat_title)
                if count > 0:
                    item.setForeground(QColor("#38bdf8"))
                self.provider_list.addItem(item)

    def _filter_providers(self, text: str):
        search = text.strip().lower()
        self.btn_clear_search.setVisible(bool(search))
        for i in range(self.provider_list.count()):
            item = self.provider_list.item(i)
            key = item.data(Qt.ItemDataRole.UserRole)
            if not key:
                # Category header
                continue
            matches = search in item.text().lower() or search in key.lower()
            item.setHidden(not matches)

    def _on_provider_item_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if not current:
            return
        key = current.data(Qt.ItemDataRole.UserRole)
        cat_badge = current.data(Qt.ItemDataRole.UserRole + 1) or "Custom Provider"
        if key:
            self._current_provider_badge = cat_badge
            self._select_provider(key)

    def _select_provider(self, key: str):
        self._active_preset_key = key
        preset = PROVIDER_PRESETS.get(key, {})

        name = preset.get("name", "Custom Webhook")
        desc = preset.get("description", "Custom AI endpoint or webhook integration.")
        base_url = preset.get("base_url", "https://api.domain.com/v1")
        models = preset.get("models", [])
        default_model = preset.get("default_model", "")

        self.prov_title.setText(f"<h3>{name}</h3>")
        self.prov_desc.setText(desc)

        # Dynamic category tag & styling
        cat = preset.get("category", "")
        if cat == "indian_ai":
            tag_text = "🇮🇳 Indian Sovereign AI"
            tag_style = "background-color: #2a1f10; border: 1px solid #78350f; color: #fbbf24; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 12px;"
        elif cat == "cloud":
            tag_text = "🌐 Global Flagship Provider"
            tag_style = "background-color: #10233b; border: 1px solid #1e3a8a; color: #38bdf8; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 12px;"
        elif cat == "cloud_fast":
            tag_text = "⚡ Ultra-Fast Cloud LPU"
            tag_style = "background-color: #24163b; border: 1px solid #581c87; color: #c084fc; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 12px;"
        elif cat == "custom" or "webhook" in key:
            tag_text = "🔌 Custom Webhook & Endpoint"
            tag_style = "background-color: #0f2e24; border: 1px solid #065f46; color: #34d399; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 12px;"
        else:
            tag_text = self._current_provider_badge
            tag_style = "background-color: #1a1e2d; border: 1px solid #2d344d; color: #94a3b8; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 12px;"

        self.prov_tag.setText(tag_text)
        self.prov_tag.setStyleSheet(tag_style)
        self.url_edit.setText(base_url)

        # Sync list selection
        for i in range(self.provider_list.count()):
            item = self.provider_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == key:
                self.provider_list.blockSignals(True)
                self.provider_list.setCurrentItem(item)
                self.provider_list.blockSignals(False)
                break

        # Populate model combo
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for m in models:
            self.model_combo.addItem(m)
        if default_model:
            self.model_combo.setCurrentText(default_model)
        elif models:
            self.model_combo.setCurrentIndex(0)
        else:
            self.model_combo.setEditText("custom-model-id")
        self.model_combo.blockSignals(False)

        # Rebuild quick preset pills
        self._rebuild_preset_pills(models[:5], self.model_combo.currentText())

        # Tailor placeholder for API key
        if "sarvam" in key:
            self.key_edit.setPlaceholderText("sarvam-... API key from sarvam.ai")
        elif "anthropic" in key:
            self.key_edit.setPlaceholderText("sk-ant-... API key from console.anthropic.com")
        elif "openai" in key:
            self.key_edit.setPlaceholderText("sk-... API key from platform.openai.com")
        elif "gemini" in key:
            self.key_edit.setPlaceholderText("AIza... API key from Google AI Studio")
        elif preset.get("api_key_required", False):
            self.key_edit.setPlaceholderText("Enter provider API Key")
        else:
            self.key_edit.setPlaceholderText("Optional API key for internal webhook or local engine")

        self._update_key_badge()
        self.status_label.setText("<span style='color: #64748b;'>Selected provider: " + name + "</span>")

    def _rebuild_preset_pills(self, pills: List[str], current_model: str):
        # Clear existing pills
        self._preset_buttons.clear()
        while self.pills_layout.count():
            child = self.pills_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        lbl_quick = QLabel("Presets:")
        lbl_quick.setStyleSheet("color: #64748b; font-size: 11px; margin-right: 2px;")
        self.pills_layout.addWidget(lbl_quick)

        for m_id in pills:
            btn = QPushButton(m_id)
            is_active = (m_id == current_model)
            btn.setObjectName("pillBtnActive" if is_active else "pillBtn")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda _, mid=m_id: self.model_combo.setCurrentText(mid))
            self._preset_buttons.append(btn)
            self.pills_layout.addWidget(btn)

        self.pills_layout.addStretch()

    def _on_model_text_changed(self, current_text: str):
        for btn in self._preset_buttons:
            if btn.text() == current_text:
                btn.setObjectName("pillBtnActive")
            else:
                btn.setObjectName("pillBtn")
            btn.setStyle(btn.style())

    def _reset_default_url(self):
        preset = PROVIDER_PRESETS.get(self._active_preset_key, {})
        default_url = preset.get("base_url", "https://api.domain.com/v1")
        self.url_edit.setText(default_url)

    def _validate_url_indicator(self, text: str):
        url = text.strip()
        if url.startswith("http://") or url.startswith("https://"):
            self.url_status_indicator.setText("✓")
            self.url_status_indicator.setStyleSheet("color: #10b981; font-weight: bold; font-size: 14px;")
            self.url_status_indicator.setToolTip("Valid URL protocol format")
        else:
            self.url_status_indicator.setText("⚠")
            self.url_status_indicator.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 14px;")
            self.url_status_indicator.setToolTip("URL should begin with https:// or http://")

    def _toggle_key_visibility(self):
        if self.key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_key.setText("🙈 Hide")
        else:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_key.setText("👁 Show")

    def _update_key_badge(self):
        val = self.key_edit.text().strip()
        preset = PROVIDER_PRESETS.get(self._active_preset_key, {})
        required = preset.get("api_key_required", False)

        if val:
            self.lbl_key_status.setText("● Key Provided")
            self.lbl_key_status.setStyleSheet(
                "background-color: #0f2e24; border: 1px solid #065f46; border-radius: 10px; "
                "color: #34d399; font-size: 11px; padding: 4px 8px;"
            )
        elif required:
            self.lbl_key_status.setText("⚠ Required")
            self.lbl_key_status.setStyleSheet(
                "background-color: #2e1d0f; border: 1px solid #78350f; border-radius: 10px; "
                "color: #fbbf24; font-size: 11px; padding: 4px 8px;"
            )
        else:
            self.lbl_key_status.setText("○ Optional")
            self.lbl_key_status.setStyleSheet(
                "background-color: #1a1e2d; border: 1px solid #2d344d; border-radius: 10px; "
                "color: #94a3b8; font-size: 11px; padding: 4px 8px;"
            )

    # ==========================================================================
    # CUSTOM HEADERS EDITOR LOGIC
    # ==========================================================================
    def _add_header_row(self, key: str = "", val: str = ""):
        if self.headers_stack.currentIndex() == 0:
            self.headers_stack.setCurrentIndex(1)

        row = self.headers_table.rowCount()
        self.headers_table.insertRow(row)

        key_item = QLineEdit(key)
        key_item.setPlaceholderText("Header name (e.g. X-Tenant-Id)")
        self.headers_table.setCellWidget(row, 0, key_item)

        val_item = QLineEdit(val)
        val_item.setPlaceholderText("Value")
        self.headers_table.setCellWidget(row, 1, val_item)

        btn_del = QPushButton("✕")
        btn_del.setObjectName("dangerBtn")
        btn_del.setStyleSheet("padding: 2px 6px; font-size: 11px;")
        btn_del.clicked.connect(lambda _, r=row: self._delete_header_row(r))
        self.headers_table.setCellWidget(row, 2, btn_del)

    def _delete_header_row(self, row: int):
        self.headers_table.removeRow(row)
        for r in range(self.headers_table.rowCount()):
            btn = self.headers_table.cellWidget(r, 2)
            if isinstance(btn, QPushButton):
                btn.clicked.disconnect()
                btn.clicked.connect(lambda _, curr_r=r: self._delete_header_row(curr_r))

        if self.headers_table.rowCount() == 0 and self.headers_stack.currentIndex() == 1:
            self.headers_stack.setCurrentIndex(0)

    def _insert_quick_header(self, key: str, val: str):
        if self.headers_stack.currentIndex() == 2:
            headers = self._get_headers_dict()
            headers[key] = val
            self.headers_json_edit.setText(json.dumps(headers, indent=2))
        else:
            self._add_header_row(key, val)

    def _toggle_headers_editor_mode(self):
        if self.headers_stack.currentIndex() in (0, 1):
            headers = self._get_headers_dict()
            self.headers_json_edit.setText(json.dumps(headers, indent=2))
            self.headers_stack.setCurrentIndex(2)
            self.btn_toggle_headers_view.setText("Switch to Table")
        else:
            text = self.headers_json_edit.toPlainText().strip()
            headers = {}
            if text:
                try:
                    headers = json.loads(text)
                except Exception as e:
                    QMessageBox.warning(self, "Invalid JSON", f"Cannot switch: {e}")
                    return
            self.headers_table.setRowCount(0)
            for k, v in headers.items():
                self._add_header_row(str(k), str(v))
            if len(headers) > 0:
                self.headers_stack.setCurrentIndex(1)
            else:
                self.headers_stack.setCurrentIndex(0)
            self.btn_toggle_headers_view.setText("Toggle JSON Mode")

    def _get_headers_dict(self) -> dict:
        headers = {}
        if self.headers_stack.currentIndex() == 2:
            text = self.headers_json_edit.toPlainText().strip()
            if text:
                try:
                    headers = json.loads(text)
                except Exception:
                    pass
        elif self.headers_stack.currentIndex() == 1:
            for r in range(self.headers_table.rowCount()):
                k_widget = self.headers_table.cellWidget(r, 0)
                v_widget = self.headers_table.cellWidget(r, 1)
                if isinstance(k_widget, QLineEdit) and isinstance(v_widget, QLineEdit):
                    k = k_widget.text().strip()
                    v = v_widget.text().strip()
                    if k:
                        headers[k] = v
        return headers

    # ==========================================================================
    # ASYNC CONNECTION TEST
    # ==========================================================================
    def _test_connection(self):
        key = self._active_preset_key
        preset = PROVIDER_PRESETS.get(key, {})
        p_type = preset.get("type", "openai_compatible")
        base_url = self.url_edit.text().strip()
        api_key = self.key_edit.text().strip()
        model_id = self.model_combo.currentText().strip()
        custom_headers = self._get_headers_dict()

        if not base_url:
            self.status_label.setText("<span style='color: #ef4444;'>❌ Error: Base URL is required to test.</span>")
            return

        self.btn_test.setEnabled(False)
        self.status_label.setText(
            "<span style='color: #38bdf8;'>⏳ Pinging endpoint & testing authentication...</span>"
        )

        self._test_thread = TestWorker(
            p_type=p_type,
            base_url=base_url,
            api_key=api_key,
            model_id=model_id,
            custom_headers=custom_headers
        )
        self._test_thread.finished.connect(self._on_test_finished)
        self._test_thread.start()

    def _on_test_finished(self, res: dict):
        self.btn_test.setEnabled(True)
        latency = res.get("latency_ms", 0)
        if res.get("success"):
            msg = res.get("message", "Connected successfully")
            self.status_label.setText(
                f"<span style='color: #10b981;'>✓ {msg} · Latency: {latency}ms</span>"
            )
        else:
            err = res.get("error", "Connection failed")
            self.status_label.setText(
                f"<span style='color: #ef4444;'>❌ {err} · Latency: {latency}ms</span>"
            )

    # ==========================================================================
    # SAVE & SET ACTIVE
    # ==========================================================================
    def _save_model(self, set_active_override: Optional[bool] = None):
        key = self._active_preset_key
        preset = PROVIDER_PRESETS.get(key, {})
        p_name = preset.get("name", "Custom Webhook")
        p_type = preset.get("type", "openai_compatible")
        base_url = self.url_edit.text().strip()
        api_key = self.key_edit.text().strip()
        model_id = self.model_combo.currentText().strip()

        if not model_id:
            QMessageBox.warning(self, "Missing Model", "Please enter or select a model identifier.")
            return

        if not base_url:
            QMessageBox.warning(self, "Missing Endpoint", "Please enter a valid base URL or webhook endpoint.")
            return

        custom_headers = self._get_headers_dict()
        set_active = self.chk_set_active.isChecked() if set_active_override is None else set_active_override

        saved_key = OnlineModelRegistry.add_model(
            name=f"{p_name} · {model_id}",
            provider_id=key,
            provider_name=p_name,
            model_id=model_id,
            p_type=p_type,
            base_url=base_url,
            api_key=api_key,
            custom_headers=custom_headers,
            category=preset.get("category", "general"),
            set_active=set_active
        )

        self.status_label.setText(
            f"<span style='color: #10b981;'>✓ Successfully configured model '{model_id}'!</span>"
        )
        self._load_registered_models()
        self._populate_provider_list()

        if set_active:
            QMessageBox.information(
                self,
                "Model Activated",
                f"Model '{model_id}' ({p_name}) has been saved and set as the active model for LMMs with full tool execution parity!"
            )

    # ==========================================================================
    # REGISTERED MODELS DASHBOARD
    # ==========================================================================
    def _load_registered_models(self):
        models = OnlineModelRegistry.list_models(safe=True)
        active_type = OnlineModelRegistry.get_active_type()
        active_model = OnlineModelRegistry.get_active_model()
        active_key = active_model.get("key") if active_model else None

        # Update Top Header & Stat Cards
        if active_type == "online" and active_model:
            active_title = f"{active_model.get('provider_name')} · {active_model.get('id')}"
            self.lbl_header_active.setText(f"● Active: [Online] {active_title}")
            self.lbl_header_active.setStyleSheet(
                "background-color: #0f2e24; border: 1px solid #065f46; border-radius: 14px; "
                "color: #34d399; font-size: 11px; font-weight: 600; padding: 5px 12px;"
            )
            self.lbl_stat_active.setText(f"Active: <span style='color: #34d399;'>{active_title}</span>")
        else:
            self.lbl_header_active.setText("● Active: [Offline Engine]")
            self.lbl_header_active.setStyleSheet(
                "background-color: #1f1d38; border: 1px solid #4338ca; border-radius: 14px; "
                "color: #a78bfa; font-size: 11px; font-weight: 600; padding: 5px 12px;"
            )
            self.lbl_stat_active.setText("Active: <span style='color: #a78bfa;'>Offline Local Engine</span>")

        self.lbl_stat_count.setText(f"<b>{len(models)}</b> Online Models Configured")

        self.models_table.setRowCount(len(models))

        for row, m in enumerate(models):
            is_active = (m.get("key") == active_key and active_type == "online")

            # Col 0: Status Pill
            status_item = QTableWidgetItem("● ACTIVE" if is_active else "○ STANDBY")
            status_item.setForeground(QColor("#34d399" if is_active else "#64748b"))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            font = status_item.font()
            font.setBold(True)
            font.setPointSize(10)
            status_item.setFont(font)
            self.models_table.setItem(row, 0, status_item)

            # Col 1: Provider Name
            prov_item = QTableWidgetItem(m.get("provider_name", ""))
            self.models_table.setItem(row, 1, prov_item)

            # Col 2: Model ID (Monospace)
            id_item = QTableWidgetItem(m.get("id", ""))
            id_item.setFont(QFont("Monospace", 10))
            self.models_table.setItem(row, 2, id_item)

            # Col 3: Endpoint
            url_item = QTableWidgetItem(m.get("base_url", ""))
            self.models_table.setItem(row, 3, url_item)

            # Col 4: API Key Masked
            key_item = QTableWidgetItem(m.get("api_key_masked", "Configured"))
            key_item.setForeground(QColor("#94a3b8"))
            self.models_table.setItem(row, 4, key_item)

            # Col 5: Actions
            btn_frame = QWidget()
            btn_layout = QHBoxLayout(btn_frame)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)

            m_key = m.get("key")

            if is_active:
                btn_set = QPushButton("✓ Active")
                btn_set.setEnabled(False)
                btn_set.setObjectName("secondaryBtn")
                btn_set.setStyleSheet("padding: 3px 8px; font-size: 11px; color: #34d399; border-color: #065f46;")
            else:
                btn_set = QPushButton("Set Active")
                btn_set.setObjectName("accentActionBtn")
                btn_set.setStyleSheet("padding: 3px 8px; font-size: 11px;")
                btn_set.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                btn_set.clicked.connect(lambda _, k=m_key: self._set_model_active(k))
            btn_layout.addWidget(btn_set)

            btn_test = QPushButton("Test")
            btn_test.setObjectName("secondaryBtn")
            btn_test.setStyleSheet("padding: 3px 8px; font-size: 11px;")
            btn_test.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_test.clicked.connect(lambda _, mod=m: self._test_registered_model(mod))
            btn_layout.addWidget(btn_test)

            btn_del = QPushButton("Delete")
            btn_del.setObjectName("dangerBtn")
            btn_del.setStyleSheet("padding: 3px 8px; font-size: 11px;")
            btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_del.clicked.connect(lambda _, k=m_key: self._delete_model(k))
            btn_layout.addWidget(btn_del)

            self.models_table.setCellWidget(row, 5, btn_frame)

    def _test_registered_model(self, mod: dict):
        p_type = mod.get("type", "openai_compatible")
        base_url = mod.get("base_url", "")
        m_id = mod.get("id", "")
        full_mod = OnlineModelRegistry.get_model(mod.get("key", ""))
        api_key = full_mod.get("api_key", "") if full_mod else ""
        custom_headers = full_mod.get("custom_headers", {}) if full_mod else {}

        self.status_label.setText(f"<span style='color: #38bdf8;'>⏳ Testing saved model '{m_id}'...</span>")
        res = OnlineModelClient.test_connection(
            p_type=p_type,
            base_url=base_url,
            api_key=api_key,
            model_id=m_id,
            custom_headers=custom_headers
        )
        if res.get("success"):
            self.status_label.setText(f"<span style='color: #10b981;'>✓ Connected to '{m_id}': {res.get('message')}</span>")
        else:
            self.status_label.setText(f"<span style='color: #ef4444;'>❌ Ping failed for '{m_id}': {res.get('error')}</span>")

    def _set_model_active(self, key: str):
        OnlineModelRegistry.set_active_model(key, "online")
        self._load_registered_models()

    def _delete_model(self, key: str):
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete configured model '{key}'?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            OnlineModelRegistry.remove_model(key)
            self._load_registered_models()
            self._populate_provider_list()


def launch_model_manager_dialog():
    """Entry point to launch the dialog in a standalone Qt Application."""
    app = QApplication.instance()
    owns_app = False
    if not app:
        app = QApplication(sys.argv)
        owns_app = True

    dialog = ModelManagerDialog()
    dialog.show()

    if owns_app:
        app.exec()


if __name__ == "__main__":
    launch_model_manager_dialog()
