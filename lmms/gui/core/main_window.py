# Made by markanm
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QPushButton, QLabel, QSplitter,
    QTreeView, QTabWidget, QTextEdit, QDockWidget, QMenu, QStatusBar, QFrame, QLineEdit
)
from PyQt6.QtCore import Qt, QSize, QPoint, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QIcon, QFont, QCursor, QColor, QPixmap, QPainter

from lmms.backend.config.config import ConfigManager
import os
import re
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
from lmms.packages.qt_vscode_icons import VscodeIconProvider  # type: ignore[import]
from lmms.gui.panels.search_panel import SearchPanel
from lmms.gui.widgets.model_browser import ModelBrowser, ModelDetailsTab
from lmms.gui.panels.terminal_panel import TerminalPanel
from lmms.backend.services.workspace_service import WorkspaceService
from lmms.gui.widgets.menu import LMMsMenuBar
from lmms.gui.panels.source_control_panel import SourceControlPanel
from lmms.gui.panels.extensions_panel import ExtensionsPanel

# State Management & Notifications
from lmms.backend.logic.manager import BackendManager
from lmms.gui.state.manager import GUIStateManager
from lmms.gui.notifications.manager import NotificationManager

# Removed InlineInput class

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
        
        # Initialize Extension Manager
        from lmms.extensions.manager import ExtensionManager
        self.ext_manager = ExtensionManager.instance()
        self.ext_manager.set_workspace_root(ConfigManager().get("workspace_dir", os.getcwd()))
        
        self.ext_manager.extension_ui_registered.connect(self.on_extension_ui_registered)
        self.ext_manager.extension_js_activation.connect(self.on_extension_js_activation)
        
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

        # Heartbeat to keep Engine alive
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(self.ping_engine)
        self.heartbeat_timer.start(5000)

    def ping_engine(self):
        import requests
        from PyQt6.QtCore import QThread
        
        class PingThread(QThread):
            def run(self):
                try:
                    requests.post("http://127.0.0.1:11435/v1/internal/ping", timeout=2)
                except Exception:
                    pass
                    
        self._ping_thread = PingThread(self)
        self._ping_thread.start()


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
        
        # Central Widget: Multi-tab Editor and Terminal in a Splitter
        self.editor_manager = EditorManager()
        
        self.central_splitter = QSplitter(Qt.Orientation.Vertical)
        self.central_splitter.setChildrenCollapsible(False)
        self.central_splitter.addWidget(self.editor_manager)
        
        self.inner_window.setCentralWidget(self.central_splitter)

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
            from PyQt6.QtCore import QDir
            self.file_model = QFileSystemModel()
            self.file_model.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.Hidden)
            self.file_model.setReadOnly(False)
            self.file_model.setIconProvider(VscodeIconProvider())
            self.file_model.fileRenamed.connect(self.on_file_renamed)
            cwd = ConfigManager().get("workspace_dir", os.getcwd())
            if not os.path.exists(cwd):
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
            
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
            
            self.btn_new_file = QPushButton()
            self.btn_new_file.setIcon(QIcon(os.path.join(assets_dir, "icon_new_file.svg").replace("\\", "/")))
            self.btn_new_file.setToolTip("New File")
            self.btn_new_file.clicked.connect(self.create_new_file)
            
            self.btn_new_folder = QPushButton()
            self.btn_new_folder.setIcon(QIcon(os.path.join(assets_dir, "icon_new_folder.svg").replace("\\", "/")))
            self.btn_new_folder.setToolTip("New Folder")
            self.btn_new_folder.clicked.connect(self.create_new_folder)
            
            self.btn_refresh = QPushButton()
            self.btn_refresh.setIcon(QIcon(os.path.join(assets_dir, "icon_refresh.svg").replace("\\", "/")))
            self.btn_refresh.setToolTip("Refresh Explorer")
            self.btn_refresh.clicked.connect(lambda: self.file_model.setRootPath(self.file_model.rootPath()))
            
            for btn in [self.btn_new_file, self.btn_new_folder, self.btn_refresh]:
                btn.setFixedSize(24, 24)
                btn.setIconSize(QSize(16, 16))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton { background: transparent; border: none; border-radius: 4px; padding: 0px; }
                    QPushButton:hover { background: #30363d; }
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
            
            from lmms.gui.utils.diagnostic_manager import DiagnosticManager
            from PyQt6.QtCore import QIdentityProxyModel
            
            class DiagnosticProxyModel(QIdentityProxyModel):
                def data(self, proxy_index, role=Qt.ItemDataRole.DisplayRole):
                    if role == Qt.ItemDataRole.ForegroundRole:
                        source_index = self.mapToSource(proxy_index)
                        if hasattr(self.sourceModel(), 'filePath'):
                            file_path = self.sourceModel().filePath(source_index)
                            if DiagnosticManager.get_instance().has_errors(file_path):
                                return QColor("#f14c4c") # error_color
                    return super().data(proxy_index, role)
                    
            self.diagnostic_model = DiagnosticProxyModel(self)
            self.diagnostic_model.setSourceModel(self.file_model)
            
            from PyQt6.QtWidgets import QStyledItemDelegate
            from PyQt6.QtGui import QPainter
            class ExplorerItemDelegate(QStyledItemDelegate):
                def __init__(self, main_window, parent=None):
                    super().__init__(parent)
                    self.main_window = main_window
                    
                def paint(self, painter, option, index):
                    super().paint(painter, option, index)
                    
                    # Check dirty state
                    if hasattr(index.model(), 'sourceModel'):
                        proxy_model = index.model()
                        source_index = proxy_model.mapToSource(index)
                        file_model = proxy_model.sourceModel()
                        if hasattr(file_model, 'filePath'):
                            file_path = file_model.filePath(source_index)
                            
                            # Is it dirty?
                            editor_mgr = self.main_window.editor_manager
                            editor = editor_mgr.open_files.get(file_path)
                            if editor and getattr(editor, 'is_dirty', False):
                                # Draw dirty dot (white or accent color)
                                painter.save()
                                painter.setBrush(QColor("#e5e7eb"))
                                painter.setPen(Qt.PenStyle.NoPen)
                                # Draw dot on the right side
                                radius = 4
                                rect = option.rect
                                painter.drawEllipse(rect.right() - 10, rect.center().y() - radius//2, radius, radius)
                                painter.restore()
                                
            self.tree_delegate = ExplorerItemDelegate(self, self.tree_view)
            self.tree_view.setItemDelegate(self.tree_delegate)
            
            DiagnosticManager.get_instance().diagnostics_updated.connect(
                lambda: self.diagnostic_model.layoutChanged.emit()
            )
            
            # Repaint for dirty dots
            self.editor_manager.file_saved.connect(
                lambda p: self.diagnostic_model.layoutChanged.emit()
            )
            self.editor_manager.file_dirty.connect(
                lambda p: self.diagnostic_model.layoutChanged.emit()
            )
            self.editor_manager.run_action_requested.connect(self.on_run_action_requested)
            
            self.tree_view.setModel(self.diagnostic_model)
            self.tree_view.setHeaderHidden(True)
            self.tree_view.setIndentation(14)
            
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
            closed_icon = os.path.join(assets_dir, "branch_closed.svg").replace("\\", "/")
            open_icon = os.path.join(assets_dir, "branch_open.svg").replace("\\", "/")
            
            self.tree_view.setStyleSheet(f"""
                QTreeView {{
                    background-color: transparent;
                    color: #cccccc;
                    border: none;
                    outline: none;
                    font-family: 'Segoe UI', 'San Francisco', sans-serif;
                    font-size: 13px;
                }}
                QTreeView QLineEdit {{
                    background-color: #252526;
                    color: #cccccc;
                    border: 1px solid #007fd4;
                    padding: 0px 2px;
                    selection-background-color: #062f4a;
                }}
                QTreeView::item {{
                    padding: 3px 0px;
                }}
                QTreeView::item:selected {{
                    background-color: #37373d;
                    color: #ffffff;
                }}
                QTreeView::item:hover:!selected {{
                    background-color: #2a2d2e;
                }}
                QTreeView::branch:has-siblings:!adjoins-item {{
                    border-left: 1px solid #404040;
                }}
                QTreeView::branch:has-siblings:adjoins-item {{
                    border-left: 1px solid #404040;
                }}
                QTreeView::branch:!has-children:!has-siblings:adjoins-item {{
                    border-left: 1px solid #404040;
                }}
                QTreeView::branch:has-children:!has-siblings:closed,
                QTreeView::branch:closed:has-children:has-siblings {{
                    border-image: none;
                    image: url("{closed_icon}");
                }}
                QTreeView::branch:open:has-children:!has-siblings,
                QTreeView::branch:open:has-children:has-siblings {{
                    border-image: none;
                    image: url("{open_icon}");
                }}
            """)
            
            for i in range(1, 4):
                self.tree_view.hideColumn(i)
            self.tree_view.setExpandsOnDoubleClick(False)
            self.tree_view.doubleClicked.connect(self.on_file_double_clicked)
            self.tree_view.clicked.connect(self.on_file_clicked)
            self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.tree_view.customContextMenuRequested.connect(self.show_explorer_context_menu)
            
            # Explorer Splitter
            self.explorer_splitter = QSplitter(Qt.Orientation.Vertical)
            self.explorer_splitter.setChildrenCollapsible(False)
            
            # File Tree wrapper to give it a title
            file_tree_wrapper = QWidget()
            file_tree_layout = QVBoxLayout(file_tree_wrapper)
            file_tree_layout.setContentsMargins(0, 0, 0, 0)
            file_tree_layout.setSpacing(0)
            file_title = QLabel("FILES")
            file_title.setStyleSheet("color: #cccccc; font-weight: bold; font-size: 11px; padding: 4px 10px; background: #252526;")
            file_tree_layout.addWidget(file_title)
            file_tree_layout.addWidget(self.tree_view)
            
            self.explorer_splitter.addWidget(file_tree_wrapper)
            
            # Outline Tree
            self.outline_tree_view = QTreeView()
            self.outline_tree_view.setObjectName("outlineTree")
            self.outline_tree_view.setHeaderHidden(True)
            self.outline_tree_view.setIndentation(15)
            self.outline_tree_view.setStyleSheet(self.tree_view.styleSheet())
            
            from PyQt6.QtGui import QStandardItemModel, QStandardItem
            self.outline_model = QStandardItemModel()
            self.outline_tree_view.setModel(self.outline_model)
            self.outline_tree_view.doubleClicked.connect(self.on_outline_item_double_clicked)
            
            outline_wrapper = QWidget()
            outline_layout = QVBoxLayout(outline_wrapper)
            outline_layout.setContentsMargins(0, 0, 0, 0)
            outline_layout.setSpacing(0)
            outline_title = QLabel("OUTLINE")
            outline_title.setStyleSheet("color: #cccccc; font-weight: bold; font-size: 11px; padding: 4px 10px; background: #252526;")
            outline_layout.addWidget(outline_title)
            outline_layout.addWidget(self.outline_tree_view)
            
            self.explorer_splitter.addWidget(outline_wrapper)
            self.explorer_splitter.setSizes([600, 400])
            
            explorer_layout.addWidget(self.explorer_splitter)
            
            # Connect EditorManager's outline updates
            self.editor_manager.outline_updated.connect(self.on_outline_updated)
            self.editor_manager.tabs.currentChanged.connect(self.on_editor_tab_changed_outline)
            
            # Removed inline input connection
            
            if self.is_empty_workspace:
                self.tree_view.hide()
                self.btn_new_file.hide()
                self.btn_new_folder.hide()
                self.btn_refresh.hide()
            else:
                self.open_folder_btn.hide()
                source_idx = self.file_model.index(cwd)
                proxy_idx = self.diagnostic_model.mapFromSource(source_idx)
                self.tree_view.setRootIndex(proxy_idx)
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
        
        # 5. Source Control Dock
        self.source_control_dock = SourceControlPanel(self.inner_window)
        self.source_control_dock.setObjectName("SourceControlDock")
        self.docks["Source Control"] = self.source_control_dock
        self.source_control_dock.hide()

        # 6. Extensions Dock
        self.extensions_dock = ExtensionsPanel(self.inner_window)
        self.extensions_dock.setObjectName("ExtensionsDock")
        self.docks["Extensions"] = self.extensions_dock
        self.extensions_dock.hide()
        # Wire: click on extension → open detail tab in main editor area
        self.extensions_dock.open_detail_requested.connect(self._open_extension_detail)

        # Init Source Control Workspace
        if not self.is_empty_workspace and hasattr(self.source_control_dock, 'set_workspace'):
            cwd = ConfigManager().get("workspace_dir", os.getcwd())
            if os.path.exists(cwd):
                self.source_control_dock.set_workspace(cwd)
        
        # Set Dock Dimensions
        for dock in self.docks.values():
            dock.setMinimumWidth(170)
            dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable | QDockWidget.DockWidgetFeature.DockWidgetMovable)
            
            # Remove title bar from left docks to save space? The user asked for "Title Bar" height 30px,
            # which we applied to the Menu Bar. We will leave dock title bars alone for now.

        # Add Docks - Initial Default Layout
        self.inner_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.explorer_dock)
        self.inner_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.search_dock)
        self.inner_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.source_control_dock)
        self.inner_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.extensions_dock)
        self.inner_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.model_dock)
        self.inner_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.chat_dock)
        
        # Set default width for docks — match VS Code proportions
        # Explorer ~18-20%, Chat ~26%, Bottom panel ~28% height
        screen_w = 1280 # assume 1280px default window
        explorer_w = int(screen_w * 0.19) # ~242px
        chat_w = int(screen_w * 0.26)     # ~333px
        self.inner_window.resizeDocks(
            [self.explorer_dock, self.search_dock, self.source_control_dock, self.extensions_dock, self.model_dock],
            [explorer_w, explorer_w, explorer_w, explorer_w, explorer_w],
            Qt.Orientation.Horizontal
        )
        self.inner_window.resizeDocks(
            [self.chat_dock],
            [chat_w],
            Qt.Orientation.Horizontal
        )
        
        # 5. Bottom Panel (unified — TerminalPanel now includes Phase 5 tabs)
        from lmms.gui.utils.dap_manager import DAPManager
        
        self.dap_manager = DAPManager(["python3", "-m", "debugpy.adapter"])
        
        self.terminal_panel = TerminalPanel(self)
        self.terminal_panel.set_dap_manager(self.dap_manager)
        
        # Keep bottom_panel as an alias so existing references still work
        self.bottom_panel = self.terminal_panel
        
        self.central_splitter.addWidget(self.terminal_panel)
        
        # Wire Problems Tab double clicks to Editor Manager
        self.terminal_panel.problems_tab.diagnostic_clicked.connect(self.editor_manager.open_file)
        
        # Wire file dirty counter to ChatPage's Review Changes button
        def on_file_dirty(file_path):
            count = sum(1 for e in self.editor_manager.open_files.values() if getattr(e, 'is_dirty', False))
            self.chat_page.set_dirty_count(count)
        
        def on_file_saved(file_path):
            count = sum(1 for e in self.editor_manager.open_files.values() if getattr(e, 'is_dirty', False))
            self.chat_page.set_dirty_count(count)
        
        self.editor_manager.file_dirty.connect(on_file_dirty)
        self.editor_manager.file_saved.connect(on_file_saved)
        
        # Set default sizes for the splitter — 72% editor, 28% bottom panel
        self.central_splitter.setSizes([720, 280])

        # Sidebar Buttons
        self.nav_buttons = {}
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        logo_path = os.path.join(assets_dir, "lmms_logo.png")
        nav_items = [
            ("📁", "Explorer", os.path.join(assets_dir, "icon_explorer.svg")),
            ("🔍", "Search", os.path.join(assets_dir, "icon_search.svg")),
            ("🌿", "Source Control", os.path.join(assets_dir, "icon_source_control.svg")),
            ("🧩", "Extensions", os.path.join(assets_dir, "icon_extensions.svg")),
            ("📦", "Models", os.path.join(assets_dir, "icon_models.svg")),
            ("⚙", "Settings", os.path.join(assets_dir, "icon_settings.svg")),
        ]
        
        self._sidebar_layout = sidebar_layout
        sidebar_layout.addStretch()
        for text_icon, name, custom_icon_path in nav_items:
            self._add_nav_item(text_icon, name, custom_icon_path)

        # Add to main layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.inner_window)

        # Wrap with Title Bar
        from lmms.gui.widgets.title_bar import CustomTitleBar
        self.title_bar = CustomTitleBar(self, self.menu_bar_widget)
        
        # Connect Toggles
        self.title_bar.btn_toggle_left.clicked.connect(self.toggle_left_panel)
        self.title_bar.btn_toggle_bottom.clicked.connect(self.toggle_bottom_panel)
        self.title_bar.btn_toggle_right.clicked.connect(self.toggle_right_panel)

        container_widget = QWidget()
        container_layout = QVBoxLayout(container_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(self.title_bar)
        container_layout.addWidget(main_widget)

        self.setCentralWidget(container_widget)
        
        # Status Bar
        from lmms.gui.widgets.status_bar import CustomStatusBar
        self.custom_status_bar = CustomStatusBar(self)
        self.setStatusBar(None) # Remove default
        container_layout.addWidget(self.custom_status_bar)
        
        # Wire git_manager from SourceControlPanel
        if hasattr(self, 'source_control_dock') and hasattr(self.source_control_dock, 'git_manager'):
            self.custom_status_bar.set_git_manager(self.source_control_dock.git_manager)
        
        self.editor_manager.cursor_position_changed.connect(self.custom_status_bar.update_cursor_position)
        self.editor_manager.file_context_changed.connect(self.custom_status_bar.update_file_context)
        
        # Auto-manage Chat visibility based on tab context
        self.editor_manager.tabs.currentChanged.connect(self.on_editor_tab_changed)
        
        # Command Palette Shortcut
        from PyQt6.QtGui import QShortcut, QKeySequence
        self.cmd_palette_shortcut = QShortcut(QKeySequence("Ctrl+Shift+P"), self)
        self.cmd_palette_shortcut.activated.connect(self.open_command_palette)

    def open_command_palette(self):
        editor = self.editor_manager.get_active_editor()
        if editor and hasattr(editor, 'open_command_palette'):
            editor.open_command_palette()

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

    def on_run_action_requested(self, action_type, file_path):
        import os
        import subprocess
        ext = os.path.splitext(file_path)[1].lower()
        cmd = ""
        
        if ext == ".py":
            cmd = f'python "{file_path}"'
        elif ext == ".dart":
            cmd = f'dart run "{file_path}"'
        elif ext == ".js":
            cmd = f'node "{file_path}"'
        elif ext == ".html":
            cmd = f'xdg-open "{file_path}"' if os.name == 'posix' else f'start "" "{file_path}"'
        else:
            # Fallback based on shebang or just execute
            cmd = f'./"{file_path}"'
            
        if action_type == "integrated":
            self.bottom_panel.setVisible(True)
            self.terminal_panel.setFocus()
            self.terminal_panel.send_command(cmd)
        elif action_type == "dedicated":
            import sys
            # Open OS terminal
            if sys.platform == "win32":
                subprocess.Popen(['start', 'cmd', '/k', cmd], shell=True)
            elif sys.platform == "darwin":
                subprocess.Popen(['open', '-a', 'Terminal.app', file_path])
            else:
                # Basic gnome-terminal, fallback to xterm
                try:
                    subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', f'{cmd}; exec bash'])
                except:
                    subprocess.Popen(['xterm', '-e', f'{cmd}; bash'])
        elif action_type == "debug":
            # For now, start with Python pdb
            if ext == ".py":
                self.bottom_panel.setVisible(True)
                self.terminal_panel.setFocus()
                self.terminal_panel.send_command(f'python -m pdb "{file_path}"')
        elif action_type == "task":
            # Placeholder for task runner
            self.bottom_panel.setVisible(True)
            self.terminal_panel.setFocus()
            self.terminal_panel.send_command(f'echo "Running task for {os.path.basename(file_path)}"')

    def on_editor_tab_changed(self, index):
        editor = self.editor_manager.get_active_editor()
        if editor and hasattr(editor, "file_path"):
            self.status_bar.update_file_status(editor.file_path)
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
    def _load_svg_icon(self, path, size=24):
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

    def _add_nav_item(self, text_icon, name, custom_icon_path, is_extension=False):
        btn = QPushButton(text_icon if not custom_icon_path else "")
        if custom_icon_path and os.path.exists(custom_icon_path):
            svg_icon = self._load_svg_icon(custom_icon_path, 24)
            if svg_icon:
                btn.setIcon(svg_icon)
            else:
                btn.setIcon(QIcon(custom_icon_path))
            
            # VS Code activity bar icons are typically 24x24
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
        
        # Settings handled specially, or toggle dock
        if name == "Settings":
            btn.clicked.connect(lambda checked: CommandRegistry.execute("settings.providers"))
        else:
            if is_extension and name not in self.docks:
                # Real extension docks should render an actual extension detail page,
                # not a dead placeholder. If no extension-specific UI exists yet,
                # we still render the extension metadata view so the pane is usable.
                dock = QDockWidget(name, self.inner_window)
                dock.setObjectName(f"{name}Dock")
                dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)

                from lmms.gui.panels.extensions_panel import ExtensionDetailTab
                slug = re.sub(r"[^a-z0-9]+", "-", (name or "extension").lower()).strip("-") or "extension"
                ext_meta = {
                    "namespace": "local",
                    "name": slug,
                    "displayName": name,
                    "description": "Extension is loaded through the runtime manager. The extension detail panel is available here.",
                    "version": "0.0.0",
                    "downloadCount": 0,
                    "files": {"icon": "", "readme": ""},
                    "categories": ["general"],
                }

                # If an installed extension record already exists, prefer its real metadata.
                from lmms.extensions.manager import ExtensionManager
                mgr = ExtensionManager.instance()
                for ext_id, rec in getattr(mgr, "_records", {}).items():
                    record_name = rec.name if hasattr(rec, "name") else ""
                    if record_name and record_name.lower() == name.lower():
                        ext_meta = {
                            "namespace": ext_id.split(".", 1)[0],
                            "name": ext_id.split(".", 1)[1],
                            "displayName": getattr(rec, "display_name", record_name),
                            "description": getattr(rec, "description", rec.summary or ""),
                            "version": getattr(rec, "version", "0.0.0"),
                            "downloadCount": getattr(rec, "downloads", 0),
                            "files": getattr(rec, "files", {}) or {"icon": ""},
                            "categories": getattr(rec, "categories", []) or ["general"],
                        }
                        break

                detail_tab = ExtensionDetailTab(ext_meta)
                dock.setWidget(detail_tab)

                self.inner_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
                dock.hide()
                self.docks[name] = dock
                
            btn.clicked.connect(lambda checked, n=name, b=btn: self.toggle_dock(n, b))
            # Connect visibility changed to update button state
            if name in self.docks:
                self.docks[name].visibilityChanged.connect(lambda visible, b=btn: b.setChecked(visible))
                # Sync initial state
                btn.setChecked(self.docks[name].isVisible())
        
        if name == "Settings":
            # Add after stretch
            self._sidebar_layout.addWidget(btn)
        else:
            # Insert before the stretch (which is the first stretch added)
            # Find the stretch index. It's usually count() - 1, but we might have Settings at the end.
            # A simpler way: we know items are added in order, we can insert at layout.count() - 1 
            # if we assume stretch is at count - 1. But wait! If Settings is already added?
            # Actually, Settings is always the last item in `nav_items`.
            # So when Explorer, Search, etc. are added, Settings is not there yet.
            # But for extensions added later dynamically, Settings IS there!
            # So we should insert before the stretch. How to find stretch? 
            # `self._sidebar_layout.count()` contains elements. 
            # Let's just find the index of the stretch or just insert before Settings.
            # Actually, `count() - 1` without Settings was inserting before stretch (if stretch was there).
            # If Settings is present, the last item is Settings, the second to last is Stretch.
            # But wait! For dynamic extensions, we want to insert them at the end of the top group.
            # Let's find the stretch index dynamically or keep it simple: insert before stretch.
            stretch_index = -1
            for i in range(self._sidebar_layout.count()):
                item = self._sidebar_layout.itemAt(i)
                if item and item.spacerItem():
                    stretch_index = i
                    break
            
            if stretch_index >= 0:
                self._sidebar_layout.insertWidget(stretch_index, btn)
            else:
                self._sidebar_layout.insertWidget(self._sidebar_layout.count() - 1, btn)

        if name != "Settings":
            self.nav_buttons[name] = btn


    def toggle_dock(self, name, button):
        dock = self.docks[name]
        
        left_docks = ["Explorer", "Search", "Source Control", "Extensions", "Models"]
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
        
        if index.isValid():
            file_path = self.file_model.filePath(index)
            is_dir = self.file_model.isDir(index)
        else:
            file_path = self.file_model.rootPath()
            is_dir = True

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #252526; color: #cccccc; border: 1px solid #454545; padding: 4px; font-family: 'Segoe UI', 'San Francisco', sans-serif; font-size: 13px; }
            QMenu::item { padding: 4px 24px 4px 24px; border-radius: 4px; }
            QMenu::item:selected { background-color: #04395e; color: #ffffff; }
            QMenu::separator { height: 1px; background-color: #454545; margin: 4px 0px; }
        """)

        action_new_file = menu.addAction("New File...")
        action_new_folder = menu.addAction("New Folder...")
        menu.addSeparator()

        action_open_side = None
        if index.isValid() and not is_dir:
            action_open_side = menu.addAction("Open to the Side")

        action_open_containing = menu.addAction("Reveal in File Explorer")
        action_open_terminal = menu.addAction("Open in Integrated Terminal")
        
        menu.addSeparator()
        action_cut = menu.addAction("Cut")
        action_copy = menu.addAction("Copy")
        action_paste = menu.addAction("Paste")
        menu.addSeparator()
        action_copy_path = menu.addAction("Copy Path")
        action_copy_rel = menu.addAction("Copy Relative Path")
        menu.addSeparator()
        action_rename = menu.addAction("Rename...")
        action_delete = menu.addAction("Delete")
        
        action = menu.exec(self.tree_view.viewport().mapToGlobal(position))
        
        if not action:
            return

        import os
        import subprocess
        import sys
        from PyQt6.QtWidgets import QApplication
        
        clipboard = QApplication.clipboard()

        if action == action_new_file:
            self.create_new_file()
        elif action == action_new_folder:
            self.create_new_folder()
        elif action == action_open_side:
            if hasattr(self, 'editor_manager'):
                self.editor_manager.open_file(file_path)
        elif action == action_open_containing:
            target = file_path if is_dir else os.path.dirname(file_path)
            if sys.platform == "win32":
                os.startfile(target)
            elif sys.platform == "darwin":
                subprocess.Popen(['open', target])
            else:
                subprocess.Popen(['xdg-open', target])
        elif action == action_open_terminal:
            if hasattr(self, 'terminal_panel') and self.terminal_panel:
                self.terminal_panel.setFocus()
        elif action == action_copy_path:
            clipboard.setText(file_path)
        elif action == action_copy_rel:
            rel = os.path.relpath(file_path, self.file_model.rootPath())
            clipboard.setText(rel)
        elif action == action_rename and index.isValid():
            self.tree_view.setCurrentIndex(index)
            self.tree_view.edit(index)
        elif action == action_delete and index.isValid():
            self.file_model.remove(index)

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

    def _open_extension_detail(self, ext: dict):
        """Open a VS Code-style extension detail page in the main editor tab area."""
        from lmms.gui.panels.extensions_panel import ExtensionDetailTab
        name = ext.get("displayName") or ext.get("name", "Extension")
        ns   = ext.get("namespace", "")
        identifier = f"ext:{ns}.{ext.get('name', '')}"
        # Reuse tab if already open
        if hasattr(self.editor_manager, "custom_tabs") and identifier in self.editor_manager.custom_tabs:
            self.editor_manager.tabs.setCurrentWidget(
                self.editor_manager.custom_tabs[identifier]
            )
            return
        tab = ExtensionDetailTab(ext)
        self.editor_manager.open_custom_tab(tab, f"Extension: {name}", identifier)

    def on_file_double_clicked(self, index):
        if not hasattr(self, 'file_model') or self.file_model is None:
            return
        file_path = self.file_model.filePath(index)
        if not self.file_model.isDir(index):
            self.editor_manager.open_file(file_path)

    def on_outline_item_double_clicked(self, index):
        item = self.outline_model.itemFromIndex(index)
        if item:
            line = item.data(Qt.ItemDataRole.UserRole + 1)
            col = item.data(Qt.ItemDataRole.UserRole + 2)
            if line is not None and col is not None:
                editor = self.editor_manager.get_active_editor()
                if editor and hasattr(editor, 'jump_to'):
                    # Monaco jump_to expects 0-indexed line/col
                    editor.jump_to(line - 1, col - 1)

    def on_editor_tab_changed_outline(self, index):
        # Request outline for new tab
        editor = self.editor_manager.get_active_editor()
        if editor and hasattr(editor, 'request_outline'):
            editor.request_outline()
        else:
            from PyQt6.QtGui import QStandardItem
            self.outline_model.clear()
            item = QStandardItem("No outline available")
            self.outline_model.appendRow(item)

    def on_outline_updated(self, file_path, json_data):
        # Make sure this outline is for the currently active editor
        editor = self.editor_manager.get_active_editor()
        if not editor or editor.property("file_path") != file_path:
            return
            
        import json
        from PyQt6.QtGui import QStandardItem
        try:
            symbols = json.loads(json_data)
            self.outline_model.clear()
            
            def get_symbol_icon(kind):
                from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
                from PyQt6.QtCore import Qt
                
                # Map kind to (character, color) based on VS Code defaults
                mapping = {
                    1: ('F', '#cccccc'), 2: ('{}', '#cccccc'), 3: ('{}', '#cccccc'), 4: ('P', '#cccccc'),
                    5: ('C', '#007acc'), 6: ('M', '#b180d7'), 7: ('P', '#cccccc'), 8: ('f', '#007acc'),
                    9: ('C', '#b180d7'), 10: ('E', '#ee9d28'), 11: ('I', '#007acc'), 12: ('f', '#b180d7'),
                    13: ('v', '#007acc'), 14: ('c', '#cccccc'), 22: ('e', '#ee9d28'), 23: ('S', '#cccccc'),
                    24: ('E', '#ee9d28')
                }
                char, color = mapping.get(kind, ('?', '#cccccc'))
                
                pixmap = QPixmap(16, 16)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                painter.setPen(QColor(color))
                font = QFont("Arial", 9, QFont.Weight.Bold)
                painter.setFont(font)
                painter.drawText(0, 0, 16, 16, Qt.AlignmentFlag.AlignCenter, char)
                painter.end()
                
                return QIcon(pixmap)
            
            def add_symbols(parent_item, syms):
                for s in syms:
                    name = s.get("name", "Unknown")
                    kind = s.get("kind", 0)
                    
                    # Filter out spammy flat variables (often standard imports sent by pylsp)
                    if kind == 13 and not s.get("children") and name in ("sys", "os", "json", "urllib", "typing", "subprocess"):
                        continue
                        
                    item = QStandardItem(name)
                    item.setToolTip(s.get("detail", ""))
                    item.setIcon(get_symbol_icon(kind))
                    
                    # Store 1-indexed position
                    rng = s.get("range", {})
                    item.setData(rng.get("startLineNumber", 1), Qt.ItemDataRole.UserRole + 1)
                    item.setData(rng.get("startColumn", 1), Qt.ItemDataRole.UserRole + 2)
                    
                    parent_item.appendRow(item)
                    
                    if s.get("children"):
                        add_symbols(item, s["children"])
            
            if not symbols:
                item = QStandardItem("No symbols found")
                self.outline_model.appendRow(item)
            else:
                add_symbols(self.outline_model, symbols)
                self.outline_tree_view.expandAll()
                
        except Exception as e:
            print("Failed to parse outline:", e)


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
                    elif result.returncode != 1:
                        # Return code 1 is Cancel. If it's something else, zenity probably failed.
                        use_zenity = False
                except Exception:
                    use_zenity = False # Fallback if zenity fails to run
                
        if not use_zenity and not folder:
            from PyQt6.QtWidgets import QFileDialog
            folder = QFileDialog.getExistingDirectory(self, "Open Folder", os.path.expanduser("~"))
            
        if folder:
            self.open_workspace(folder)

    def _on_directory_loaded(self, path: str):
        if path == ConfigManager().get("workspace_dir"):
            source_idx = self.file_model.index(path)
            proxy_idx = self.diagnostic_model.mapFromSource(source_idx)
            if proxy_idx.isValid():
                self.tree_view.setRootIndex(proxy_idx)
            
    def open_workspace(self, folder: str):
        if not os.path.exists(folder):
            return
        
        ConfigManager().set("workspace_dir", folder)
        self.is_empty_workspace = False

        # Update extension manager workspace root
        from lmms.extensions.manager import ExtensionManager
        ExtensionManager.instance().set_workspace_root(folder)

        # Connect directoryLoaded to correctly set root index after async load
        try:
            self.file_model.directoryLoaded.disconnect(self._on_directory_loaded)
        except TypeError:
            pass # Not connected
        self.file_model.directoryLoaded.connect(self._on_directory_loaded)
        
        self.file_model.setRootPath(folder)
        project_name = os.path.basename(folder)
        if not project_name: project_name = folder
        self.project_label.setText(project_name.upper())
        
        self.open_folder_btn.hide()
        self.tree_view.show()
        self.btn_new_file.show()
        self.btn_new_folder.show()
        self.btn_refresh.show()
        
        # Try to set immediately, though it may be invalid until directoryLoaded
        source_idx = self.file_model.index(folder)
        proxy_idx = self.diagnostic_model.mapFromSource(source_idx)
        if proxy_idx.isValid():
            self.tree_view.setRootIndex(proxy_idx)
        
        # Change actual working directory so terminal and new files default to it
        os.chdir(folder)
        
        # Notify panels
        if hasattr(self, 'source_control_dock') and hasattr(self.source_control_dock, 'set_workspace'):
            self.source_control_dock.set_workspace(folder)
        
        # Notify chat page
        if hasattr(self, 'chat_page') and hasattr(self.chat_page, 'update_workspace'):
            self.chat_page.update_workspace(folder)

    def get_selected_explorer_path(self):
        if not hasattr(self, 'tree_view'): return os.getcwd()
        idx = self.tree_view.currentIndex()
        if idx.isValid() and hasattr(self, 'file_model'):
            return self.file_model.filePath(idx)
        if hasattr(self, 'file_model') and self.file_model.rootPath():
            return self.file_model.rootPath()
        return os.getcwd()

    def _create_native_inline(self, is_folder):
        path = self.get_selected_explorer_path()
        if os.path.isfile(path): path = os.path.dirname(path)
        
        prefix = "New Folder" if is_folder else "Untitled"
        ext = "" if is_folder else ".txt"
        target_path = os.path.join(path, f"{prefix}{ext}")
        
        i = 1
        while os.path.exists(target_path):
            target_path = os.path.join(path, f"{prefix} ({i}){ext}")
            i += 1
            
        try:
            if is_folder:
                os.makedirs(target_path, exist_ok=True)
            else:
                open(target_path, 'a').close()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Could not create item: {e}")
            return
            
        # Wait for file system model to detect the new file
        def edit_when_ready(retries=10):
            source_idx = self.file_model.index(target_path)
            if source_idx.isValid():
                if hasattr(self, 'diagnostic_model') and self.diagnostic_model:
                    proxy_idx = self.diagnostic_model.mapFromSource(source_idx)
                    idx_to_edit = proxy_idx
                else:
                    idx_to_edit = source_idx
                self.tree_view.setCurrentIndex(idx_to_edit)
                self.tree_view.edit(idx_to_edit)
            elif retries > 0:
                QTimer.singleShot(50, lambda: edit_when_ready(retries - 1))
                
        QTimer.singleShot(50, edit_when_ready)

    def on_file_renamed(self, path, old_name, new_name):
        target_path = os.path.join(path, new_name)
        if os.path.isfile(target_path):
            self.editor_manager.open_file(target_path)

    def create_new_file(self):
        self._create_native_inline(is_folder=False)
                
    def create_new_folder(self):
        self._create_native_inline(is_folder=True)

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
                
        if hasattr(self, 'terminal_panel'):
            try:
                self.terminal_panel.cleanup()
            except Exception:
                pass
                
        if hasattr(self, 'ext_manager'):
            try:
                self.ext_manager.cleanup()
            except Exception:
                pass
                
        super().closeEvent(event)

    def toggle_bottom_panel(self):
        if not hasattr(self, 'terminal_panel'):
            return
        
        is_visible = self.terminal_panel.isVisible()
        self.terminal_panel.setVisible(not is_visible)

    def on_extension_ui_registered(self, ext_id, contributes):
        import json
        
        # Keep track of view mappings
        if not hasattr(self, '_extension_view_map'):
            self._extension_view_map = {}
            
        views_containers = contributes.get("viewsContainers", {})
        views = contributes.get("views", {})
        
        activity_bars = views_containers.get("activitybar", [])
        
        # Build mapping of view_id -> container_title
        builtin_map = {'explorer': 'Explorer', 'scm': 'Source Control', 'search': 'Search', 'debug': 'Run and Debug'}
        for container_id, view_list in views.items():
            container_title = builtin_map.get(container_id, container_id)
            for bar in activity_bars:
                if bar.get("id") == container_id:
                    container_title = bar.get("title", container_title)
                    break
                    
            for v in view_list:
                view_id = v.get("id")
                if view_id:
                    self._extension_view_map[view_id] = container_title
        
        for bar in activity_bars:
            title = bar.get("title", ext_id)
            icon_path = bar.get("icon", "")
            
            # Find the actual path of the icon in the extension directory
            rec = self.ext_manager._records.get(ext_id)
            full_icon_path = ""
            if rec and rec.path:
                full_icon_path = os.path.join(rec.path, "extension", icon_path)
            
            # Use initials if no valid icon
            text_icon = title[:2].upper() if not os.path.exists(full_icon_path) else ""
            
            # Add to sidebar
            self._add_nav_item(text_icon, title, full_icon_path, is_extension=True)
            
        # Optional: Prompt for API keys if required
        configuration = contributes.get("configuration", {})
        if configuration:
            props = configuration.get("properties", {})
            for key, val in props.items():
                if val.get("type") == "string":
                    desc = val.get("description", "").lower()
                    if "api key" in desc or "token" in desc or "api" in key.lower() or "key" in key.lower():
                        from PyQt6.QtWidgets import QInputDialog, QMessageBox
                        text, ok = QInputDialog.getText(self, f"Configure {title}", f"Please enter {key}:")
                        if ok and text:
                            # Send configuration to JS context (or save globally)
                            pass # TODO: push to Workspace Configuration

    def update_extension_view_html(self, view_id: str, html: str):
        if not hasattr(self, '_extension_view_map'):
            return
            
        # Find the display name for this view_id
        name = self._extension_view_map.get(view_id)
        if not name:
            # If not mapped, maybe the view_id itself is the name
            name = view_id
            
        # Find the dock with this name
        dock = self.docks.get(name)
        if dock and dock.widget():
            # Ensure it is a QWebEngineView
            webview = dock.widget()
            if hasattr(webview, 'setHtml'):
                # Inject a base tag if needed, but for VS Code webviews, the HTML is usually fully formed.
                # However, local resources might fail to load. We inject a script to handle VS Code Webview API.
                injected_html = html
                if "<head>" in injected_html and "acquireVsCodeApi" not in injected_html:
                    vscode_api_script = "<script>function acquireVsCodeApi() { return { postMessage: function(msg) { console.log('VSCode API message:', msg); } }; }</script>"
                    injected_html = injected_html.replace("<head>", f"<head>{vscode_api_script}")
                webview.setHtml(injected_html)

    def on_extension_js_activation(self, ext_id, manifest_json):
        # We need to send this to the CodeEditor instances so JS can register it.
        if hasattr(self, 'editor_manager'):
            for i in range(self.editor_manager.tabs.count()):
                widget = self.editor_manager.tabs.widget(i)
                if hasattr(widget, 'bridge'):
                    try:
                        import json
                        manifest = json.loads(manifest_json)
                        # Ensure we have the path to load files from
                        rec = self.ext_manager._records.get(ext_id)
                        if rec and rec.path:
                            manifest["extensionLocation"] = f"file://{os.path.join(rec.path, 'extension')}"
                        # Emit a custom signal or call JS directly
                        # We will need to define a new signal on PythonBridge for this
                        if hasattr(widget.bridge, 'registerExtension'):
                            widget.bridge.registerExtension.emit(json.dumps(manifest))
                    except Exception as e:
                        print(f"Error sending extension manifest to JS: {e}")
