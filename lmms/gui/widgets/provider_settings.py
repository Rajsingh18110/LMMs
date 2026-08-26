from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
    QPushButton, QLabel, QDialog, QFormLayout, QLineEdit, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt
from lmms.backend.core.registry.provider_registry import ProviderRegistry

class ProviderDialog(QDialog):
    def __init__(self, parent=None, provider_id=None):
        super().__init__(parent)
        self.provider_id = provider_id
        self.setWindowTitle("Add Provider" if not provider_id else "Edit Provider")
        self.setMinimumWidth(400)
        self.setStyleSheet("background-color: #0e1116; color: #e5e7eb;")
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["openai_compatible", "ollama", "llama_cpp"])
        self.base_url_input = QLineEdit()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.webhook_input = QLineEdit()
        
        form.addRow("Name:", self.name_input)
        form.addRow("Type:", self.type_combo)
        form.addRow("Base URL:", self.base_url_input)
        form.addRow("API Key:", self.api_key_input)
        form.addRow("Webhook URL:", self.webhook_input)
        layout.addLayout(form)
        
        # If editing, prefill
        if self.provider_id:
            provider = ProviderRegistry.get_safe(self.provider_id)
            if provider:
                self.name_input.setText(provider.get("name", ""))
                index = self.type_combo.findText(provider.get("type", ""))
                if index >= 0:
                    self.type_combo.setCurrentIndex(index)
                self.base_url_input.setText(provider.get("base_url", ""))
                # DO NOT show real API key, show masked one
                self.api_key_input.setText(provider.get("api_key", ""))
                self.webhook_input.setText(provider.get("webhook_url", ""))
                
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
    def save(self):
        name = self.name_input.text().strip()
        p_type = self.type_combo.currentText()
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
                "base_url": base_url,
                "webhook_url": webhook_url
            }
            # Only update API key if user typed something new (and not the masked text)
            if api_key and not api_key.startswith(api_key[:4] + "••••••••"):
                updates["api_key"] = api_key
            ProviderRegistry.update(self.provider_id, updates)
        else:
            ProviderRegistry.create(name, p_type, base_url, api_key, webhook_url)
            
        self.accept()


class ProviderSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: #0d1117; border: 1px solid #30363d; border-radius: 4px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #21262d; }
            QListWidget::item:selected { background-color: #1f6feb; color: white; }
        """)
        self.layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Provider")
        edit_btn = QPushButton("Edit")
        del_btn = QPushButton("Delete")
        
        add_btn.clicked.connect(self.add_provider)
        edit_btn.clicked.connect(self.edit_provider)
        del_btn.clicked.connect(self.delete_provider)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        
        self.layout.addLayout(btn_layout)
        self.refresh_list()
        
    def refresh_list(self):
        self.list_widget.clear()
        providers = ProviderRegistry.list_safe()
        for p in providers:
            item = QListWidgetItem(f"{p['name']} ({p['type']}) - {p['base_url']}")
            item.setData(Qt.ItemDataRole.UserRole, p["id"])
            self.list_widget.addItem(item)
            
    def add_provider(self):
        dlg = ProviderDialog(self)
        if dlg.exec():
            self.refresh_list()
            
    def edit_provider(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            return
        p_id = selected[0].data(Qt.ItemDataRole.UserRole)
        dlg = ProviderDialog(self, p_id)
        if dlg.exec():
            self.refresh_list()
            
    def delete_provider(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            return
        p_id = selected[0].data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this provider?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            ProviderRegistry.delete(p_id)
            self.refresh_list()
