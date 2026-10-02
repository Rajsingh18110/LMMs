# Made by markanm
import os
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTextEdit,
    QPushButton, QComboBox, QStackedWidget, QToolButton, QLabel, QFrame
)
from PyQt6.QtCore import QProcess, pyqtSlot, Qt, QProcessEnvironment
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat, QFont

import pty
import fcntl
import termios
import struct
import select
import json
from PyQt6.QtCore import QThread, pyqtSignal, QObject, pyqtSlot, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel

XTERM_HTML = """
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css" />
    <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        body, html { margin: 0; padding: 0; height: 100%; background-color: #1e1e1e; overflow: hidden; }
        #terminal { height: 100%; width: 100%; padding: 4px 10px; box-sizing: border-box; }
        .xterm .xterm-viewport { overflow-y: auto !important; }
    </style>
</head>
<body>
    <div id="terminal"></div>
    <script>
        var term = new Terminal({
            theme: {
                background: '#1e1e1e',
                foreground: '#cccccc',
                cursor: '#ffffff',
                selectionBackground: '#264f78'
            },
            fontFamily: 'monospace',
            fontSize: 13,
            cursorBlink: true
        });
        var fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);
        term.open(document.getElementById('terminal'));
        
        var backend;
        new QWebChannel(qt.webChannelTransport, function(channel) {
            backend = channel.objects.backend;
            
            term.onData(e => {
                backend.write_data(e);
            });
            
            term.onResize(size => {
                backend.resize_pty(size.cols, size.rows);
            });
            
            fitAddon.fit();
            backend.resize_pty(term.cols, term.rows);
            
            window.addEventListener('resize', () => {
                fitAddon.fit();
            });
        });
        
        window.write_to_term = function(data) {
            term.write(data);
        };
    </script>
</body>
</html>
"""

class PtyReaderThread(QThread):
    data_ready = pyqtSignal(str)
    
    def __init__(self, fd):
        super().__init__()
        self.fd = fd
        self.running = True
        
    def run(self):
        while self.running:
            r, _, _ = select.select([self.fd], [], [], 0.1)
            if self.fd in r:
                try:
                    data = os.read(self.fd, 4096)
                    if data:
                        text = data.decode('utf-8', errors='replace')
                        self.data_ready.emit(text)
                    else:
                        break
                except Exception:
                    break

class TerminalBackend(QObject):
    def __init__(self, fd):
        super().__init__()
        self.fd = fd
        
    @pyqtSlot(str)
    def write_data(self, data):
        try:
            os.write(self.fd, data.encode('utf-8'))
        except Exception:
            pass
            
    @pyqtSlot(int, int)
    def resize_pty(self, cols, rows):
        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

