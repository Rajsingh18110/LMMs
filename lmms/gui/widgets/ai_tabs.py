from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QLabel, QSplitter, QTextEdit
from PyQt6.QtCore import Qt

class CanvasTab(QWidget):
    """
    A custom canvas tab for the AI model to create graph presentations
    or other visual elements.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0d1117; color: #c9d1d9;")
        layout = QVBoxLayout(self)
        
        self.canvas_label = QLabel("Canvas Area\nWaiting for AI model rendering...")
        self.canvas_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas_label.setStyleSheet("color: #8b949e; font-size: 16px; border: 2px dashed #30363d;")
        
        layout.addWidget(self.canvas_label)

    def set_content(self, html_or_text):
        """Update canvas content"""
        self.canvas_label.setText(html_or_text)


class MarkdownTab(QWidget):
    """
    A general purpose tab for rendering markdown content.
    Used for Implementation Plan, Tasks, and Walkthroughs.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0d1117; color: #c9d1d9;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.browser = QTextBrowser()
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: #0d1117;
                color: #c9d1d9;
                border: none;
                padding: 20px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
            }
        """)
        self.browser.setOpenExternalLinks(True)
        layout.addWidget(self.browser)

    def set_markdown(self, markdown_text):
        self.browser.setMarkdown(markdown_text)


class ReviewTab(QWidget):
    """
    A Diff viewer tab to show what the AI changed in the code.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0d1117; color: #c9d1d9;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QLabel("Code Review (Diff)")
        header.setStyleSheet("padding: 10px; background-color: #161b22; border-bottom: 1px solid #30363d; font-weight: bold;")
        layout.addWidget(header)
        
        # Splitter for before/after or diff view
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.left_editor = QTextEdit()
        self.left_editor.setReadOnly(True)
        self.left_editor.setStyleSheet("background-color: #2d1a1c; color: #c9d1d9; border: none; font-family: monospace;")
        
        self.right_editor = QTextEdit()
        self.right_editor.setReadOnly(True)
        self.right_editor.setStyleSheet("background-color: #1a2d21; color: #c9d1d9; border: none; font-family: monospace;")
        
        splitter.addWidget(self.left_editor)
        splitter.addWidget(self.right_editor)
        
        layout.addWidget(splitter)

    def set_diff(self, original_text, new_text):
        self.left_editor.setPlainText(original_text)
        self.right_editor.setPlainText(new_text)
