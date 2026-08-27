from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
    QPushButton, QLabel, QFormLayout, QLineEdit, QComboBox, QMessageBox,
    QStackedWidget, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from lmms.backend.core.registry.provider_registry import ProviderRegistry

class ProviderItemWidget(QWidget):
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    toggle_requested = pyqtSignal(str, bool)
    
    def __init__(self, provider, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.p_id = provider["id"]
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        info_layout = QVBoxLayout()
        category = provider.get('category', 'text')
        name_lbl = QLabel(f"<b>{provider['name']}</b> ({provider['type']} - {category})")
        
        is_enabled = provider.get("enabled", True)
        if not is_enabled:
            name_lbl.setStyleSheet("color: #8b949e; font-size: 14px; text-decoration: line-through;")
        else:
            name_lbl.setStyleSheet("color: #e6edf3; font-size: 14px;")
            
        url_lbl = QLabel(provider.get('base_url', ''))
        url_lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(url_lbl)
        
        layout.addLayout(info_layout, 1)
        
        # Buttons
        self.toggle_btn = QPushButton("Disable" if is_enabled else "Enable")
        self.toggle_btn.clicked.connect(self.on_toggle)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.p_id))
        self.del_btn = QPushButton("Delete")
        self.del_btn.clicked.connect(self.show_confirm)
        
        btn_style = """
            QPushButton { background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px; padding: 4px 10px; font-weight: 500;}
            QPushButton:hover { background-color: #30363d; }
        """
        danger_btn_style = """
            QPushButton { background-color: #da3633; color: #ffffff; border: 1px solid #f85149; border-radius: 4px; padding: 4px 10px; font-weight: 500;}
            QPushButton:hover { background-color: #f85149; }
        """
        
        self.toggle_btn.setStyleSheet(btn_style)
        self.edit_btn.setStyleSheet(btn_style)
        self.del_btn.setStyleSheet(danger_btn_style)
        
        self.btn_layout = QHBoxLayout()
        self.btn_layout.addWidget(self.toggle_btn)
        self.btn_layout.addWidget(self.edit_btn)
        self.btn_layout.addWidget(self.del_btn)
        layout.addLayout(self.btn_layout)

        # Inline Confirm Delete
        self.confirm_widget = QWidget()
        conf_layout = QHBoxLayout(self.confirm_widget)
        conf_layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Delete?")
        lbl.setStyleSheet("color: #e5e7eb; font-weight: bold;")
        yes_btn = QPushButton("Yes")
        no_btn = QPushButton("No")
        yes_btn.setStyleSheet(danger_btn_style)
        no_btn.setStyleSheet(btn_style)
        yes_btn.clicked.connect(lambda: self.delete_requested.emit(self.p_id))
        no_btn.clicked.connect(self.hide_confirm)
        conf_layout.addWidget(lbl)
        conf_layout.addWidget(yes_btn)
        conf_layout.addWidget(no_btn)
        self.confirm_widget.hide()
        layout.addWidget(self.confirm_widget)
        
    def on_toggle(self):
        is_enabled = self.provider.get("enabled", True)
        self.toggle_requested.emit(self.p_id, not is_enabled)

    def show_confirm(self):
        self.toggle_btn.hide()
        self.edit_btn.hide()
        self.del_btn.hide()
        self.confirm_widget.show()
        
    def hide_confirm(self):
        self.confirm_widget.hide()
        self.toggle_btn.show()
        self.edit_btn.show()
        self.del_btn.show()