class TerminalWebEngine(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Enable QWebChannel support
        self.page().settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        # Fork PTY
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            shell = env.get("SHELL", "bash")
            os.execvpe(shell, [shell], env)
            
        self.shell_name = os.path.basename(os.environ.get("SHELL", "bash"))
            
        self.channel = QWebChannel(self)
        self.backend = TerminalBackend(self.fd)
        self.channel.registerObject("backend", self.backend)
        self.page().setWebChannel(self.channel)
        
        self.setHtml(XTERM_HTML, QUrl("qrc:///"))
        
        self.reader = PtyReaderThread(self.fd)
        self.reader.data_ready.connect(self.on_pty_data)
        self.reader.start()

    def on_pty_data(self, text):
        js = f"if (window.write_to_term) window.write_to_term({json.dumps(text)});"
        self.page().runJavaScript(js)

    def close_process(self):
        self.reader.running = False
        self.reader.wait(100)
        try:
            os.close(self.fd)
        except:
            pass
        # Kill the child process gracefully
        try:
            os.kill(self.pid, 9)
        except:
            pass


class TerminalPanel(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.terminals = []
        self.init_ui()
        
        from lmms.gui.utils.diagnostic_manager import DiagnosticManager
        DiagnosticManager.get_instance().diagnostics_updated.connect(self._update_problems_badge)
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border-top: 1px solid #30363d; background-color: #1e1e1e; }
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
        
        # Problems Tab — full Phase 5 widget with filter toolbar and live count
        from lmms.gui.panels.problems_tab import ProblemsTab
        self.problems_tab = ProblemsTab()
        self.tabs.addTab(self.problems_tab, "Problems")
        
        # Output Tab — full Phase 5 widget with channel dropdown
        from lmms.gui.panels.output_tab import OutputTab
        self.output_tab = OutputTab()
        self.tabs.addTab(self.output_tab, "Output")
        
        # Debug Console Tab — full Phase 5 widget with DAP REPL
        from lmms.gui.panels.debug_console_tab import DebugConsoleTab
        self.debug_console_tab = DebugConsoleTab()
        self.tabs.addTab(self.debug_console_tab, "Debug Console")
        
        # Terminal Tab
        from PyQt6.QtWidgets import QSplitter, QListWidget
        self.terminal_container = QSplitter(Qt.Orientation.Horizontal)
        self.terminal_container.setHandleWidth(1)
        self.terminal_container.setStyleSheet("QSplitter::handle { background: #30363d; }")
        
        self.terminal_stack = QStackedWidget()
        self.terminal_list = QListWidget()
        self.terminal_list.setFixedWidth(200)
        self.terminal_list.setStyleSheet("""
            QListWidget { background-color: #1e1e1e; color: #c9d1d9; border: none; border-left: 1px solid #30363d; outline: none; }
            QListWidget::item { padding: 6px 10px; border: none; font-size: 12px; }
            QListWidget::item:selected { background-color: #37373d; }
            QListWidget::item:hover { background-color: #2a2d2e; }
        """)
        self.terminal_list.currentRowChanged.connect(self.switch_terminal)
        
        self.terminal_container.addWidget(self.terminal_stack)
        self.terminal_container.addWidget(self.terminal_list)
        self.tabs.addTab(self.terminal_container, "Terminal")
        
        # Ports Tab — full Phase 5 widget with psutil
        from lmms.gui.panels.ports_tab import PortsTab
        self.ports_tab = PortsTab()
        self.tabs.addTab(self.ports_tab, "Ports")
        
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
        
        # Load VS Code Codicon Font
        from PyQt6.QtGui import QFontDatabase, QFont
        font_id = QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(__file__), "..", "assets", "monaco_build", "node_modules", "monaco-editor", "esm", "vs", "base", "browser", "ui", "codicons", "codicon", "codicon.ttf"))
        codicon_family = QFontDatabase.applicationFontFamilies(font_id)[0] if font_id != -1 else "sans-serif"
        
        icon_font = QFont(codicon_family, 12)
        
        self.btn_new_term = QToolButton()
        self.btn_new_term.setText("\uea60") # Plus
        self.btn_new_term.setFont(icon_font)
        self.btn_new_term.setStyleSheet(btn_style)
        self.btn_new_term.setToolTip("New Terminal")
        self.btn_new_term.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_term.clicked.connect(self.add_new_terminal)
        
        self.btn_split_term = QToolButton()
        self.btn_split_term.setText("\uea38") # Split
        self.btn_split_term.setFont(icon_font)
        self.btn_split_term.setStyleSheet(btn_style)
        self.btn_split_term.setToolTip("Split Terminal")
        self.btn_split_term.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_kill_term = QToolButton()
        self.btn_kill_term.setText("\uea81") # Trash
        self.btn_kill_term.setFont(icon_font)
        self.btn_kill_term.setStyleSheet(btn_style)
        self.btn_kill_term.setToolTip("Kill Terminal")
        self.btn_kill_term.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_kill_term.clicked.connect(self.kill_current_terminal)
        
        t_layout.addWidget(self.btn_new_term)
        t_layout.addWidget(self.btn_split_term)
        t_layout.addWidget(self.btn_kill_term)
        
        div = QFrame(); div.setFrameShape(QFrame.Shape.VLine); div.setStyleSheet("color: #30363d; margin: 4px 6px;")
        t_layout.addWidget(div)
        
        self.add_window_controls(t_layout, btn_style)
        self.corner_widget.addWidget(terminal_tb)
        
        # 3. Default Toolbar (for Output, Debug Console, Ports, Extension Logs)
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
        from PyQt6.QtGui import QFontDatabase, QFont
        import os
        font_id = QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(__file__), "..", "assets", "monaco_build", "node_modules", "monaco-editor", "esm", "vs", "base", "browser", "ui", "codicons", "codicon", "codicon.ttf"))
        codicon_family = QFontDatabase.applicationFontFamilies(font_id)[0] if font_id != -1 else "sans-serif"
        icon_font = QFont(codicon_family, 12)
        
        btn_max = QToolButton()
        btn_max.setText("\ueb2c") # Maximize/Chevron Up
        btn_max.setFont(icon_font)
        btn_max.setStyleSheet(btn_style)
        btn_max.setToolTip("Maximize Panel")
        btn_max.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_max.clicked.connect(self.maximize_panel)
        
        btn_close = QToolButton()
        btn_close.setText("\uea76") # Close
        btn_close.setFont(icon_font)
        btn_close.setStyleSheet(btn_style)
        btn_close.setToolTip("Close Panel")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close_panel)
        
        layout.addWidget(btn_max)
        layout.addWidget(btn_close)
    def cleanup(self):
        for term in self.terminals:
            try:
                term.close_process()
            except Exception:
                pass

    def add_new_terminal(self):
        term = TerminalWebEngine()
        self.terminals.append(term)
        self.terminal_stack.addWidget(term)
        
        name = term.shell_name
        self.terminal_list.addItem(f">_  {name}")
        self.terminal_list.setCurrentRow(len(self.terminals) - 1)
        
    def switch_terminal(self, index):
        if 0 <= index < len(self.terminals):
            self.terminal_stack.setCurrentIndex(index)
            
    def kill_current_terminal(self):
        idx = self.terminal_list.currentRow()
        if 0 <= idx < len(self.terminals):
            term = self.terminals.pop(idx)
            term.close_process()
            self.terminal_stack.removeWidget(term)
            term.deleteLater()
            
            item = self.terminal_list.takeItem(idx)
            if item:
                del item
            
            if not self.terminals:
                self.add_new_terminal()
                
    def on_tab_changed(self, index):
        title = self.tabs.tabText(index)
        if title.startswith("Problems"):
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

    def _update_problems_badge(self, file_path=None):
        """Update the Problems tab title badge count."""
        from lmms.gui.utils.diagnostic_manager import DiagnosticManager
        diags = DiagnosticManager.get_instance().get_diagnostics()
        count = sum(len(v) for v in diags.values())
        idx = self.tabs.indexOf(self.problems_tab)
        if idx != -1:
            self.tabs.setTabText(idx, f"Problems {count}" if count else "Problems")

    def set_dap_manager(self, dap_manager):
        """Wire the DAP manager into the Debug Console tab."""
        self.debug_console_tab.set_dap_manager(dap_manager)
