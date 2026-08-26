import os
from PyQt6.QtCore import Qt, QUrl, QObject, pyqtSlot, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

class PythonBridge(QObject):
    contentChanged = pyqtSignal(str)
    editorReady = pyqtSignal()
    setContent = pyqtSignal(str, str) # content, language
    sendLspMessage = pyqtSignal(str) # Send to JS
    lspMessageFromJs = pyqtSignal(str) # Receive from JS

    @pyqtSlot(str)
    def onContentChanged(self, content):
        self.contentChanged.emit(content)
        
    @pyqtSlot()
    def onEditorReady(self):
        self.editorReady.emit()
        
    @pyqtSlot(str)
    def onLspMessage(self, message):
        self.lspMessageFromJs.emit(message)

from lmms.gui.utils.lsp_manager import LSPManager

class CodeEditor(QWebEngineView):
    textChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.bridge = PythonBridge()
        self.channel = QWebChannel()
        self.channel.registerObject("pythonBridge", self.bridge)
        self.page().setWebChannel(self.channel)
        
        self.lsp = LSPManager(["pylsp"])
        self.bridge.lspMessageFromJs.connect(self.lsp.sendMessage)
        self.lsp.messageReceived.connect(self.bridge.sendLspMessage)
        self.lsp.start()
        
        # Connect bridge signals
        self.bridge.contentChanged.connect(self._on_content_changed)
        self.bridge.editorReady.connect(self._on_editor_ready)
        
        self._current_content = ""
        self._pending_content = ""
        self._pending_language = ""
        self._is_ready = False
        
        # Background color to match LMMs theme while loading
        self.setStyleSheet("background-color: #0d1117; border: none;")
        
        # Load the index.html from dist
        dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "monaco_build", "dist", "index.html")
        if os.path.exists(dist_path):
            self.setUrl(QUrl.fromLocalFile(dist_path))
        else:
            print(f"Warning: Monaco build not found at {dist_path}")
        
    def _on_editor_ready(self):
        self._is_ready = True
        if self._pending_content:
            self._set_content_in_js(self._pending_content, self._pending_language)
            
    def _set_content_in_js(self, content, language):
        # We encode it safely by emitting the signal which PyWebChannel transports safely
        self.bridge.setContent.emit(content, language)

    def _on_content_changed(self, content):
        self._current_content = content
        self.textChanged.emit()
        
    def load_file(self, file_path, content, disable_highlighting=False):
        self.setProperty("file_path", file_path)
        self._current_content = content
        
        # Basic mapping to Monaco language IDs
        ext = os.path.splitext(file_path)[1].lower()
        language = "plaintext"
        if ext == ".py": language = "python"
        elif ext == ".json": language = "json"
        elif ext in [".js", ".jsx"]: language = "javascript"
        elif ext in [".ts", ".tsx"]: language = "typescript"
        elif ext in [".html", ".htm"]: language = "html"
        elif ext == ".css": language = "css"
        elif ext == ".md": language = "markdown"
        
        if self._is_ready:
            self._set_content_in_js(content, language)
        else:
            self._pending_content = content
            self._pending_language = language

    def toPlainText(self):
        return self._current_content
