from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer

class NotificationManager(QWidget):
    """
    Centralized notification toaster for the GUI.
    Listens to EventManager indirectly through StateManager.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        
    def show_notification(self, title: str, message: str, duration_ms: int = 3000):
        # Placeholder for a real toaster popup
        label = QLabel(f"<b>{title}</b>: {message}")
        label.setStyleSheet("background-color: #333; color: white; padding: 10px; border-radius: 5px;")
        self.layout.addWidget(label)
        
        QTimer.singleShot(duration_ms, label.deleteLater)
