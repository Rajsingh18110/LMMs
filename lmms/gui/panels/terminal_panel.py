import os
import re
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QTextEdit
from PyQt6.QtCore import QProcess, pyqtSlot, Qt, QProcessEnvironment
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat, QFont

ANSI_COLORS = {
    '30': '#000000', '31': '#ff7b72', '32': '#3fb950', '33': '#d29922',
    '34': '#58a6ff', '35': '#bc8cff', '36': '#39c5cf', '37': '#c9d1d9',
    '90': '#8b949e', '91': '#ff7b72', '92': '#56d364', '93': '#e3b341',
    '94': '#79c0ff', '95': '#d2a8ff', '96': '#56d4dd', '97': '#f0f6fc',
}

class TerminalEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0d1117; color: #c9d1d9; border: none; font-family: monospace;")
        self.setFont(QFont("monospace", 10))
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.on_ready_read)
        
        # Environment variables for colorful output
        env = QProcessEnvironment.systemEnvironment()
        env.insert("TERM", "xterm-256color")
        env.insert("CLICOLOR", "1")
        env.insert("LSCOLORS", "ExFxBxDxCxegedabagacad")
        self.process.setProcessEnvironment(env)
        
        self.process.setWorkingDirectory(os.getcwd())
        self.process.start("bash", ["-i"])
        
        self.readonly_pos = 0

    def on_ready_read(self):
        data = self.process.readAllStandardOutput().data()
        try:
            text = data.decode('utf-8', errors='replace')
        except:
            text = data.decode('latin1', errors='replace')
            
        self.append_ansi_text(text)

    def append_ansi_text(self, text):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        
        # Extremely basic ANSI color parser
        # \x1b[31;1m etc
        parts = re.split(r'\x1b\[([0-9;]*)m', text)
        
        format = QTextCharFormat()
        format.setForeground(QColor("#c9d1d9")) # Default color
        
        for i, part in enumerate(parts):
            if i % 2 == 1:
                # This is a color code
                codes = part.split(';')
                for code in codes:
                    if code in ANSI_COLORS:
                        format.setForeground(QColor(ANSI_COLORS[code]))
                    elif code == '0' or code == '':
                        format.setForeground(QColor("#c9d1d9"))
                        format.setFontWeight(QFont.Weight.Normal)
                    elif code == '1':
                        format.setFontWeight(QFont.Weight.Bold)
            else:
                # This is text
                if part:
                    # Filter out other escape sequences we don't support
                    clean_part = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', part)
                    cursor.insertText(clean_part, format)
                    
        self.readonly_pos = self.document().characterCount() - 1
        self.ensureCursorVisible()

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        
        # Prevent editing before readonly_pos
        if cursor.position() < self.readonly_pos and event.key() not in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Copy):
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            
        if event.key() == Qt.Key.Key_Backspace and cursor.position() <= self.readonly_pos:
            return
            
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            
            # Get the command user typed
            cursor.setPosition(self.readonly_pos, QTextCursor.MoveMode.KeepAnchor)
            cmd = cursor.selectedText()
            
            # Clear selection and insert newline locally
            cursor.clearSelection()
            self.setTextCursor(cursor)
            
            # Append newline locally to echo it
            format = QTextCharFormat()
            format.setForeground(QColor("#c9d1d9"))
            cursor.insertText("\n", format)
            self.readonly_pos = self.document().characterCount() - 1
            
            # Send to process
            self.process.write((cmd + "\n").encode('utf-8'))
            return

        super().keyPressEvent(event)


class TerminalPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border-top: 1px solid #30363d; background-color: #0d1117; }
            QTabBar::tab {
                background: #0e1116;
                color: #8b949e;
                padding: 6px 12px;
                border: none;
            }
            QTabBar::tab:selected {
                color: #c9d1d9;
                border-bottom: 2px solid #58a6ff;
            }
        """)
        
        # Terminal Tab
        self.terminal_text = TerminalEdit()
        self.tabs.addTab(self.terminal_text, "Terminal")
        
        # Output Tab
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("background-color: #0d1117; color: #c9d1d9; border: none; font-family: monospace;")
        self.tabs.addTab(self.output_text, "Output")
        
        # Problems Tab
        self.problems_text = QTextEdit()
        self.problems_text.setReadOnly(True)
        self.problems_text.setStyleSheet("background-color: #0d1117; color: #c9d1d9; border: none; font-family: monospace;")
        self.problems_text.setPlainText("No problems have been detected in the workspace.")
        self.tabs.addTab(self.problems_text, "Problems")
        
        layout.addWidget(self.tabs)
