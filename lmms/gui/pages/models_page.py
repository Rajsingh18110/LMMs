from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget
from lmms.backend.models.__init__ import ModelManager

class ModelsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.models_manager = ModelManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("🧠 Local Models")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 10px;
                font-size: 16px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #30363d;
            }
            QListWidget::item:hover {
                background-color: #21262d;
            }
        """)
        
        # Load local models
        try:
            from lmms.backend.logic.manager import backend_manager
            registry = backend_manager.registry.load_registry()
            if not registry:
                self.list_widget.addItem("No models found locally. Use 'lmms pull <model>'")
            for model_id, details in registry.items():
                self.list_widget.addItem(f"📦 {model_id}   |   Format: {details.get('format', 'GGUF')}")
        except Exception as e:
            self.list_widget.addItem(f"Error loading models: {e}")
            
        layout.addWidget(self.list_widget)
