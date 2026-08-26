from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
    QStackedWidget, QWidget, QLabel, QPushButton, QFormLayout, QLineEdit
)
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LMMs Settings")
        self.resize(800, 600)
        self.setStyleSheet("background-color: #0e1116; color: #e5e7eb;")

        main_layout = QHBoxLayout(self)
        
        # Left sidebar for navigation
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        self.nav_list.setStyleSheet("""
            QListWidget { border: none; background-color: #0d1117; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #21262d; }
            QListWidget::item:selected { background-color: #1f6feb; color: white; }
        """)
        
        categories = [
            "Providers", "APIs", "Memory", "Context", 
            "Workspace", "Theme", "Server", "Keyboard Shortcuts"
        ]
        self.nav_list.addItems(categories)
        self.nav_list.currentRowChanged.connect(self.change_page)

        # Right content area
        self.content_area = QStackedWidget()
        self.content_area.setStyleSheet("background-color: #0e1116; border: none;")

        # Setup functional form elements
        self.inputs = {}
        from lmms.backend.services.workspace_service import WorkspaceService
        state = WorkspaceService.load_workspace_state()

        for cat in categories:
            page = QWidget()
            layout = QVBoxLayout(page)
            title = QLabel(f"{cat} Settings")
            title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 20px;")
            layout.addWidget(title)
            
            if cat == "Providers":
                from lmms.gui.widgets.provider_settings import ProviderSettingsWidget
                self.provider_widget = ProviderSettingsWidget(self)
                layout.addWidget(self.provider_widget)
            else:
                form = QFormLayout()
                if cat == "APIs":
                    self.inputs["openai_key"] = QLineEdit(state.get("openai_key", ""))
                    self.inputs["anthropic_key"] = QLineEdit(state.get("anthropic_key", ""))
                    form.addRow("OpenAI API Key:", self.inputs["openai_key"])
                    form.addRow("Anthropic API Key:", self.inputs["anthropic_key"])
                elif cat == "Server":
                    self.inputs["host"] = QLineEdit(state.get("host", "127.0.0.1"))
                    self.inputs["port"] = QLineEdit(state.get("port", "11434"))
                    form.addRow("Host:", self.inputs["host"])
                    form.addRow("Port:", self.inputs["port"])
                elif cat == "Workspace":
                    self.inputs["auto_save"] = QLineEdit(str(state.get("auto_save", "True")))
                    form.addRow("Auto Save:", self.inputs["auto_save"])
                layout.addLayout(form)
            layout.addStretch()
            self.content_area.addWidget(page)

        # Buttons
        button_layout = QVBoxLayout()
        close_btn = QPushButton("Save & Close")
        close_btn.setStyleSheet("padding: 8px; background-color: #21262d; border: 1px solid #30363d; border-radius: 4px;")
        close_btn.clicked.connect(self.save_and_close)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        # Add to main layout
        main_layout.addWidget(self.nav_list)
        main_layout.addWidget(self.content_area)
        main_layout.addLayout(button_layout)
        
        # Select first item
        self.nav_list.setCurrentRow(0)

    def change_page(self, index):
        self.content_area.setCurrentIndex(index)

    def save_and_close(self):
        from lmms.backend.services.workspace_service import WorkspaceService
        state = WorkspaceService.load_workspace_state()
        for key, field in self.inputs.items():
            state[key] = field.text()
        WorkspaceService.save_workspace_state(state)
        self.accept()
