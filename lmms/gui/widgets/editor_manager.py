import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel, QHBoxLayout, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from lmms.gui.widgets.code_editor import CodeEditor
from lmms.gui.panels.terminal_panel import TerminalPanel
from lmms.gui.widgets.ai_tabs import CanvasTab, MarkdownTab, ReviewTab

class EditorManager(QWidget):
    file_saved = pyqtSignal(str) # file_path
    
    def __init__(self):
        super().__init__()
        self.open_files = {} # path -> CodeEditor
        self.terminal_tab_index = -1
        self.terminal_panel = None
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
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tabs)
        
        # Empty State Container (Overlay)
        self.empty_state_widget = QWidget(self.tabs)
        self.empty_state_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        empty_state_layout = QVBoxLayout(self.empty_state_widget)
        empty_state_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_state_layout.setSpacing(20)
        
        # Welcome Logo
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        logo_path = os.path.join(assets_dir, "lmms_logo.png")
        if os.path.exists(logo_path):
            self.welcome_logo = QLabel()
            from PyQt6.QtGui import QPixmap
            big_logo_pixmap = QPixmap(logo_path).scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.welcome_logo.setPixmap(big_logo_pixmap)
            self.welcome_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_state_layout.addWidget(self.welcome_logo)
        
        # Shortcuts
        self.shortcuts_label = QLabel("<center><p style='color: #8b949e; font-size: 14px;'>Ctrl+P : Search Files<br>Ctrl+N : New File<br>Ctrl+B : Toggle Sidebar</p></center>")
        self.shortcuts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_state_layout.addWidget(self.shortcuts_label)
        
        self.empty_state_widget.show() # Initially empty
        
    def open_file(self, file_path: str):
        if file_path in self.open_files:
            self.tabs.setCurrentWidget(self.open_files[file_path])
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
        
        self.open_files[file_path] = editor
        file_name = os.path.basename(file_path)
        
        idx = self.tabs.addTab(editor, file_name)
        self.tabs.setCurrentIndex(idx)
        self.update_breadcrumbs(file_path)

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
        if self.terminal_panel is None:
            self.terminal_panel = TerminalPanel()
            self.terminal_panel.setProperty("is_terminal", True)
            self.terminal_tab_index = self.tabs.addTab(self.terminal_panel, "Terminal")
        
        # Check if it was closed and needs to be re-added
        if self.tabs.indexOf(self.terminal_panel) == -1:
            self.terminal_tab_index = self.tabs.addTab(self.terminal_panel, "Terminal")
            
        self.tabs.setCurrentWidget(self.terminal_panel)
        self.breadcrumb_label.setText("Terminal")
        
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
        if widget == self.terminal_panel:
            self.tabs.removeTab(index)
            # We don't delete the terminal panel, we just hide it from tabs
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
            if widget == self.terminal_panel:
                self.breadcrumb_label.setText("Terminal")
            else:
                file_path = widget.property("file_path")
                if file_path:
                    self.update_breadcrumbs(file_path)
            
    def update_breadcrumbs(self, file_path: str):
        parts = file_path.split(os.sep)
        if len(parts) > 3:
            display = " > ".join(parts[-3:])
        else:
            display = " > ".join(parts)
        self.breadcrumb_label.setText(display)
        
    def mark_unsaved(self, editor: CodeEditor):
        file_path = editor.property("file_path")
        for i in range(self.tabs.count()):
            if self.tabs.widget(i) == editor:
                name = os.path.basename(file_path)
                if not self.tabs.tabText(i).endswith("*"):
                    self.tabs.setTabText(i, name + " *")
                break
                
    def save_current_file(self):
        idx = self.tabs.currentIndex()
        if idx >= 0:
            widget = self.tabs.widget(idx)
            if widget == self.terminal_panel:
                return
                
            editor = widget
            file_path = editor.property("file_path")
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(editor.toPlainText())
                self.tabs.setTabText(idx, os.path.basename(file_path))
                self.file_saved.emit(file_path)
            except Exception as e:
                print(f"Failed to save file: {e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'empty_state_widget') and self.empty_state_widget.isVisible():
            self.empty_state_widget.setGeometry(0, self.tabs.tabBar().height(), self.tabs.width(), self.tabs.height() - self.tabs.tabBar().height())
