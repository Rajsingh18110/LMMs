from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, 
    QComboBox, QPushButton, QLabel
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QTextCharFormat

class ExtensionHostLogsPanel(QWidget):
    """
    Panel to view stdout/stderr from Extension Hosts (Node.js).
    Groups logs by extension ID.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ExtensionHostLogsPanel")
        self._logs: dict[str, list[tuple[str, str]]] = {}  # ext_id -> [(level, msg)]
        self._current_ext_id = "All Extensions"
        
        self.setStyleSheet("""
            QWidget#ExtensionHostLogsPanel {
                background-color: #1e1e1e;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #3c3c3c;
                border-radius: 2px;
                padding: 4px;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: #cccccc;
                border: none;
                border-radius: 2px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        
        self._build_ui()
        
        # Subscribe to ExtensionManager logs
        from lmms.extensions.manager import ExtensionManager
        ExtensionManager.instance().log_emitted.connect(self._on_log_emitted)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Header toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel("Extension Logs:")
        lbl.setStyleSheet("color: #cccccc;")
        toolbar.addWidget(lbl)
        
        self.ext_combo = QComboBox()
        self.ext_combo.addItem("All Extensions")
        self.ext_combo.currentTextChanged.connect(self._on_ext_changed)
        toolbar.addWidget(self.ext_combo, 1)
        
        clear_btn = QPushButton("Clear")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_logs)
        toolbar.addWidget(clear_btn)
        
        layout.addLayout(toolbar)
        
        # Text view
        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #3c3c3c;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 12px;
            }
        """)
        
        # Setup text formats for different log levels
        self.fmt_info = QTextCharFormat()
        self.fmt_info.setForeground(QColor("#cccccc"))
        
        self.fmt_warn = QTextCharFormat()
        self.fmt_warn.setForeground(QColor("#cca700"))
        
        self.fmt_error = QTextCharFormat()
        self.fmt_error.setForeground(QColor("#f48771"))
        
        layout.addWidget(self.text_view)
        
    @pyqtSlot(str, str, str)
    def _on_log_emitted(self, ext_id: str, level: str, msg: str):
        if ext_id not in self._logs:
            self._logs[ext_id] = []
            self.ext_combo.addItem(ext_id)
            
        self._logs[ext_id].append((level, msg))
        
        if self._current_ext_id in ("All Extensions", ext_id):
            self._append_text(ext_id, level, msg)

    def _on_ext_changed(self, ext_id: str):
        self._current_ext_id = ext_id
        self._refresh_view()
        
    def _refresh_view(self):
        self.text_view.clear()
        if self._current_ext_id == "All Extensions":
            for ext_id, logs in self._logs.items():
                for level, msg in logs:
                    self._append_text(ext_id, level, msg)
        elif self._current_ext_id in self._logs:
            for level, msg in self._logs[self._current_ext_id]:
                self._append_text(self._current_ext_id, level, msg)
                
    def _append_text(self, ext_id: str, level: str, msg: str):
        cursor = self.text_view.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        
        if level == "error":
            cursor.setCharFormat(self.fmt_error)
        elif level == "warn":
            cursor.setCharFormat(self.fmt_warn)
        else:
            cursor.setCharFormat(self.fmt_info)
            
        prefix = f"[{ext_id}] " if self._current_ext_id == "All Extensions" else ""
        cursor.insertText(f"{prefix}{msg}\n")
        
        # Scroll to bottom
        sb = self.text_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _clear_logs(self):
        if self._current_ext_id == "All Extensions":
            self._logs.clear()
            self.ext_combo.clear()
            self.ext_combo.addItem("All Extensions")
        else:
            self._logs[self._current_ext_id] = []
            
        self._refresh_view()
