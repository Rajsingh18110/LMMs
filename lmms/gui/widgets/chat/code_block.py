from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextBrowser, QApplication
from PyQt6.QtCore import Qt, QTimer
import html

class CodeBlockWidget(QWidget):
    def __init__(self, code: str, language: str = ""):
        super().__init__()
        self.code = code
        self.language = language
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header (Language + Copy Button)
        header = QWidget()
        header.setStyleSheet("background-color: #21262d; border-top-left-radius: 6px; border-top-right-radius: 6px; border: 1px solid #30363d; border-bottom: none;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 4, 10, 4)
        
        lang_label = QLabel(self.language.upper() if self.language else "CODE")
        lang_label.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: bold;")
        
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #58a6ff;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { color: #79c0ff; }
        """)
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        
        header_layout.addWidget(lang_label)
        header_layout.addStretch()
        header_layout.addWidget(self.copy_btn)
        
        # Code Area
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        # Disable frame and set monospace font
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #0d1117;
                color: #c9d1d9;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
                border: 1px solid #30363d;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                padding: 10px;
            }
        """)
        
        # Simple rendering for now (can integrate a syntax highlighter later)
        escaped_code = html.escape(self.code)
        self.text_browser.setHtml(f"<pre style='margin:0;'>{escaped_code}</pre>")
        
        # Dynamically size the browser based on lines
        lines = self.code.count('\\n') + 1
        height = max(40, min(lines * 20 + 25, 400))
        self.text_browser.setMinimumHeight(height)
        self.text_browser.setMaximumHeight(height)
        
        layout.addWidget(header)
        layout.addWidget(self.text_browser)

    def copy_to_clipboard(self):
        QApplication.clipboard().setText(self.code)
        self.copy_btn.setText("Copied!")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #3fb950;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        QTimer.singleShot(2000, self.reset_copy_btn)
        
    def reset_copy_btn(self):
        self.copy_btn.setText("Copy")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #58a6ff;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { color: #79c0ff; }
        """)
