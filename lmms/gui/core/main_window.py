from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QPushButton, QLabel, QSplitter,
    QTreeView, QTabWidget, QTextEdit, QDockWidget, QMenu, QStatusBar, QFrame
)
from PyQt6.QtCore import Qt, QSize, QPoint, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QIcon, QFont, QCursor, QColor, QPixmap, QPainter
import os
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
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
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
        
        # Setup Menu Bar
        menu_bar = LMMsMenuBar(self)
        self.menu_bar_widget = menu_bar
        
        self.init_ui()
        
        # Notification Overlay
        self.notifications = NotificationManager(self)
        self.notifications.setGeometry(0, 0, self.width(), self.height())
        
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

        # Sidebar (Activity Bar - VS Code style)
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(48)
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setStyleSheet("background-color: #181818;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 10, 0, 10)
        sidebar_layout.setSpacing(10)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

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
            
            self.is_empty_workspace = (cwd == os.path.expanduser("~"))
            
            if not self.is_empty_workspace:
                self.file_model.setRootPath(cwd)
                project_name = os.path.basename(cwd)
                if not project_name: project_name = cwd
            else:
                self.file_model.setRootPath("")
                project_name = "NO FOLDER OPENED"
            
            # Explorer Toolbar
            self.explorer_toolbar = QWidget()
            toolbar_layout = QHBoxLayout(self.explorer_toolbar)
            toolbar_layout.setContentsMargins(15, 8, 10, 8)
            
            self.project_label = QLabel(project_name.upper())
            self.project_label.setStyleSheet("color: #cccccc; font-weight: bold; font-size: 11px; letter-spacing: 1px;")
            
            self.btn_new_file = QPushButton("📄")
            self.btn_new_file.setToolTip("New File")
            self.btn_new_file.clicked.connect(self.create_new_file)
            
            self.btn_new_folder = QPushButton("📁")
            self.btn_new_folder.setToolTip("New Folder")
            self.btn_new_folder.clicked.connect(self.create_new_folder)
            
            self.btn_refresh = QPushButton("↻")
            self.btn_refresh.setToolTip("Refresh Explorer")
            self.btn_refresh.clicked.connect(lambda: self.file_model.setRootPath(self.file_model.rootPath()))
            
            for btn in [self.btn_new_file, self.btn_new_folder, self.btn_refresh]:
                btn.setFixedSize(22, 22)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton { background: transparent; border: none; color: #8b949e; border-radius: 4px; font-size: 12px; padding: 0px; }
                    QPushButton:hover { background: #30363d; color: #c9d1d9; }
                """)
                
            toolbar_layout.addWidget(self.project_label)
            toolbar_layout.addStretch()
            toolbar_layout.addWidget(self.btn_new_file)
            toolbar_layout.addWidget(self.btn_new_folder)
            toolbar_layout.addWidget(self.btn_refresh)
            
            explorer_layout.addWidget(self.explorer_toolbar)
            
            # The Empty State "Open Folder" button
            self.open_folder_btn = QPushButton("Open Folder")
            self.open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.open_folder_btn.setStyleSheet("""
                QPushButton { background-color: #0e639c; color: #ffffff; border-radius: 4px; padding: 6px 14px; font-weight: bold; font-size: 13px; margin: 20px; }
                QPushButton:hover { background-color: #1177bb; }
            """)
            self.open_folder_btn.clicked.connect(self.prompt_open_folder)
            explorer_layout.addWidget(self.open_folder_btn)
            explorer_layout.setAlignment(self.open_folder_btn, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            
            self.tree_view = QTreeView()
            self.tree_view.setObjectName("explorerTree")
            self.tree_view.setModel(self.file_model)
            self.tree_view.setHeaderHidden(True)
            for i in range(1, 4):
                self.tree_view.hideColumn(i)
            self.tree_view.setExpandsOnDoubleClick(False)
            self.tree_view.doubleClicked.connect(self.on_file_double_clicked)
            self.tree_view.clicked.connect(self.on_file_clicked)
            self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.tree_view.customContextMenuRequested.connect(self.show_explorer_context_menu)
            
            explorer_layout.addWidget(self.tree_view)
            
            if self.is_empty_workspace:
                self.tree_view.hide()
                self.btn_new_file.hide()
                self.btn_new_folder.hide()
                self.btn_refresh.hide()
            else:
                self.open_folder_btn.hide()
                self.tree_view.setRootIndex(self.file_model.index(cwd))
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
        
        from lmms.gui.widgets.title_bar import ChatDockTitleBar
        self.chat_dock.setTitleBarWidget(ChatDockTitleBar(self.chat_dock, self.chat_page))
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
        
        # Set Dock Dimensions
        for dock in self.docks.values():
            dock.setMinimumWidth(170)
            dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable | QDockWidget.DockWidgetFeature.DockWidgetMovable)
            
            # Remove title bar from left docks to save space? The user asked for "Title Bar" height 30px,
            # which we applied to the Menu Bar. We will leave dock title bars alone for now.

        # Add Docks - Initial Default Layout
        self.inner_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.explorer_dock)
        self.inner_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.search_dock)
        self.inner_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.model_dock)
        self.inner_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.chat_dock)
        
        # Set default width for left docks to 250px
        self.inner_window.resizeDocks(
            [self.explorer_dock, self.search_dock, self.model_dock],
            [250, 250, 250],
            Qt.Orientation.Horizontal
        )

        # Sidebar Buttons
        self.nav_buttons = {}
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        logo_path = os.path.join(assets_dir, "lmms_logo.png")
        nav_items = [
            ("📁", "Explorer", os.path.join(assets_dir, "icon_explorer.svg")),
            ("🔍", "Search", os.path.join(assets_dir, "icon_search.svg")),
            ("📦", "Models", os.path.join(assets_dir, "icon_models.svg")),
            ("⚙", "Settings", os.path.join(assets_dir, "icon_settings.svg")),
        ]
        
        def load_svg_icon(path, size=24):
            try:
                from PyQt6.QtSvg import QSvgRenderer # type: ignore
                renderer = QSvgRenderer(path)
                if not renderer.isValid():
                    return None
                    
                def render_colored(color_hex):
                    pixmap = QPixmap(size, size)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    renderer.render(painter)
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                    painter.fillRect(pixmap.rect(), QColor(color_hex))
                    painter.end()
                    return pixmap

                icon = QIcon()
                icon.addPixmap(render_colored("#8b949e"), QIcon.Mode.Normal, QIcon.State.Off) # Normal grey
                icon.addPixmap(render_colored("#ffffff"), QIcon.Mode.Normal, QIcon.State.On)  # Active white
                # Active mode is used for hover in some themes
                icon.addPixmap(render_colored("#c9d1d9"), QIcon.Mode.Active, QIcon.State.Off)
                icon.addPixmap(render_colored("#ffffff"), QIcon.Mode.Active, QIcon.State.On)
                return icon
            except ImportError:
                return QIcon(path)

        for text_icon, name, custom_icon_path in nav_items:
            btn = QPushButton(text_icon if not custom_icon_path else "")
            if custom_icon_path and os.path.exists(custom_icon_path):
                svg_icon = load_svg_icon(custom_icon_path, 24)
                if svg_icon:
                    btn.setIcon(svg_icon)
                else:
                    btn.setIcon(QIcon(custom_icon_path))
                
                # VS Code activity bar icons are typically 24x24
                from PyQt6.QtCore import QSize
                btn.setIconSize(QSize(24, 24))
                
            btn.setToolTip(name)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setFixedSize(48, 48) # Match sidebar width so it fills horizontally
            btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background-color: transparent;
                    border-left: 2px solid transparent;
                }
                QPushButton:hover {
                    background-color: #2b2d31;
                }
                QPushButton:checked {
                    border-left: 2px solid #58a6ff;
                }
            """)
            
            # Special case for Settings since we removed the dock
            if name == "Settings":
                btn.clicked.connect(lambda checked: CommandRegistry.execute("settings.providers"))
            else:
                btn.clicked.connect(lambda checked, n=name, b=btn: self.toggle_dock(n, b))
                # Connect visibility changed to update button state
                self.docks[name].visibilityChanged.connect(lambda visible, b=btn: b.setChecked(visible))
                # Sync initial state
                btn.setChecked(self.docks[name].isVisible())
            
            sidebar_layout.addWidget(btn)
            if name != "Settings":
                self.nav_buttons[name] = btn

        sidebar_layout.addStretch()

        # Add to main layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.inner_window)

        # Wrap with Title Bar
        from lmms.gui.widgets.title_bar import CustomTitleBar
        self.title_bar = CustomTitleBar(self, self.menu_bar_widget)
        
        # Connect Toggles
        self.title_bar.btn_toggle_left.clicked.connect(self.toggle_left_panel)
        self.title_bar.btn_toggle_right.clicked.connect(self.toggle_right_panel)

        container_widget = QWidget()
        container_layout = QVBoxLayout(container_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(self.title_bar)
        container_layout.addWidget(main_widget)

        self.setCentralWidget(container_widget)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setFixedHeight(22)
        self.status_bar.setStyleSheet("background-color: #161b22; color: #8b949e; border-top: 1px solid #30363d; padding-left: 10px; font-size: 11px;")
        self.setStatusBar(self.status_bar)
        
        self.status_file_info = QLabel("Ready")
        self.status_ai_info = QLabel("AI: Idle | Model: default")
        self.status_bar.addWidget(self.status_file_info)
        self.status_bar.addPermanentWidget(self.status_ai_info)
        
        # Auto-manage Chat visibility based on tab context
        self.editor_manager.tabs.currentChanged.connect(self.on_editor_tab_changed)

    def toggle_left_panel(self):
        if self.explorer_dock.isVisible():
            self.explorer_dock.hide()
            if "Explorer" in self.nav_buttons:
                self.nav_buttons["Explorer"].setChecked(False)
        else:
            self.explorer_dock.show()
            self.explorer_dock.raise_()
            if "Explorer" in self.nav_buttons:
                self.nav_buttons["Explorer"].setChecked(True)

    def toggle_right_panel(self):
        if self.chat_dock.isVisible():
            self.chat_dock.hide()
            if "Chats" in self.nav_buttons:
                self.nav_buttons["Chats"].setChecked(False)
        else:
            self.chat_dock.show()
            self.chat_dock.raise_()
            if "Chats" in self.nav_buttons:
                self.nav_buttons["Chats"].setChecked(True)

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
        
        left_docks = ["Explorer", "Search", "Models"]
        if name in left_docks:
            # Hide other left docks to simulate sidebar tabs
            if not dock.isVisible():
                for other in left_docks:
                    if other != name and other in self.docks and self.docks[other].isVisible():
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

    def prompt_open_folder(self):
        folder = ""
        import sys, os
        use_zenity = False
        if sys.platform.startswith("linux"):
            import subprocess, shutil
            if shutil.which('zenity'):
                use_zenity = True
                try:
                    result = subprocess.run(['zenity', '--file-selection', '--directory', '--title=Open Folder'], capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout.strip():
                        folder = result.stdout.strip()
                except Exception:
                    use_zenity = False # Fallback if zenity fails to run
                
        if not use_zenity and not folder:
            from PyQt6.QtWidgets import QFileDialog
            folder = QFileDialog.getExistingDirectory(self, "Open Folder", os.path.expanduser("~"))
            
        if folder:
            self.is_empty_workspace = False
            self.file_model.setRootPath(folder)
            project_name = os.path.basename(folder)
            if not project_name: project_name = folder
            self.project_label.setText(project_name.upper())
            
            self.open_folder_btn.hide()
            self.tree_view.show()
            self.btn_new_file.show()
            self.btn_new_folder.show()
            self.btn_refresh.show()
            self.tree_view.setRootIndex(self.file_model.index(folder))
            
            # Change actual working directory so terminal and new files default to it
            os.chdir(folder)

    def get_selected_explorer_path(self):
        if not hasattr(self, 'tree_view'): return os.getcwd()
        idx = self.tree_view.currentIndex()
        if idx.isValid() and hasattr(self, 'file_model'):
            return self.file_model.filePath(idx)
        if hasattr(self, 'file_model') and self.file_model.rootPath():
            return self.file_model.rootPath()
        return os.getcwd()

    def create_new_file(self):
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        path = self.get_selected_explorer_path()
        if os.path.isfile(path): path = os.path.dirname(path)
        name, ok = QInputDialog.getText(self, "New File", "Enter file name:")
        if ok and name:
            try:
                file_path = os.path.join(path, name)
                open(file_path, 'w').close()
                self.editor_manager.open_file(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error creating file: {e}")
                
    def create_new_folder(self):
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        path = self.get_selected_explorer_path()
        if os.path.isfile(path): path = os.path.dirname(path)
        name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and name:
            try:
                os.makedirs(os.path.join(path, name), exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error creating folder: {e}")

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
