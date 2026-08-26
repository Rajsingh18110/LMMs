from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import Qt, pyqtSignal

class ChatInputEdit(QTextEdit):
    files_pasted = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.send_callback = None
        self.setAcceptDrops(True)
        self._default_style = ""
        self._drag_style = "border: 2px dashed #58a6ff; background: #1f2937;"

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            if self.send_callback:
                self.send_callback()
            event.accept()
        else:
            super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._default_style = self.styleSheet()
            self.setStyleSheet(self._default_style + self._drag_style)
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self._default_style)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.setStyleSheet(self._default_style)
        paths = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    paths.append(url.toLocalFile())
            
            if paths:
                self.files_pasted.emit(paths)
                event.acceptProposedAction()
                return
        
        super().dropEvent(event)

    def insertFromMimeData(self, source):
        paths = []

        if source.hasUrls():
            for url in source.urls():
                if url.isLocalFile():
                    paths.append(url.toLocalFile())

        if source.hasImage():
            import os
            import uuid

            image = source.imageData()
            if image and not image.isNull():
                paste_dir = os.path.join("/tmp", "lmms-pasted-images")
                os.makedirs(paste_dir, exist_ok=True)
                path = os.path.join(paste_dir, f"paste-{uuid.uuid4().hex}.png")
                if image.save(path, "PNG"):
                    paths.append(path)

        if paths:
            self.files_pasted.emit(paths)

        if source.hasText():
            super().insertFromMimeData(source)
