from PyQt6.QtWidgets import QMenuBar, QMenu
from PyQt6.QtGui import QAction, QKeySequence
from lmms.backend.core.commands import CommandRegistry

class LMMsMenuBar(QMenuBar):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.setStyleSheet("""
            QMenuBar { background-color: #0d1117; color: #c9d1d9; border-bottom: 1px solid #30363d; }
            QMenuBar::item { background: transparent; padding: 4px 10px; margin: 2px; }
            QMenuBar::item:selected { background: #30363d; border-radius: 4px; }
            QMenu { background-color: #161b22; color: #c9d1d9; border: 1px solid #30363d; padding: 5px 0px; border-radius: 6px; }
            QMenu::item { padding: 6px 30px 6px 20px; margin: 0px 4px; border-radius: 4px; }
            QMenu::item:selected { background-color: #1f6feb; color: white; }
            QMenu::separator { height: 1px; background: #30363d; margin: 4px 0px; }
        """)
        self.init_menus()

    def init_menus(self):
        # APP MENU (LOGO)
        import os
        from PyQt6.QtGui import QIcon
        
        app_menu = QMenu(self)
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "lmms_logo.png")
        if os.path.exists(icon_path):
            app_menu.setIcon(QIcon(icon_path))
        else:
            app_menu.setTitle("LMMs")
            
        self._add_action(app_menu, "About LMMs", "", "app.about")
        self._add_action(app_menu, "Workspace Settings", "", "app.settings")
        self._add_action(app_menu, "Check Updates", "", "app.updates")
        app_menu.addSeparator()
        self._add_action(app_menu, "Restart Application", "", "app.restart")
        self._add_action(app_menu, "Exit", "", "file.exit")
        self.addMenu(app_menu)

        # FILE MENU
        file_menu = self.addMenu("File")
        self._add_action(file_menu, "New Chat", "Ctrl+N", "file.new_chat")
        self._add_action(file_menu, "Open Workspace", "Ctrl+Shift+O", "file.open_workspace")
        self._add_action(file_menu, "Open Folder", "Ctrl+K,Ctrl+O", "file.open_folder")
        self._add_action(file_menu, "Open File", "Ctrl+O", "file.open_file")
        file_menu.addSeparator()
        self._add_action(file_menu, "Recent Workspaces", "", "file.recent_workspaces")
        file_menu.addSeparator()
        self._add_action(file_menu, "Save Chat", "Ctrl+S", "file.save_chat")
        self._add_action(file_menu, "Export Chat", "", "file.export_chat")
        file_menu.addSeparator()
        self._add_action(file_menu, "Exit", "Ctrl+Q", "file.exit")

        # EDIT MENU
        edit_menu = self.addMenu("Edit")
        self._add_action(edit_menu, "Undo", "Ctrl+Z", "edit.undo")
        self._add_action(edit_menu, "Redo", "Ctrl+Y", "edit.redo")
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Cut", "Ctrl+X", "edit.cut")
        self._add_action(edit_menu, "Copy", "Ctrl+C", "edit.copy")
        self._add_action(edit_menu, "Paste", "Ctrl+V", "edit.paste")
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Find", "Ctrl+F", "edit.find")
        self._add_action(edit_menu, "Replace", "Ctrl+H", "edit.replace")

        # AI MENU
        ai_menu = self.addMenu("AI")
        self._add_action(ai_menu, "New Task", "", "ai.new_task")
        self._add_action(ai_menu, "Explain Selected Code", "", "ai.explain_code")
        self._add_action(ai_menu, "Fix Error", "", "ai.fix_error")
        self._add_action(ai_menu, "Refactor File", "", "ai.refactor_file")
        self._add_action(ai_menu, "Generate Documentation", "", "ai.generate_docs")
        self._add_action(ai_menu, "Generate Tests", "", "ai.generate_tests")
        ai_menu.addSeparator()
        self._add_action(ai_menu, "Fast Mode", "", "ai.fast_mode")
        self._add_action(ai_menu, "Thinking Mode", "", "ai.thinking_mode")
        self._add_action(ai_menu, "Deep Thinking Mode", "", "ai.deep_thinking_mode")
        ai_menu.addSeparator()
        self._add_action(ai_menu, "Agent Settings", "", "ai.agent_settings")

        # CHAT MENU
        chat_menu = self.addMenu("Chat")
        self._add_action(chat_menu, "New Chat", "", "chat.new_chat")
        self._add_action(chat_menu, "Rename Chat", "", "chat.rename_chat")
        self._add_action(chat_menu, "Delete Chat", "", "chat.delete_chat")
        self._add_action(chat_menu, "Duplicate Chat", "", "chat.duplicate_chat")
        self._add_action(chat_menu, "Export Chat", "", "chat.export_chat")
        chat_menu.addSeparator()
        self._add_action(chat_menu, "Chat History", "", "chat.chat_history")

        # VIEW MENU
        view_menu = self.addMenu("View")
        self._add_action(view_menu, "Toggle Explorer", "", "view.toggle_explorer")
        self._add_action(view_menu, "Toggle Chat", "", "view.toggle_chat")
        self._add_action(view_menu, "Toggle Terminal", "", "view.toggle_terminal")
        view_menu.addSeparator()
        self._add_action(view_menu, "Reset Layout", "", "view.reset_layout")
        view_menu.addSeparator()
        self._add_action(view_menu, "Full Screen", "F11", "view.full_screen")
        self._add_action(view_menu, "Zen Mode", "", "view.zen_mode")

        # SETTINGS MENU
        settings_menu = self.addMenu("Settings")
        self._add_action(settings_menu, "Providers", "", "settings.providers")
        self._add_action(settings_menu, "APIs", "", "settings.apis")
        self._add_action(settings_menu, "Memory", "", "settings.memory")
        self._add_action(settings_menu, "Context", "", "settings.context")
        self._add_action(settings_menu, "Workspace", "", "settings.workspace")
        self._add_action(settings_menu, "Theme", "", "settings.theme")
        self._add_action(settings_menu, "Server", "", "settings.server")
        self._add_action(settings_menu, "Keyboard Shortcuts", "", "settings.shortcuts")

        # HELP MENU
        help_menu = self.addMenu("Help")
        self._add_action(help_menu, "Documentation", "", "help.documentation")
        self._add_action(help_menu, "Keyboard Shortcuts", "", "help.shortcuts")
        self._add_action(help_menu, "Check Updates", "", "help.check_updates")
        self._add_action(help_menu, "Report Issue", "", "help.report_issue")
        help_menu.addSeparator()
        self._add_action(help_menu, "About LMMs", "", "help.about")

    def _add_action(self, menu: QMenu, title: str, shortcut: str, command_id: str):
        action = QAction(title, self)
        if shortcut:
            # QKeySequence handles Ctrl+K,Ctrl+O correctly
            action.setShortcut(QKeySequence(shortcut))
        
        # Connect the action to the central CommandRegistry
        action.triggered.connect(lambda checked, cid=command_id: CommandRegistry.execute(cid))
        menu.addAction(action)
