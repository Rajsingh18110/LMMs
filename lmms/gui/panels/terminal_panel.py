# Made by markanm
import os
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTextEdit,
    QPushButton, QComboBox, QStackedWidget, QToolButton, QLabel, QFrame
)
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
        
        shell_path = os.environ.get("SHELL", "bash")
        self.shell_name = os.path.basename(shell_path)
        self.process.start(shell_path, ["-i"])
        
        self.readonly_pos = 0

    def close_process(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(100)

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
        
        # Remove OSC (Operating System Command) sequences like window title
        text = re.sub(r'\x1b\].*?(?:\x07|\x1b\\)', '', text)
        
        # Extremely basic ANSI color parser
        parts = re.split(r'\x1b\[([0-9;]*)m', text)
        
        format = QTextCharFormat()
        format.setForeground(QColor("#c9d1d9")) # Default color
        
        for i, part in enumerate(parts):
            if i % 2 == 1:
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
                if part:
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
            
            cursor.setPosition(self.readonly_pos, QTextCursor.MoveMode.KeepAnchor)
            cmd = cursor.selectedText().replace('\u2029', '\n').replace('\u00a0', ' ')
            
            cursor.removeSelectedText()
            self.setTextCursor(cursor)
            
            self.process.write((cmd + "\n").encode('utf-8'))
            return

        super().keyPressEvent(event)


class TerminalPanel(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.terminals = []
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
                background: transparent;
                color: #8b949e;
                padding: 6px 15px;
                border: none;
                font-size: 11px;
                text-transform: uppercase;
                border-bottom: 1px solid transparent;
            }
            QTabBar::tab:selected {
                color: #c9d1d9;
                border-bottom: 1px solid #58a6ff;
            }
            QTabBar::tab:hover {
                color: #c9d1d9;
            }
        """)
        
        # Problems Tab
        self.problems_text = QTextEdit()
        self.problems_text.setReadOnly(True)
        self.problems_text.setStyleSheet("background-color: #0d1117; color: #c9d1d9; border: none; font-family: monospace; padding: 10px;")
        self.problems_text.setPlainText("No problems have been detected in the workspace.")
        self.tabs.addTab(self.problems_text, "Problems")
        
        # Output Tab
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("background-color: #0d1117; color: #c9d1d9; border: none; font-family: monospace; padding: 10px;")
        self.tabs.addTab(self.output_text, "Output")
        
        # Debug Console Tab
        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        self.debug_text.setStyleSheet("background-color: #0d1117; color: #c9d1d9; border: none; font-family: monospace; padding: 10px;")
        self.tabs.addTab(self.debug_text, "Debug Console")
        
        # Terminal Tab
        self.terminal_container = QWidget()
        terminal_layout = QVBoxLayout(self.terminal_container)
        terminal_layout.setContentsMargins(0,0,0,0)
        terminal_layout.setSpacing(0)
        
        self.terminal_stack = QStackedWidget()
        terminal_layout.addWidget(self.terminal_stack)
        self.tabs.addTab(self.terminal_container, "Terminal")
        
        # Ports Tab
        self.ports_text = QTextEdit()
        self.ports_text.setReadOnly(True)
        self.ports_text.setStyleSheet("background-color: #0d1117; color: #c9d1d9; border: none; font-family: monospace; padding: 10px;")
        self.ports_text.setPlainText("No forwarded ports.")
        self.tabs.addTab(self.ports_text, "Ports")
        
        # --- Corner Widget Toolbars ---
        self.corner_widget = QStackedWidget()
        self.tabs.setCornerWidget(self.corner_widget)
        
        btn_style = """
            QToolButton { background: transparent; color: #c9d1d9; border: none; font-size: 14px; padding: 4px 6px; }
            QToolButton:hover { background: #30363d; border-radius: 4px; }
        """
        
        # 1. Problems Toolbar
        problems_tb = QWidget()
        p_layout = QHBoxLayout(problems_tb)
        p_layout.setContentsMargins(0, 0, 15, 0)
        p_layout.setSpacing(10)
        self.btn_send_ai = QPushButton("✨ Send all problems to AI")
        self.btn_send_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send_ai.setStyleSheet("""
            QPushButton { background: transparent; color: #58a6ff; border: none; font-size: 11px; padding: 4px 8px; }
            QPushButton:hover { color: #79c0ff; text-decoration: underline; }
        """)
        p_layout.addWidget(self.btn_send_ai)
        
        self.add_window_controls(p_layout, btn_style)
        self.corner_widget.addWidget(problems_tb)
        
        # 2. Terminal Toolbar
        terminal_tb = QWidget()
        t_layout = QHBoxLayout(terminal_tb)
        t_layout.setContentsMargins(0, 0, 15, 0)
        t_layout.setSpacing(4)
        
        self.term_selector = QComboBox()
        self.term_selector.setCursor(Qt.CursorShape.PointingHandCursor)
        self.term_selector.setStyleSheet("""
            QComboBox { background: transparent; color: #c9d1d9; border: none; font-size: 11px; padding: 2px 5px; }
            QComboBox::drop-down { border: none; }
            QComboBox:hover { background: #30363d; border-radius: 4px; }
        """)
        self.term_selector.currentIndexChanged.connect(self.switch_terminal)
        t_layout.addWidget(self.term_selector)
        
        self.btn_new_term = QToolButton(); self.btn_new_term.setText("＋"); self.btn_new_term.setStyleSheet(btn_style); self.btn_new_term.setToolTip("New Terminal"); self.btn_new_term.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_term.clicked.connect(self.add_new_terminal)
        
        self.btn_kill_term = QToolButton(); self.btn_kill_term.setText("🗑"); self.btn_kill_term.setStyleSheet(btn_style); self.btn_kill_term.setToolTip("Kill Terminal"); self.btn_kill_term.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_kill_term.clicked.connect(self.kill_current_terminal)
        
        t_layout.addWidget(self.btn_new_term)
        t_layout.addWidget(self.btn_kill_term)
        
        div = QFrame(); div.setFrameShape(QFrame.Shape.VLine); div.setStyleSheet("color: #30363d; margin: 4px 6px;")
        t_layout.addWidget(div)
        
        self.add_window_controls(t_layout, btn_style)
        self.corner_widget.addWidget(terminal_tb)
        
        # 3. Default Toolbar (for Output, Debug Console, Ports)
        default_tb = QWidget()
        d_layout = QHBoxLayout(default_tb)
        d_layout.setContentsMargins(0, 0, 15, 0)
        d_layout.setSpacing(4)
        self.add_window_controls(d_layout, btn_style)
        self.corner_widget.addWidget(default_tb)
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # Initialize the first terminal
        self.add_new_terminal()
        
        layout.addWidget(self.tabs)
        self.tabs.setCurrentIndex(3) # Set to Terminal
        self.on_tab_changed(3)
        
    def add_window_controls(self, layout, btn_style):
        btn_max = QToolButton(); btn_max.setText("⛶"); btn_max.setStyleSheet(btn_style); btn_max.setToolTip("Maximize Panel"); btn_max.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_max.clicked.connect(self.maximize_panel)
        
        btn_close = QToolButton(); btn_close.setText("✕"); btn_close.setStyleSheet(btn_style); btn_close.setToolTip("Close Panel"); btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close_panel)
        
        layout.addWidget(btn_max)
        layout.addWidget(btn_close)

    def add_new_terminal(self):
        term = TerminalEdit()
        self.terminals.append(term)
        self.terminal_stack.addWidget(term)
        
        idx = len(self.terminals)
        name = term.shell_name
        self.term_selector.addItem(f">_  {name}")
        self.term_selector.setCurrentIndex(idx - 1)
        
    def switch_terminal(self, index):
        if 0 <= index < len(self.terminals):
            self.terminal_stack.setCurrentIndex(index)
            
    def kill_current_terminal(self):
        idx = self.term_selector.currentIndex()
        if 0 <= idx < len(self.terminals):
            term = self.terminals.pop(idx)
            term.close_process()
            self.terminal_stack.removeWidget(term)
            term.deleteLater()
            self.term_selector.removeItem(idx)
            
            if not self.terminals:
                self.add_new_terminal()
                
    def on_tab_changed(self, index):
        title = self.tabs.tabText(index)
        if title == "Problems":
            self.corner_widget.setCurrentIndex(0)
        elif title == "Terminal":
            self.corner_widget.setCurrentIndex(1)
        else:
            self.corner_widget.setCurrentIndex(2)
            
    def maximize_panel(self):
        if self.main_window and hasattr(self.main_window, 'central_splitter'):
            splitter = self.main_window.central_splitter
            sizes = splitter.sizes()
            if not sizes:
                return
            # If editor is visible (size > 50), maximize panel
            if sizes[0] > 50:
                self._old_sizes = sizes
                splitter.setSizes([0, sum(sizes)])
            else:
                if hasattr(self, '_old_sizes'):
                    splitter.setSizes(self._old_sizes)
                else:
                    total = sum(sizes)
                    splitter.setSizes([int(total * 0.7), int(total * 0.3)])
                    
    def close_panel(self):
        self.setVisible(False)
