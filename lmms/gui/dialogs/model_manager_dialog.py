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
Native Desktop interface to add, configure, test, and switch online LLM providers
(Anthropic, OpenAI, Gemini, Sarvam AI, Krutrim, DeepSeek, Groq, and Custom Webhooks).
"""

from __future__ import annotations

import sys
import json
from typing import Dict, Any, Optional

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QColor, QCursor, QFont, QIcon
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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from lmms.backend.core.registry.online_models import OnlineModelRegistry
from lmms.backend.core.registry.provider_presets import PROVIDER_PRESETS
from lmms.backend.providers.online_client import OnlineModelClient


# Dark Obsidian & Cyberpunk Slate Theme Stylesheet
STYLESHEET = """
QDialog {
    background-color: #101116;
    color: #f3f4f6;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
QFrame#sidebarFrame {
    background-color: #16171e;
    border-right: 1px solid #272835;
}
QFrame#cardFrame {
    background-color: #171821;
    border: 1px solid #272835;
    border-radius: 10px;
}
QLineEdit, QComboBox {
    background-color: #1e202b;
    border: 1px solid #333647;
    border-radius: 6px;
    padding: 8px 12px;
    color: #f3f4f6;
    font-size: 13px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #38bdf8;
    background-color: #232533;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QPushButton {
    border-radius: 6px;
    font-weight: 600;
    font-size: 13px;
    padding: 8px 16px;
}
QPushButton#primaryBtn {
    background-color: #0284c7;
    color: #ffffff;
    border: 1px solid #38bdf8;
}
QPushButton#primaryBtn:hover {
    background-color: #0369a1;
}
QPushButton#secondaryBtn {
    background-color: #262837;
    color: #e2e8f0;
    border: 1px solid #3d4158;
}
QPushButton#secondaryBtn:hover {
    background-color: #323549;
}
QPushButton#dangerBtn {
    background-color: #451a1a;
    color: #fca5a5;
    border: 1px solid #7f1d1d;
}
QPushButton#dangerBtn:hover {
    background-color: #5c1d1d;
}
QListWidget {
    background-color: transparent;
    border: none;
    color: #cbd5e1;
    font-size: 13px;
    outline: none;
}
QListWidget::item {
    padding: 10px 14px;
    border-radius: 6px;
    margin-bottom: 2px;
}
QListWidget::item:hover {
    background-color: #212330;
    color: #f8fafc;
}
QListWidget::item:selected {
    background-color: #292d3f;
    color: #38bdf8;
    font-weight: 600;
    border-left: 3px solid #38bdf8;
}
QTableWidget {
    background-color: #14151c;
    border: 1px solid #272835;
    border-radius: 8px;
    gridline-color: #272835;
    color: #f1f5f9;
}
QHeaderView::section {
    background-color: #1a1b24;
    color: #94a3b8;
    font-weight: 600;
    font-size: 12px;
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid #272835;
}
QScrollBar:vertical {
    background: #12131a;
    width: 8px;
    margin: 0px;
}
QScrollBar::thumb:vertical {
    background: #2d3042;
    border-radius: 4px;
}
"""


class ModelManagerDialog(QDialog):
    """Interactive Native GUI for Adding and Managing Online LLMs & Webhooks."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("LMMs · AI Models & Custom Webhook Hub")
        self.resize(1100, 750)
        self.setMinimumSize(880, 580)
        self.setStyleSheet(STYLESHEET)

        self._active_preset_key = "sarvam"
        self._init_ui()
        self._load_registered_models()
        self._select_provider("sarvam")

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Header bar
        header_bar = QHBoxLayout()
        title_label = QLabel("<h2>🧠 AI Models & Custom Webhook Hub</h2>")
        title_label.setStyleSheet("color: #f8fafc; margin: 0;")
        header_bar.addWidget(title_label)

        sub_label = QLabel("<span style='color: #94a3b8;'>Add API keys or custom webhooks with full agent & tool execution parity.</span>")
        header_bar.addWidget(sub_label)
        header_bar.addStretch()

        btn_close = QPushButton("✕ Close")
        btn_close.setObjectName("secondaryBtn")
        btn_close.clicked.connect(self.close)
        header_bar.addWidget(btn_close)
        main_layout.addLayout(header_bar)

        # Top Splitter: Left Sidebar (Providers) | Right Config Form
        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Left Sidebar ---
        sidebar_frame = QFrame()
        sidebar_frame.setObjectName("sidebarFrame")
        side_layout = QVBoxLayout(sidebar_frame)
        side_layout.setContentsMargins(10, 10, 10, 10)
        side_layout.setSpacing(8)

        search_label = QLabel("<b>Select Provider</b>")
        search_label.setStyleSheet("color: #94a3b8; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;")
        side_layout.addWidget(search_label)

        self.provider_search = QLineEdit()
        self.provider_search.setPlaceholderText("Search providers...")
        self.provider_search.textChanged.connect(self._filter_providers)
        side_layout.addWidget(self.provider_search)

        self.provider_list = QListWidget()
        self.provider_list.currentItemChanged.connect(self._on_provider_item_changed)
        side_layout.addWidget(self.provider_list)

        self._populate_provider_list()
        top_splitter.addWidget(sidebar_frame)

        # --- Right Config Form ---
        right_frame = QFrame()
        right_frame.setObjectName("cardFrame")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(14)

        # Provider Details Header
        self.prov_title = QLabel("<h3>Sarvam AI (India 🇮🇳)</h3>")
        self.prov_desc = QLabel("<span style='color: #94a3b8;'>Foundational Indian language AI models built by Sarvam AI.</span>")
        right_layout.addWidget(self.prov_title)
        right_layout.addWidget(self.prov_desc)

        # Form Grid
        form_grid = QGridLayout()
        form_grid.setSpacing(12)

        # Row 0: Model Selector
        form_grid.addWidget(QLabel("<b>Model / Identifier:</b>"), 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setToolTip("Select preset model or type any custom model ID")
        form_grid.addWidget(self.model_combo, 0, 1)

        # Row 1: Base URL / Webhook
        form_grid.addWidget(QLabel("<b>Base URL / Endpoint:</b>"), 1, 0)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://api.domain.com/v1")
        form_grid.addWidget(self.url_edit, 1, 1)

        # Row 2: API Key
        form_grid.addWidget(QLabel("<b>API Key:</b>"), 2, 0)
        key_box = QHBoxLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("Enter API Key (Optional for unprotected local webhooks)")
        key_box.addWidget(self.key_edit)

        self.btn_toggle_key = QPushButton("👁")
        self.btn_toggle_key.setFixedWidth(36)
        self.btn_toggle_key.setObjectName("secondaryBtn")
        self.btn_toggle_key.clicked.connect(self._toggle_key_visibility)
        key_box.addWidget(self.btn_toggle_key)
        form_grid.addLayout(key_box, 2, 1)

        # Row 3: Custom Headers (JSON)
        form_grid.addWidget(QLabel("<b>Custom Headers:</b>"), 3, 0)
        self.headers_edit = QLineEdit()
        self.headers_edit.setPlaceholderText('Optional JSON headers e.g. {"X-Custom-Auth": "secret"}')
        form_grid.addWidget(self.headers_edit, 3, 1)

        # Row 4: Set active toggle
        self.chk_set_active = QCheckBox("Set as Active Model immediately")
        self.chk_set_active.setChecked(True)
        form_grid.addWidget(self.chk_set_active, 4, 1)

        right_layout.addLayout(form_grid)

        # Status & Action Buttons
        act_box = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        act_box.addWidget(self.status_label)
        act_box.addStretch()

        self.btn_test = QPushButton("⚡ Test Connection")
        self.btn_test.setObjectName("secondaryBtn")
        self.btn_test.clicked.connect(self._test_connection)
        act_box.addWidget(self.btn_test)

        self.btn_save = QPushButton("💾 Save & Add Model")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.clicked.connect(self._save_model)
        act_box.addWidget(self.btn_save)

        right_layout.addLayout(act_box)
        right_layout.addStretch()

        top_splitter.addWidget(right_frame)
        top_splitter.setSizes([300, 750])
        main_layout.addWidget(top_splitter, 3)

        # --- Bottom Panel: Registered Online Models Table ---
        bot_frame = QFrame()
        bot_frame.setObjectName("cardFrame")
        bot_layout = QVBoxLayout(bot_frame)
        bot_layout.setContentsMargins(14, 12, 14, 12)
        bot_layout.setSpacing(8)

        bot_header = QHBoxLayout()
        bot_title = QLabel("<b>Configured Online & Webhook Models</b>")
        bot_title.setStyleSheet("color: #f1f5f9; font-size: 14px;")
        bot_header.addWidget(bot_title)
        bot_header.addStretch()

        self.lbl_active_info = QLabel("Active: [Offline Engine]")
        self.lbl_active_info.setStyleSheet("color: #38bdf8; font-weight: 600;")
        bot_header.addWidget(self.lbl_active_info)
        bot_layout.addLayout(bot_header)

        self.models_table = QTableWidget()
        self.models_table.setColumnCount(6)
        self.models_table.setHorizontalHeaderLabels(["Status", "Provider", "Model ID", "Endpoint / Webhook", "API Key", "Actions"])
        self.models_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.models_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.models_table.setColumnWidth(0, 100)
        self.models_table.setColumnWidth(1, 150)
        self.models_table.setColumnWidth(3, 260)
        self.models_table.setColumnWidth(4, 140)
        self.models_table.setColumnWidth(5, 180)
        bot_layout.addWidget(self.models_table)

        main_layout.addWidget(bot_frame, 2)

    def _populate_provider_list(self):
        self.provider_list.clear()

        # Categorized Presets
        categories = [
            ("🇮🇳 Indian AI Providers", [
                ("sarvam", "Sarvam AI (India 🇮🇳)"),
                ("krutrim", "Krutrim Cloud (India 🇮🇳)"),
                ("two_ai", "Two AI (SUTRA 🇮🇳)"),
                ("bharatgpt", "BharatGPT / Hanooman (🇮🇳)"),
            ]),
            ("🌐 Global Flagships", [
                ("anthropic", "Anthropic Claude"),
                ("openai", "OpenAI"),
                ("gemini", "Google Gemini"),
                ("deepseek", "DeepSeek AI"),
                ("groq", "Groq Fast LPU"),
                ("mistral", "Mistral AI"),
                ("openrouter", "OpenRouter (Multi-Hub)"),
                ("together", "Together AI"),
                ("perplexity", "Perplexity Sonar"),
                ("fireworks", "Fireworks AI"),
                ("cohere", "Cohere Command"),
                ("xai", "xAI Grok"),
                ("cerebras", "Cerebras CS-3"),
                ("sambanova", "SambaNova Systems"),
            ]),
            ("🔌 Custom Webhook & Endpoints", [
                ("custom_webhook", "Custom Webhook & Endpoint"),
                ("custom_openai", "Custom OpenAI-Compatible"),
            ])
        ]

        for cat_name, provs in categories:
            header_item = QListWidgetItem(f"── {cat_name} ──")
            header_item.setFlags(Qt.ItemFlag.NoItemFlags)
            header_item.setForeground(QColor("#64748b"))
            self.provider_list.addItem(header_item)

            for key, display_name in provs:
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, key)
                self.provider_list.addItem(item)

    def _filter_providers(self, text: str):
        search = text.lower()
        for i in range(self.provider_list.count()):
            item = self.provider_list.item(i)
            key = item.data(Qt.ItemDataRole.UserRole)
            if not key:
                continue
            item.setHidden(search not in item.text().lower() and search not in key.lower())

    def _on_provider_item_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if not current:
            return
        key = current.data(Qt.ItemDataRole.UserRole)
        if key:
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
        self.prov_desc.setText(f"<span style='color: #94a3b8;'>{desc}</span>")
        self.url_edit.setText(base_url)

        self.model_combo.clear()
        for m in models:
            self.model_combo.addItem(m)
        if default_model:
            self.model_combo.setCurrentText(default_model)
        elif models:
            self.model_combo.setCurrentIndex(0)
        else:
            self.model_combo.setEditText("custom-model-id")

        self.status_label.setText("")

    def _toggle_key_visibility(self):
        if self.key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_key.setText("🙈")
        else:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_key.setText("👁")

    def _test_connection(self):
        key = self._active_preset_key
        preset = PROVIDER_PRESETS.get(key, {})
        p_type = preset.get("type", "openai_compatible")
        base_url = self.url_edit.text().strip()
        api_key = self.key_edit.text().strip()
        model_id = self.model_combo.currentText().strip()

        custom_headers = {}
        h_text = self.headers_edit.text().strip()
        if h_text:
            try:
                custom_headers = json.loads(h_text)
            except Exception:
                self.status_label.setText("<span style='color:#ef4444;'>❌ Invalid JSON in Custom Headers</span>")
                return

        self.status_label.setText("<span style='color:#38bdf8;'>⏳ Testing connection...</span>")
        QApplication.processEvents()

        res = OnlineModelClient.test_connection(
            p_type=p_type,
            base_url=base_url,
            api_key=api_key,
            model_id=model_id,
            custom_headers=custom_headers
        )

        if res.get("success"):
            self.status_label.setText("<span style='color:#10b981;'>✓ " + res.get("message", "Connected Successfully!") + "</span>")
        else:
            self.status_label.setText("<span style='color:#ef4444;'>❌ " + res.get("error", "Connection Failed") + "</span>")

    def _save_model(self):
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
            QMessageBox.warning(self, "Missing URL", "Please enter a valid base URL or webhook endpoint.")
            return

        custom_headers = {}
        h_text = self.headers_edit.text().strip()
        if h_text:
            try:
                custom_headers = json.loads(h_text)
            except Exception as e:
                QMessageBox.warning(self, "Invalid Headers", f"Custom headers must be valid JSON: {e}")
                return

        set_active = self.chk_set_active.isChecked()

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

        self.status_label.setText(f"<span style='color:#10b981;'>✓ Added '{model_id}' successfully!</span>")
        self._load_registered_models()

        if set_active:
            QMessageBox.information(
                self,
                "Model Activated",
                f"Model '{model_id}' ({p_name}) has been saved and set as the active model for LMMs!"
            )

    def _load_registered_models(self):
        models = OnlineModelRegistry.list_models(safe=True)
        active_type = OnlineModelRegistry.get_active_type()
        active_model = OnlineModelRegistry.get_active_model()
        active_key = active_model.get("key") if active_model else None

        if active_type == "online" and active_model:
            self.lbl_active_info.setText(f"Active: [Online] {active_model.get('name')}")
        else:
            self.lbl_active_info.setText("Active: [Offline Engine]")

        self.models_table.setRowCount(len(models))

        for row, m in enumerate(models):
            is_active = (m.get("key") == active_key and active_type == "online")

            status_item = QTableWidgetItem("● ACTIVE" if is_active else "○ INACTIVE")
            status_item.setForeground(QColor("#10b981" if is_active else "#64748b"))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.models_table.setItem(row, 0, status_item)

            prov_item = QTableWidgetItem(m.get("provider_name", ""))
            self.models_table.setItem(row, 1, prov_item)

            id_item = QTableWidgetItem(m.get("id", ""))
            id_item.setFont(QFont("Monospace", 10))
            self.models_table.setItem(row, 2, id_item)

            url_item = QTableWidgetItem(m.get("base_url", ""))
            self.models_table.setItem(row, 3, url_item)

            key_item = QTableWidgetItem(m.get("api_key_masked", "Configured"))
            key_item.setForeground(QColor("#94a3b8"))
            self.models_table.setItem(row, 4, key_item)

            # Action buttons cell
            btn_frame = QWidget()
            btn_layout = QHBoxLayout(btn_frame)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)

            m_key = m.get("key")

            btn_set = QPushButton("Set Active")
            btn_set.setObjectName("secondaryBtn")
            btn_set.setStyleSheet("padding: 4px 8px; font-size: 11px;")
            btn_set.clicked.connect(lambda _, k=m_key: self._set_model_active(k))
            btn_layout.addWidget(btn_set)

            btn_del = QPushButton("Delete")
            btn_del.setObjectName("dangerBtn")
            btn_del.setStyleSheet("padding: 4px 8px; font-size: 11px;")
            btn_del.clicked.connect(lambda _, k=m_key: self._delete_model(k))
            btn_layout.addWidget(btn_del)

            self.models_table.setCellWidget(row, 5, btn_frame)

    def _set_model_active(self, key: str):
        OnlineModelRegistry.set_active_model(key, "online")
        self._load_registered_models()

    def _delete_model(self, key: str):
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete configured model '{key}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            OnlineModelRegistry.remove_model(key)
            self._load_registered_models()


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
