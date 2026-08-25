from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import Qt, pyqtSignal

class ChatInputEdit(QTextEdit):
    files_pasted = pyqtSignal(list)

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
