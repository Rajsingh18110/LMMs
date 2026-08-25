from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import Qt

class ChatInputEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.send_callback = None
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            if self.send_callback:
                self.send_callback()
            event.accept()
        else:
            super().keyPressEvent(event)
