# Made by markanm
import os
import functools
from PyQt6.QtCore import Qt, QUrl, QObject, pyqtSlot, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebChannel import QWebChannel


# ── Singleton LSP Manager ──────────────────────────────────────────────────────
# One pylsp process shared across ALL open editor tabs.

_lsp_singleton = None

def _get_lsp():
    global _lsp_singleton
    if _lsp_singleton is None:
        from lmms.gui.utils.lsp_manager import LSPManager
        cmd = _detect_lsp_command()
        _lsp_singleton = LSPManager(cmd)
        _lsp_singleton.start()
        print(f"[LSP] Started singleton: {' '.join(cmd)}")
    return _lsp_singleton


def _detect_lsp_command():
    """Return the best available LSP server command."""
    import shutil
    if shutil.which("pylsp"):
        return ["pylsp"]
    if shutil.which("pyright-langserver"):
        return ["pyright-langserver", "--stdio"]
    if shutil.which("basedpyright-langserver"):
        return ["basedpyright-langserver", "--stdio"]
    print("[LSP] Warning: no Python LSP found (install python-lsp-server). LSP disabled.")
    return []


# ── Git decoration cache ────────────────────────────────────────────────────────
# GitManager is heavy (git.Repo). Cache one per repo root.

_git_cache: dict = {}

def _get_git_manager(repo_path: str):
    if repo_path not in _git_cache:
        from lmms.gui.utils.git_manager import GitManager
        _git_cache[repo_path] = GitManager(repo_path)
    return _git_cache[repo_path]


def _find_repo_root(file_path: str) -> str | None:
    """Walk up from file_path to find nearest .git directory."""
    d = os.path.dirname(os.path.abspath(file_path))
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


# ── Python ↔ JS bridge ────────────────────────────────────────────────────────

class PythonBridge(QObject):
    contentChanged      = pyqtSignal(str)
    editorReady         = pyqtSignal()
    setContent          = pyqtSignal(str, str)   # content, language
    sendLspMessage      = pyqtSignal(str)         # LSP response → JS
    lspMessageFromJs    = pyqtSignal(str)         # LSP request ← JS
    updateGitDecorations = pyqtSignal(str)        # git gutter data → JS
    registerExtension   = pyqtSignal(str)         # manifest string → JS

    @pyqtSlot(str)
    def onContentChanged(self, content: str):
        self.contentChanged.emit(content)

    @pyqtSlot()
    def onEditorReady(self):
        self.editorReady.emit()

    @pyqtSlot(str)
    def onLspMessage(self, message: str):
        self.lspMessageFromJs.emit(message)


# ── Monaco-based CodeEditor ────────────────────────────────────────────────────

class CodeEditor(QWebEngineView):
    textChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Bridge + WebChannel
        self.bridge = PythonBridge()
        self.channel = QWebChannel()
        self.channel.registerObject("pythonBridge", self.bridge)
        self.page().setWebChannel(self.channel)

        # Wire to the SHARED LSP singleton
        lsp = _get_lsp()
        if lsp and lsp.command:
            # JS → Python → LSP process
            self.bridge.lspMessageFromJs.connect(lsp.sendMessage)
            # LSP process → Python → JS  (broadcast to all tabs; client ignores
            # responses for requests it didn't send — standard JSON-RPC behaviour)
            lsp.messageReceived.connect(self.bridge.sendLspMessage)

        # Bridge signals
        self.bridge.contentChanged.connect(self._on_content_changed)
        self.bridge.editorReady.connect(self._on_editor_ready)

        self._current_content = ""
        self._pending_content = ""
        self._pending_language = ""
        self._is_ready = False

        # Debounce timer for git decorations (don't call git on every keystroke)
        self._git_timer = QTimer(self)
        self._git_timer.setSingleShot(True)
        self._git_timer.setInterval(800)  # 800 ms after last keystroke
        self._git_timer.timeout.connect(self._compute_git_decorations)

        # Background colour while loading
        self.setStyleSheet("background-color: #0d1117; border: none;")
        self.page().setBackgroundColor(QColor("#0d1117"))

        # Load Monaco dist
        dist_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "monaco_build", "dist", "index.html"
        )
        if os.path.exists(dist_path):
            self.setUrl(QUrl.fromLocalFile(dist_path))
        else:
            print(f"[CodeEditor] Warning: Monaco build not found at {dist_path}")

    # ── content management ────────────────────────────────────────────────────

    def _on_editor_ready(self):
        self._is_ready = True
        if self._pending_content:
            self._push_content(self._pending_content, self._pending_language)
            self._pending_content = ""
            self._pending_language = ""

    def _push_content(self, content: str, language: str):
        self.bridge.setContent.emit(content, language)

    def _on_content_changed(self, content: str):
        self._current_content = content
        self.textChanged.emit()
        # Restart the debounce timer
        self._git_timer.start()

    def load_file(self, file_path: str, content: str, disable_highlighting=False):
        self.setProperty("file_path", file_path)
        self._current_content = content

        ext = os.path.splitext(file_path)[1].lower()
        lang_map = {
            ".py":   "python",
            ".json": "json",
            ".js":   "javascript",
            ".jsx":  "javascript",
            ".ts":   "typescript",
            ".tsx":  "typescript",
            ".html": "html",
            ".htm":  "html",
            ".css":  "css",
            ".scss": "scss",
            ".md":   "markdown",
            ".yaml": "yaml",
            ".yml":  "yaml",
            ".sh":   "shell",
            ".bash": "shell",
            ".rs":   "rust",
            ".go":   "go",
            ".c":    "c",
            ".cpp":  "cpp",
            ".h":    "cpp",
            ".java": "java",
        }
        language = "plaintext" if disable_highlighting else lang_map.get(ext, "plaintext")

        if self._is_ready:
            self._push_content(content, language)
        else:
            self._pending_content = content
            self._pending_language = language

    # ── git gutter decorations ────────────────────────────────────────────────

    def _compute_git_decorations(self):
        file_path = self.property("file_path")
        if not file_path:
            return
        try:
            import json
            repo_root = _find_repo_root(file_path)
            if not repo_root:
                return
            manager = _get_git_manager(repo_root)
            decs = manager.compute_decorations(file_path, self._current_content)
            if decs is not None:
                self.bridge.updateGitDecorations.emit(json.dumps(decs))
        except Exception as e:
            pass  # Silently ignore — not critical

    # ── compatibility ─────────────────────────────────────────────────────────

    def toPlainText(self) -> str:
        return self._current_content

    def cleanup(self):
        """Called when the tab is closed."""
        self._git_timer.stop()
        lsp = _get_lsp()
        if lsp and lsp.command:
            try:
                lsp.messageReceived.disconnect(self.bridge.sendLspMessage)
                self.bridge.lspMessageFromJs.disconnect(lsp.sendMessage)
            except TypeError:
                pass
