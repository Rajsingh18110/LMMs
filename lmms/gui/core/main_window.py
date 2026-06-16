from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QPushButton, QLabel, QSplitter,
    QTreeView, QTabWidget, QTextEdit, QDockWidget, QMenu, QStatusBar
)
from PyQt6.QtCore import Qt
import os
from PyQt6.QtGui import QPixmap, QIcon
try:
    from PyQt6.QtGui import QFileSystemModel
except ImportError:
    try:
        from PyQt6.QtWidgets import QFileSystemModel
    except ImportError:
        QFileSystemModel = None

from lmms.gui.pages.chat_page import ChatPage
from lmms.gui.widgets.editor_manager import EditorManager
from lmms.gui.panels.terminal_panel import TerminalPanel
from lmms.backend.core.commands import CommandRegistry, CommandContext
from lmms.gui.utils.icon_provider import CustomIconProvider
from lmms.gui.panels.search_panel import SearchPanel
from lmms.gui.widgets.model_browser import ModelBrowser, ModelDetailsTab
from lmms.backend.services.workspace_service import WorkspaceService
from lmms.gui.widgets.menu import LMMsMenuBar

# State Management & Notifications
from lmms.backend.logic.manager import BackendManager
from lmms.gui.state.manager import GUIStateManager
from lmms.gui.notifications.manager import NotificationManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LMMs - Local Machine Model Studio")
        self.resize(1400, 900)
        
        # Set Window Icon
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "lmms_logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # State & Backend
        self.backend = BackendManager()
        self.state_manager = GUIStateManager(self.backend)
        
        # Setup command context before UI so actions are ready
        self.command_context = CommandContext(self)
        CommandRegistry.set_context(self.command_context)
        
        self.init_ui()
        
        # Notification Overlay
        self.notifications = NotificationManager(self)
        self.notifications.setGeometry(0, 0, self.width(), self.height())
        
        # Setup Menu Bar
        self.setMenuBar(LMMsMenuBar(self))
        
        # Restore State
        state = WorkspaceService.load_workspace_state()
        if state:
            WorkspaceService.apply_state(self, state)

    def init_ui(self):
        # Main layout: Horizontal (Sidebar + Content)
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar (Icon-only mode for IDE look)
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(60)
        self.sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(5, 20, 5, 20)
        sidebar_layout.setSpacing(15)

        # Inner QMainWindow to handle docking layout
        self.inner_window = QMainWindow()
        self.inner_window.setDockOptions(QMainWindow.DockOption.AllowNestedDocks | QMainWindow.DockOption.AnimatedDocks)
        
        # Central Widget: Multi-tab Editor
        self.editor_manager = EditorManager()
        self.inner_window.setCentralWidget(self.editor_manager)

        # Docks Dictionary
        self.docks = {}
        
        # 1. Explorer Dock
        self.explorer_dock = QDockWidget("Explorer", self.inner_window)
        self.explorer_dock.setObjectName("ExplorerDock")
        self.explorer_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        
        self.explorer_widget = QWidget()
        explorer_layout = QVBoxLayout(self.explorer_widget)
        explorer_layout.setContentsMargins(0, 0, 0, 0)
        
        if QFileSystemModel is not None:
            self.file_model = QFileSystemModel()
            self.file_model.setIconProvider(CustomIconProvider())
            cwd = os.getcwd()
            self.file_model.setRootPath(cwd)
            
            self.tree_view = QTreeView()
            self.tree_view.setModel(self.file_model)
            self.tree_view.setRootIndex(self.file_model.index(cwd))
            self.tree_view.setHeaderHidden(True)
            # Hide size, type, date columns
            for i in range(1, 4):
                self.tree_view.hideColumn(i)
            self.tree_view.setStyleSheet("QTreeView { background-color: #0d1117; border: none; } QTreeView::item:hover { background-color: #21262d; }")
            
            # Disable auto-expand on double click
            self.tree_view.setExpandsOnDoubleClick(False)
            
            # Connect clicks
            self.tree_view.doubleClicked.connect(self.on_file_double_clicked)
            self.tree_view.clicked.connect(self.on_file_clicked)
            
            # Enable custom context menu
            self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.tree_view.customContextMenuRequested.connect(self.show_explorer_context_menu)
            
            explorer_layout.addWidget(self.tree_view)
        else:
            placeholder = QLabel("File Explorer unavailable\n(QFileSystemModel missing)")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #8b949e;")
            explorer_layout.addWidget(placeholder)
            
        self.explorer_dock.setWidget(self.explorer_widget)
        self.docks["Explorer"] = self.explorer_dock
        
        # 2. Chat Dock
        self.chat_dock = QDockWidget("AI Chat", self.inner_window)
        self.chat_dock.setObjectName("ChatDock")
        self.chat_page = ChatPage()
        self.chat_dock.setWidget(self.chat_page)
        self.docks["Chats"] = self.chat_dock
        
        # 3. Search Dock
        self.search_dock = SearchPanel(self.inner_window)
        self.search_dock.setObjectName("SearchDock")
        self.docks["Search"] = self.search_dock
        self.search_dock.result_clicked.connect(self.on_search_result_clicked)
        self.search_dock.hide() # Hidden by default
        
        # 4. Model Browser Dock
        self.model_dock = ModelBrowser(self.inner_window)
        self.model_dock.setObjectName("ModelDock")
        self.docks["Models"] = self.model_dock
        self.model_dock.model_selected.connect(self.on_model_selected)
        self.model_dock.hide() # Hidden by default
        
        # 5. Reserved Docks (Tasks, Memory, Git)
        for name in ["Tasks", "Memory", "Git"]:
            dock = QDockWidget(name, self.inner_window)
            dock.setObjectName(f"{name}Dock")
            label = QLabel(f"{name} Panel (Coming Soon)")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #8b949e;")
            dock.setWidget(label)
            self.docks[name] = dock
            dock.hide()
        
        # Disable floating and enforce VS Code style layout
        for dock in self.docks.values():
            dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable | QDockWidget.DockWidgetFeature.DockWidgetMovable)

        # Add Docks - Initial Default Layout
        self.inner_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.explorer_dock)
        self.inner_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.search_dock)
        self.inner_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.model_dock)
        self.inner_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.chat_dock)

        # Sidebar Buttons
        self.nav_buttons = {}
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "lmms_logo.png")
        nav_items = [
            ("📁", "Explorer", None),
            ("🔍", "Search", None),
            ("📋", "Tasks", None),
            ("🧠", "Memory", None),
            ("🌳", "Git", None),
            ("📦", "Models", None),
            ("💬", "Chats", None),
            ("Terminal", "Terminal", None),
            ("", "Settings", logo_path if os.path.exists(logo_path) else None),
        ]

        for text_icon, name, custom_icon_path in nav_items:
            # Fallback for settings if logo doesn't exist
            if name == "Settings" and not custom_icon_path:
                text_icon = "⚙"
            # Fallback for terminal
            if name == "Terminal" and not custom_icon_path:
                text_icon = "🖥"
                
            btn = QPushButton(text_icon)
            if custom_icon_path:
                btn.setIcon(QIcon(custom_icon_path))
                
            btn.setToolTip(name)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setFixedSize(40, 40)
            
            # Special case for Settings since we removed the dock
            if name == "Settings":
                btn.clicked.connect(lambda checked: CommandRegistry.execute("settings.providers"))
            elif name == "Terminal":
                btn.clicked.connect(lambda checked: self.editor_manager.open_terminal_tab())
            else:
                btn.clicked.connect(lambda checked, n=name, b=btn: self.toggle_dock(n, b))
                # Connect visibility changed to update button state
                self.docks[name].visibilityChanged.connect(lambda visible, b=btn: b.setChecked(visible))
                # Sync initial state
                btn.setChecked(self.docks[name].isVisible())
            
            sidebar_layout.addWidget(btn)
            if name not in ["Settings", "Terminal"]:
                self.nav_buttons[name] = btn

        sidebar_layout.addStretch()

        # Add to main layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.inner_window)

        self.setCentralWidget(main_widget)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background-color: #0e1116; color: #8b949e; border-top: 1px solid #30363d; padding-left: 10px;")
        self.setStatusBar(self.status_bar)
        
        self.status_file_info = QLabel("Ready")
        self.status_ai_info = QLabel("AI: Idle | Model: default")
        self.status_bar.addWidget(self.status_file_info)
        self.status_bar.addPermanentWidget(self.status_ai_info)
        
        # Auto-manage Chat visibility based on tab context
        self.editor_manager.tabs.currentChanged.connect(self.on_editor_tab_changed)

    def on_editor_tab_changed(self, index):
        if index < 0:
            if "Chats" in self.docks and not self.docks["Chats"].isVisible():
                self.docks["Chats"].show()
                if "Chats" in self.nav_buttons:
                    self.nav_buttons["Chats"].setChecked(True)
            return

        widget = self.editor_manager.tabs.widget(index)
        is_model = hasattr(widget, "model_info") or (widget.property("is_custom") and widget.property("identifier"))
        
        if is_model:
            if "Chats" in self.docks and self.docks["Chats"].isVisible():
                self.docks["Chats"].hide()
                if "Chats" in self.nav_buttons:
                    self.nav_buttons["Chats"].setChecked(False)
        else:
            if "Chats" in self.docks and not self.docks["Chats"].isVisible():
                self.docks["Chats"].show()
                if "Chats" in self.nav_buttons:
                    self.nav_buttons["Chats"].setChecked(True)

    def toggle_dock(self, name, button):
        dock = self.docks[name]
        
        left_docks = ["Explorer", "Search", "Tasks", "Memory", "Git", "Models"]
        if name in left_docks:
            # Hide other left docks to simulate sidebar tabs
            if not dock.isVisible():
                for other in left_docks:
                    if other != name and self.docks[other].isVisible():
                        self.docks[other].hide()
                        if other in self.nav_buttons:
                            self.nav_buttons[other].setChecked(False)

        if dock.isVisible():
            dock.hide()
            button.setChecked(False)
        else:
            dock.show()
            dock.raise_()
            button.setChecked(True)

    def on_file_clicked(self, index):
        if not hasattr(self, 'file_model') or self.file_model is None:
            return
        if self.file_model.isDir(index):
            # Toggle expansion state explicitly, avoiding auto-expand on load
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
            else:
                self.tree_view.expand(index)
                
    def show_explorer_context_menu(self, position):
        if not hasattr(self, 'file_model') or self.file_model is None:
            return
        index = self.tree_view.indexAt(position)
        
        menu = QMenu()
        menu.setStyleSheet("QMenu { background-color: #161b22; color: #c9d1d9; border: 1px solid #30363d; } QMenu::item:selected { background-color: #1f6feb; }")
        
        action_refresh = menu.addAction("Refresh Explorer")
        action_collapse = menu.addAction("Collapse All")
        
        if index.isValid():
            menu.addSeparator()
            action_expand_selected = menu.addAction("Expand Selected")
            if not self.file_model.isDir(index):
                action_open_containing = menu.addAction("Open Containing Folder")
        
        action = menu.exec(self.tree_view.viewport().mapToGlobal(position))
        
        if action == action_refresh:
            self.file_model.setRootPath(self.file_model.rootPath()) # triggers refresh
        elif action == action_collapse:
            self.tree_view.collapseAll()
        elif index.isValid() and action == action_expand_selected:
            self.tree_view.expandRecursively(index)
        elif index.isValid() and not self.file_model.isDir(index) and action == action_open_containing:
            file_path = self.file_model.filePath(index)
            import subprocess
            folder = os.path.dirname(file_path)
            if os.name == 'nt':
                os.startfile(folder)
            else:
                subprocess.Popen(['xdg-open', folder])

    def on_search_result_clicked(self, path, line, col):
        # Open file
        self.editor_manager.open_file(path)
        # Highlight line in editor
        if path in self.editor_manager.open_files:
            editor = self.editor_manager.open_files[path]
            # Qt text editors are 0-indexed for blocks
            # But line passed is 1-indexed
            try:
                from PyQt6.QtGui import QTextCursor
                block = editor.document().findBlockByNumber(line - 1)
                if block.isValid():
                    cursor = QTextCursor(block)
                    cursor.setPosition(block.position() + col)
                    editor.setTextCursor(cursor)
                    editor.ensureCursorVisible()
            except Exception:
                pass

    def on_model_selected(self, model_info):
        identifier = model_info.get("modelId", model_info.get("id", ""))
        tab = ModelDetailsTab(model_info)
        self.editor_manager.open_custom_tab(tab, identifier, identifier)

    def on_file_double_clicked(self, index):
        if not hasattr(self, 'file_model') or self.file_model is None:
            return
        file_path = self.file_model.filePath(index)
        if not self.file_model.isDir(index):
            self.editor_manager.open_file(file_path)
            self.status_file_info.setText(f"Opened: {os.path.basename(file_path)}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Ensure notifications overlay resizes with window
        if hasattr(self, 'notifications'):
            self.notifications.setGeometry(0, 0, self.width(), self.height())

    def closeEvent(self, event):
        state = WorkspaceService.capture_state(self)
        WorkspaceService.save_workspace_state(state)
        
        # Cleanup threads in docks and editor manager
        for dock in self.docks.values():
            if hasattr(dock, 'cleanup'):
                try:
                    dock.cleanup()
                except Exception:
                    pass
            if dock.widget() and hasattr(dock.widget(), 'cleanup'):
                try:
                    dock.widget().cleanup()
                except Exception:
                    pass
                    
        # Close all tabs in editor manager to invoke their cleanups
        if hasattr(self, 'editor_manager'):
            while self.editor_manager.tabs.count() > 0:
                self.editor_manager.close_tab(0)
                
        super().closeEvent(event)
