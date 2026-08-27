import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel, QHBoxLayout, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QFileInfo
from PyQt6.QtGui import QIcon
from lmms.gui.utils.icon_provider import CustomIconProvider

from lmms.gui.widgets.code_editor import CodeEditor
from lmms.gui.widgets.ai_tabs import CanvasTab, MarkdownTab, ReviewTab

class EditorManager(QWidget):
    file_saved = pyqtSignal(str) # file_path
    file_dirty = pyqtSignal(str) # file_path
    cursor_position_changed = pyqtSignal(int, int) # line, col
    file_context_changed = pyqtSignal(str, int, str, str) # language, indent, encoding, eol
    
    def __init__(self):
        super().__init__()
        self.open_files = {} # path -> CodeEditor
        self.terminal_tab_index = -1
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Breadcrumb Bar
        self.breadcrumb_container = QWidget()
        self.breadcrumb_container.setStyleSheet("background-color: #161b22; border-bottom: 1px solid #30363d; padding: 4px;")
        breadcrumb_layout = QHBoxLayout(self.breadcrumb_container)
        breadcrumb_layout.setContentsMargins(10, 2, 10, 2)
        
        self.breadcrumb_label = QLabel("No file selected")
        self.breadcrumb_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        breadcrumb_layout.addWidget(self.breadcrumb_label)
        breadcrumb_layout.addStretch()
        
        # Terminal Button
        self.btn_terminal = QPushButton(">_ Terminal")
        self.btn_terminal.setStyleSheet("""
            QPushButton {
                background-color: #21262d; color: #c9d1d9;
                border: 1px solid #30363d; border-radius: 4px; padding: 4px 8px; font-size: 11px;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        self.btn_terminal.clicked.connect(self.open_terminal_tab)
        breadcrumb_layout.addWidget(self.btn_terminal)
        
        layout.addWidget(self.breadcrumb_container)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(False)
        self.tabs.setDocumentMode(True)
        self.tabs.setUsesScrollButtons(True)
        
        # Enable elision for long file names
        try:
            self.tabs.setElideMode(Qt.TextElideMode.ElideRight)
        except AttributeError:
            pass # QTabWidget has setElideMode in Qt6, just in case
            
        import os
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        close_icon = os.path.join(assets_dir, "icon_close_tab.svg").replace("\\", "/")
        close_icon_hover = os.path.join(assets_dir, "icon_close_tab_hover.svg").replace("\\", "/")
        
        self.tabs.setStyleSheet(f"""
            QTabWidget::tab-bar {{
                alignment: left;
            }}
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{
                background-color: #161b22;
                color: #8b949e;
                padding: 6px 12px;
                border: none;
                border-right: 1px solid #30363d;
                min-width: 80px;
                max-width: 160px;
            }}
            QTabBar::tab:selected {{
                background-color: #0e1116;
                color: #ffffff;
                border-top: 2px solid #1f6feb;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: #21262d;
            }}
            QTabBar::close-button {{
                image: url("{close_icon}");
                subcontrol-position: right;
                padding: 2px;
            }}
            QTabBar::close-button:hover {{
                image: url("{close_icon_hover}");
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }}
            QTabBar::scroller {{
                width: 28px;
            }}
            QTabBar QToolButton {{
                background-color: #161b22;
                color: #8b949e;
                border: 1px solid #30363d;
                border-radius: 2px;
            }}
            QTabBar QToolButton:hover {{
                background-color: #30363d;
            }}
        """)
        
        self.tabs.tabBar().setExpanding(False)
        
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tabs)
        
        # Empty State Container (Overlay)
        self.empty_state_widget = QWidget(self.tabs)
        # Removed WA_TransparentForMouseEvents to allow clicking the links
        empty_state_layout = QVBoxLayout(self.empty_state_widget)
        empty_state_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_state_layout.setSpacing(20)
        
        # Create a professional VSCode-style empty state layout
        inner_container = QWidget()
        inner_layout = QVBoxLayout(inner_container)
        inner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner_layout.setSpacing(10)
        
        # Logo/Title
        title_label = QLabel("LMMs Editor")
        title_label.setStyleSheet("color: #8b949e; font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner_layout.addWidget(title_label)
        
        # Shortcuts Section (Minimal)
        shortcuts_widget = QWidget()
        shortcuts_layout = QHBoxLayout(shortcuts_widget)
        shortcuts_layout.setContentsMargins(0, 0, 0, 0)
        
        shortcuts_left = QVBoxLayout()
        shortcuts_right = QVBoxLayout()
        
        def add_shortcut(layout, text, key):
            lbl = QLabel(f"<span style='color: #6e7681;'>{text}</span>")
            lbl.setStyleSheet("font-size: 13px;")
            key_lbl = QLabel(f"<span style='color: #8b949e; background-color: #21262d; border-radius: 4px; padding: 2px 6px;'>{key}</span>")
            key_lbl.setStyleSheet("font-size: 12px; font-weight: bold;")
            row = QHBoxLayout()
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(key_lbl)
            layout.addLayout(row)
            
        add_shortcut(shortcuts_left, "Search Files", "Ctrl+P")
        add_shortcut(shortcuts_left, "New File", "Ctrl+N")
        add_shortcut(shortcuts_right, "Toggle Sidebar", "Ctrl+B")
        add_shortcut(shortcuts_right, "Open Settings", "Ctrl+,")
        
        shortcuts_layout.addLayout(shortcuts_left)
        shortcuts_layout.addSpacing(40)
        shortcuts_layout.addLayout(shortcuts_right)
        
        inner_layout.addWidget(shortcuts_widget)
        
        empty_state_layout.addWidget(inner_container)
        
        self.empty_state_widget.show() # Initially empty
        
    def open_file(self, file_path: str, line: int = 0, col: int = 0):
        if file_path in self.open_files:
            editor = self.open_files[file_path]
            self.tabs.setCurrentWidget(editor)
            if hasattr(editor, "jump_to"):
                editor.jump_to(line, col)
            return
            
        import os
        from PyQt6.QtWidgets import QMessageBox
        
        disable_highlighting = False
        try:
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)
            
            if size_mb > 256:
                QMessageBox.warning(self, "File Too Large", f"The file is {size_mb:.1f} MB, which exceeds the 256 MB limit. Opening this could crash the editor.")
                return
                
            if size_mb > 5:
                disable_highlighting = True
                
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            content = f"Error opening file: {e}"
            disable_highlighting = True
            
        editor = CodeEditor()
        editor.load_file(file_path, content, disable_highlighting=disable_highlighting)
        editor.setProperty("file_path", file_path)
        
        # Track changes
        editor.textChanged.connect(lambda e=editor: self.mark_unsaved(e))
        editor.bridge.cursorPositionChanged.connect(self.cursor_position_changed.emit)
        
        self.open_files[file_path] = editor
        file_name = os.path.basename(file_path)
        
        provider = CustomIconProvider()
        icon = provider.icon(QFileInfo(file_path))
        
        idx = self.tabs.addTab(editor, icon, file_name)
        self.tabs.setCurrentIndex(idx)
        self.update_breadcrumbs(file_path)
        
        if hasattr(editor, "jump_to"):
            editor.jump_to(line, col)

    def open_custom_tab(self, widget: QWidget, title: str, identifier: str = None):
        # Open a generic widget as a tab
        if identifier and hasattr(self, 'custom_tabs') and identifier in self.custom_tabs:
            self.tabs.setCurrentWidget(self.custom_tabs[identifier])
            return
            
        if not hasattr(self, 'custom_tabs'):
            self.custom_tabs = {}
            
        widget.setProperty("is_custom", True)
        if identifier:
            widget.setProperty("identifier", identifier)
            self.custom_tabs[identifier] = widget
            
        idx = self.tabs.addTab(widget, title)
        self.tabs.setCurrentIndex(idx)
        self.breadcrumb_label.setText(f"Custom Tab > {title}")
        
    def open_terminal_tab(self):
        # Deprecated: Terminal is now a bottom dock panel in main_window.py
        pass
        
    def open_ai_canvas(self, identifier="ai_canvas", title="Canvas"):
        canvas = CanvasTab()
        self.open_custom_tab(canvas, title, identifier)
        return canvas

    def open_implementation_plan(self, content, identifier="ai_plan", title="Implementation Plan"):
        tab = MarkdownTab()
        tab.set_markdown(content)
        self.open_custom_tab(tab, title, identifier)
        return tab

    def open_task_list(self, content, identifier="ai_tasks", title="Task"):
        tab = MarkdownTab()
        tab.set_markdown(content)
        self.open_custom_tab(tab, title, identifier)
        return tab

    def open_walkthrough(self, content, identifier="ai_walkthrough", title="Walkthrough"):
        tab = MarkdownTab()
        tab.set_markdown(content)
        self.open_custom_tab(tab, title, identifier)
        return tab

    def open_review(self, original_text, new_text, identifier="ai_review", title="Review Code"):
        tab = ReviewTab()
        tab.set_diff(original_text, new_text)
        self.open_custom_tab(tab, title, identifier)
        return tab
        
    def close_tab(self, index: int):
        widget = self.tabs.widget(index)
        if widget:
            file_path = widget.property("file_path")
            is_custom = widget.property("is_custom")
            identifier = widget.property("identifier")
            
            self.tabs.removeTab(index)
            if file_path and file_path in self.open_files:
                del self.open_files[file_path]
            elif identifier and hasattr(self, 'custom_tabs') and identifier in self.custom_tabs:
                del self.custom_tabs[identifier]
                
            if hasattr(widget, 'cleanup'):
                try:
                    widget.cleanup()
                except Exception:
                    pass
            widget.deleteLater()
        
        if self.tabs.count() == 0:
            self.breadcrumb_label.setText("No file selected")
            self.empty_state_widget.show()
            
    def on_tab_changed(self, index: int):
        if self.tabs.count() == 0:
            self.empty_state_widget.show()
        else:
            self.empty_state_widget.hide()
            
        if index >= 0:
            widget = self.tabs.widget(index)
            file_path = widget.property("file_path")
            if file_path:
                self.update_breadcrumbs(file_path)
            
            if hasattr(widget, 'current_language'):
                # Extract some heuristics
                content = getattr(widget, '_current_content', '')
                eol = "CRLF" if "\r\n" in content else "LF"
                indent = 4
                if "  " in content and "    " not in content:
                    indent = 2
                self.file_context_changed.emit(widget.current_language.capitalize(), indent, "UTF-8", eol)
        else:
            self.file_context_changed.emit("", 4, "UTF-8", "LF")
            
    def update_breadcrumbs(self, file_path: str):
        parts = file_path.split(os.sep)
        if len(parts) > 3:
            display = " > ".join(parts[-3:])
        else:
            display = " > ".join(parts)
        self.breadcrumb_label.setText(display)
        
    def mark_unsaved(self, editor: CodeEditor):
        file_path = editor.property("file_path")
        is_dirty = getattr(editor, 'is_dirty', False)
        
        if not is_dirty:
            editor.is_dirty = True
            name = os.path.basename(file_path)
            for i in range(self.tabs.count()):
                if self.tabs.widget(i) == editor:
                    if not self.tabs.tabText(i).endswith("*"):
                        self.tabs.setTabText(i, name + " *")
                    break
            self.file_dirty.emit(file_path)
                
    def save_current_file(self):
        idx = self.tabs.currentIndex()
        if idx >= 0:
            widget = self.tabs.widget(idx)
            if widget.property("is_custom"):
                return
                
            editor = widget
            file_path = editor.property("file_path")
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(editor.toPlainText())
                editor.is_dirty = False
                self.tabs.setTabText(idx, os.path.basename(file_path))
                self.file_saved.emit(file_path)
            except Exception as e:
                print(f"Failed to save file: {e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'empty_state_widget') and self.empty_state_widget.isVisible():
            self.empty_state_widget.setGeometry(0, self.tabs.tabBar().height(), self.tabs.width(), self.tabs.height() - self.tabs.tabBar().height())