class ProviderFormWidget(QWidget):
    saved = pyqtSignal()
    cancelled = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.provider_id = None
        
        layout = QVBoxLayout(self)
        self.title_lbl = QLabel("Add Provider")
        self.title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #e5e7eb; margin-bottom: 10px;")
        layout.addWidget(self.title_lbl)
        
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["openai_compatible", "ollama", "llama_cpp"])
        
        self.category_combo = QComboBox()
        self.category_combo.addItems(["text", "image", "audio", "video", "multimodal"])
        
        self.base_url_input = QLineEdit()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.webhook_input = QLineEdit()
        
        input_style = "QLineEdit { background-color: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 6px; }"
        self.name_input.setStyleSheet(input_style)
        self.base_url_input.setStyleSheet(input_style)
        self.api_key_input.setStyleSheet(input_style)
        self.webhook_input.setStyleSheet(input_style)
        self.type_combo.setStyleSheet("QComboBox { background-color: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 6px; }")
        self.category_combo.setStyleSheet("QComboBox { background-color: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 6px; }")
        
        self.eye_btn = QPushButton("👁")
        self.eye_btn.setFixedSize(28, 28)
        self.eye_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.eye_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; font-size: 16px; color: #c9d1d9; } QPushButton:hover { color: #58a6ff; }")
        self.eye_btn.clicked.connect(self.toggle_api_key_visibility)
        
        api_key_layout = QHBoxLayout()
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        api_key_layout.addWidget(self.api_key_input)
        api_key_layout.addWidget(self.eye_btn)
        
        form.addRow("Name:", self.name_input)
        form.addRow("Type:", self.type_combo)
        form.addRow("Category:", self.category_combo)
        form.addRow("Base URL:", self.base_url_input)
        form.addRow("API Key:", api_key_layout)
        form.addRow("Webhook URL:", self.webhook_input)
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Provider")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.cancelled.emit)
        
        btn_style = """
            QPushButton { background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 6px 16px; font-weight: 500;}
            QPushButton:hover { background-color: #30363d; }
        """
        primary_btn_style = """
            QPushButton { background-color: #238636; color: #ffffff; border: 1px solid #2ea043; border-radius: 6px; padding: 6px 16px; font-weight: 600;}
            QPushButton:hover { background-color: #2ea043; }
        """
        save_btn.setStyleSheet(primary_btn_style)
        cancel_btn.setStyleSheet(btn_style)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)
        layout.addStretch(1)
        
    def toggle_api_key_visibility(self):
        if self.api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.eye_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; font-size: 16px; color: #58a6ff; }")
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.eye_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; font-size: 16px; color: #c9d1d9; } QPushButton:hover { color: #58a6ff; }")
            
    def load_provider(self, provider_id=None):
        self.provider_id = provider_id
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.eye_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; font-size: 16px; color: #c9d1d9; } QPushButton:hover { color: #58a6ff; }")
        
        if self.provider_id:
            self.title_lbl.setText("Edit Provider")
            # Use get() instead of get_safe() to reveal actual key in edit field
            provider = ProviderRegistry.get(self.provider_id)
            if provider:
                self.name_input.setText(provider.get("name", ""))
                index = self.type_combo.findText(provider.get("type", ""))
                if index >= 0:
                    self.type_combo.setCurrentIndex(index)
                cat_index = self.category_combo.findText(provider.get("category", "text"))
                if cat_index >= 0:
                    self.category_combo.setCurrentIndex(cat_index)
                self.base_url_input.setText(provider.get("base_url", ""))
                self.api_key_input.setText(provider.get("api_key", ""))
                self.api_key_input.setPlaceholderText("")
                self.webhook_input.setText(provider.get("webhook_url", ""))
        else:
            self.title_lbl.setText("Add Provider")
            self.name_input.setText("")
            self.type_combo.setCurrentIndex(0)
            self.category_combo.setCurrentIndex(0)
            self.base_url_input.setText("")
            self.api_key_input.setText("")
            self.api_key_input.setPlaceholderText("")
            self.webhook_input.setText("")
            
    def save(self):
        name = self.name_input.text().strip()
        p_type = self.type_combo.currentText()
        category = self.category_combo.currentText()
        base_url = self.base_url_input.text().strip()
        api_key = self.api_key_input.text().strip()
        webhook_url = self.webhook_input.text().strip()
        
        if not name or not p_type:
            QMessageBox.warning(self, "Validation Error", "Name and Type are required.")
            return
            
        if self.provider_id:
            updates = {
                "name": name,
                "type": p_type,
                "category": category,
                "base_url": base_url,
                "webhook_url": webhook_url,
                "api_key": api_key
            }
            ProviderRegistry.update(self.provider_id, updates)
        else:
            ProviderRegistry.create(name, p_type, base_url, api_key, webhook_url, category)
            
        self.saved.emit()


class ProviderSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)
        
        # --- List Page ---
        self.list_page = QWidget()
        list_layout = QVBoxLayout(self.list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: #010409; border: 1px solid #30363d; border-radius: 6px; font-size: 14px;}
            QListWidget::item { border-bottom: 1px solid #21262d; }
            QListWidget::item:selected { background-color: transparent; }
        """)
        list_layout.addWidget(self.list_widget)
        
        add_btn = QPushButton("Add Provider")
        add_btn.setStyleSheet("""
            QPushButton { background-color: #238636; color: #ffffff; border: 1px solid #2ea043; border-radius: 6px; padding: 8px 16px; font-weight: 600;}
            QPushButton:hover { background-color: #2ea043; }
        """)
        add_btn.clicked.connect(self.show_add_form)
        list_layout.addWidget(add_btn)
        
        # --- Form Page ---
        self.form_page = ProviderFormWidget()
        self.form_page.saved.connect(self.on_form_saved)
        self.form_page.cancelled.connect(self.on_form_cancelled)
        
        self.stacked_widget.addWidget(self.list_page)
        self.stacked_widget.addWidget(self.form_page)
        
        self.refresh_list()
        
    def refresh_list(self):
        self.list_widget.clear()
        providers = ProviderRegistry.list_safe()
        for p in providers:
            item = QListWidgetItem()
            item_widget = ProviderItemWidget(p)
            item_widget.edit_requested.connect(self.show_edit_form)
            item_widget.delete_requested.connect(self.delete_provider)
            item_widget.toggle_requested.connect(self.toggle_provider)
            
            # Using hint from widget size
            item.setSizeHint(item_widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, item_widget)
            
    def show_add_form(self):
        self.form_page.load_provider(None)
        self.stacked_widget.setCurrentWidget(self.form_page)
        
    def show_edit_form(self, p_id):
        self.form_page.load_provider(p_id)
        self.stacked_widget.setCurrentWidget(self.form_page)
        
    def on_form_saved(self):
        self.refresh_list()
        self.stacked_widget.setCurrentWidget(self.list_page)
        
    def on_form_cancelled(self):
        self.stacked_widget.setCurrentWidget(self.list_page)
        
    def delete_provider(self, p_id):
        ProviderRegistry.delete(p_id)
        self.refresh_list()
            
    def toggle_provider(self, p_id, enable: bool):
        if enable:
            ProviderRegistry.enable(p_id)
        else:
            ProviderRegistry.disable(p_id)
        self.refresh_list()
