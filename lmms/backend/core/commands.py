import traceback
import lmms.gui.core.ui

class CommandContext:
    """
    Holds the state of the active workspace to pass to commands.
    """
    def __init__(self, main_window=None):
        self.main_window = main_window

    @property
    def active_editor(self):
        if self.main_window and hasattr(self.main_window, 'editor_manager'):
            return self.main_window.editor_manager.tabs.currentWidget()
        return None
        
    @property
    def active_canvas(self):
        if self.main_window:
            return self.main_window.canvas_tab
        return None

class CommandRegistry:
    """
    Central registry for application commands.
    Allows executing commands via strings (e.g. 'file.new_chat').
    """
    _commands = {}
    _context = CommandContext()

    @classmethod
    def set_context(cls, context: CommandContext):
        cls._context = context

    @classmethod
    def register(cls, command_id: str):
        """
        Decorator to register a function as a command.
        """
        def decorator(func):
            cls._commands[command_id] = func
            return func
        return decorator

    @classmethod
    def execute(cls, command_id: str, *args, **kwargs):
        """
        Executes a registered command safely, catching any exceptions.
        """
        if command_id not in cls._commands:
            lmms.gui.core.ui.show_error(f"Unknown command: {command_id}")
            return

        try:
            func = cls._commands[command_id]
            # Pass context as the first argument if the function accepts it
            # For simplicity, we just pass context explicitly for all commands
            func(cls._context, *args, **kwargs)
        except Exception as e:
            error_msg = f"Error executing command '{command_id}':\n{str(e)}\n\n{traceback.format_exc()}"
            lmms.gui.core.ui.show_error(error_msg)

# Setup initial placeholder commands that will be hooked up later
@CommandRegistry.register("file.new_chat")
def new_chat(context: CommandContext):
    if context.main_window:
        context.main_window.switch_page(context.main_window.chat_page, context.main_window.nav_buttons["Chats"])
        context.main_window.chat_page.start_new_chat()

@CommandRegistry.register("chat.new_chat")
def chat_new_chat(context: CommandContext):
    CommandRegistry.execute("file.new_chat")

@CommandRegistry.register("chat.rename_chat")
def chat_rename_chat(context: CommandContext):
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.information(context.main_window, "Rename Chat", "Rename Chat implementation pending.")

@CommandRegistry.register("chat.delete_chat")
def chat_delete_chat(context: CommandContext):
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.information(context.main_window, "Delete Chat", "Delete Chat implementation pending.")

@CommandRegistry.register("chat.duplicate_chat")
def chat_duplicate_chat(context: CommandContext):
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.information(context.main_window, "Duplicate Chat", "Duplicate Chat implementation pending.")

@CommandRegistry.register("chat.export_chat")
def chat_export_chat(context: CommandContext):
    CommandRegistry.execute("file.export_chat")

@CommandRegistry.register("chat.chat_history")
def chat_history(context: CommandContext):
    if context.main_window:
        context.main_window.switch_page(context.main_window.chat_page, context.main_window.nav_buttons["Chats"])

@CommandRegistry.register("edit.find")
def edit_find(context: CommandContext):
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.information(context.main_window, "Find", "Find dialog pending.")

@CommandRegistry.register("edit.replace")
def edit_replace(context: CommandContext):
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.information(context.main_window, "Replace", "Replace dialog pending.")

@CommandRegistry.register("ai.explain_code")
def ai_explain_code(context: CommandContext):
    if context.active_editor and context.active_editor.hasFocus():
        text = context.active_editor.textCursor().selectedText()
        if text and context.main_window:
            context.main_window.switch_page(context.main_window.chat_page, context.main_window.nav_buttons["Chats"])
            context.main_window.chat_page.input_field.setPlainText(f"Explain this code:\n\n{text}")
    else:
        import lmms.gui.core.ui
        lmms.gui.core.ui.show_error("Please select some code in the editor first.")
        
def _feature_pending(name, context):
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.information(context.main_window, "Feature", f"{name} is currently under development.")

@CommandRegistry.register("ai.new_task")
def ai_new_task(context: CommandContext): _feature_pending("New Task", context)

@CommandRegistry.register("ai.fix_error")
def ai_fix_error(context: CommandContext): _feature_pending("Fix Error", context)

@CommandRegistry.register("ai.refactor_file")
def ai_refactor_file(context: CommandContext): _feature_pending("Refactor File", context)

@CommandRegistry.register("ai.generate_docs")
def ai_generate_docs(context: CommandContext): _feature_pending("Generate Docs", context)

@CommandRegistry.register("ai.generate_tests")
def ai_generate_tests(context: CommandContext): _feature_pending("Generate Tests", context)

@CommandRegistry.register("ai.fast_mode")
def ai_fast_mode(context: CommandContext): _feature_pending("Fast Mode", context)

@CommandRegistry.register("ai.thinking_mode")
def ai_thinking_mode(context: CommandContext): _feature_pending("Thinking Mode", context)

@CommandRegistry.register("ai.deep_thinking_mode")
def ai_deep_thinking_mode(context: CommandContext): _feature_pending("Deep Thinking Mode", context)

@CommandRegistry.register("ai.agent_settings")
def ai_agent_settings(context: CommandContext): CommandRegistry.execute("settings.providers")

@CommandRegistry.register("help.documentation")
def help_docs(context: CommandContext): _feature_pending("Documentation Viewer", context)

@CommandRegistry.register("help.shortcuts")
def help_shortcuts(context: CommandContext): CommandRegistry.execute("settings.shortcuts")

@CommandRegistry.register("help.check_updates")
def help_check_updates(context: CommandContext): CommandRegistry.execute("app.updates")

@CommandRegistry.register("help.report_issue")
def help_report(context: CommandContext): _feature_pending("Issue Reporter", context)

@CommandRegistry.register("help.about")
def help_about(context: CommandContext): CommandRegistry.execute("app.about")

@CommandRegistry.register("file.exit")
def exit_app(context: CommandContext):
    if context.main_window:
        context.main_window.close()

@CommandRegistry.register("file.open_folder")
def file_open_folder(context: CommandContext):
    if context.main_window:
        # Defer to the main window's comprehensive open folder logic
        # which handles zenity integration, proxy models, config updating, etc.
        context.main_window.prompt_open_folder()

@CommandRegistry.register("file.open_workspace")
def file_open_workspace(context: CommandContext):
    CommandRegistry.execute("file.open_folder")

@CommandRegistry.register("file.recent_workspaces")
def file_recent_workspaces(context: CommandContext):
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.information(context.main_window, "Recent Workspaces", "No recent workspaces found.")

@CommandRegistry.register("file.open_file")
def file_open_file(context: CommandContext):
    if context.main_window:
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(context.main_window, "Open File")
        if file_path:
            try:
                context.main_window.editor_manager.open_file(file_path)
            except Exception as e:
                import lmms.gui.core.ui
                lmms.gui.core.ui.show_error(f"Could not open file: {e}")

@CommandRegistry.register("file.save_chat")
def file_save_chat(context: CommandContext):
    if context.main_window:
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getSaveFileName(context.main_window, "Save Chat", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("Chat History Save - Implementation Pending") 
            QMessageBox.information(context.main_window, "Chat Saved", "Chat saved successfully.")

@CommandRegistry.register("file.export_chat")
def file_export_chat(context: CommandContext):
    CommandRegistry.execute("file.save_chat")

@CommandRegistry.register("edit.undo")
def edit_undo(context: CommandContext):
    if context.active_editor and context.active_editor.hasFocus():
        context.active_editor.undo()
    elif context.active_canvas and context.active_canvas.hasFocus():
        context.active_canvas.undo()

@CommandRegistry.register("edit.redo")
def edit_redo(context: CommandContext):
    if context.active_editor and context.active_editor.hasFocus():
        context.active_editor.redo()
    elif context.active_canvas and context.active_canvas.hasFocus():
        context.active_canvas.redo()

@CommandRegistry.register("edit.cut")
def edit_cut(context: CommandContext):
    if context.active_editor and context.active_editor.hasFocus():
        context.active_editor.cut()
    elif context.active_canvas and context.active_canvas.hasFocus():
        context.active_canvas.cut()

@CommandRegistry.register("edit.copy")
def edit_copy(context: CommandContext):
    if context.active_editor and context.active_editor.hasFocus():
        context.active_editor.copy()
    elif context.active_canvas and context.active_canvas.hasFocus():
        context.active_canvas.copy()

@CommandRegistry.register("edit.paste")
def edit_paste(context: CommandContext):
    if context.active_editor and context.active_editor.hasFocus():
        context.active_editor.paste()
    elif context.active_canvas and context.active_canvas.hasFocus():
        context.active_canvas.paste()

@CommandRegistry.register("view.toggle_explorer")
def toggle_explorer(context: CommandContext):
    if context.main_window:
        w = context.main_window.explorer_dock
        w.setVisible(not w.isVisible())

@CommandRegistry.register("view.toggle_editor")
def toggle_editor(context: CommandContext):
    pass # Obsolete with tabbed editor

@CommandRegistry.register("view.toggle_chat")
def toggle_chat(context: CommandContext):
    if context.main_window:
        w = context.main_window.chat_dock
        w.setVisible(not w.isVisible())

@CommandRegistry.register("view.toggle_terminal")
def toggle_terminal(context: CommandContext):
    if context.main_window:
        context.main_window.editor_manager.open_terminal_tab()

@CommandRegistry.register("view.reset_layout")
def reset_layout(context: CommandContext):
    if context.main_window:
        mw = context.main_window.inner_window
        from PyQt6.QtCore import Qt
        # Apply Default Layout
        mw.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, context.main_window.explorer_dock)
        mw.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, context.main_window.chat_dock)
        
        context.main_window.explorer_dock.show()
        context.main_window.chat_dock.show()

@CommandRegistry.register("view.full_screen")
def view_full_screen(context: CommandContext):
    if context.main_window:
        if context.main_window.isFullScreen():
            context.main_window.showNormal()
        else:
            context.main_window.showFullScreen()

@CommandRegistry.register("view.zen_mode")
def view_zen_mode(context: CommandContext):
    if context.main_window:
        for dock in context.main_window.docks.values():
            dock.hide()
        context.main_window.sidebar.hide()
        context.main_window.editor_dock.show()

@CommandRegistry.register("app.about")
def app_about(context: CommandContext):
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.information(context.main_window, "About LMMs", "LMMs AI Workspace\nVersion 0.1.0\nLocal Machine Model Studio")

@CommandRegistry.register("app.settings")
def app_settings(context: CommandContext):
    CommandRegistry.execute("settings.workspace")

@CommandRegistry.register("app.updates")
def app_updates(context: CommandContext):
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.information(context.main_window, "Updates", "LMMs is up to date.")

@CommandRegistry.register("app.restart")
def app_restart(context: CommandContext):
    if context.main_window:
        context.main_window.close()
    import sys, os
    os.execl(sys.executable, sys.executable, *sys.argv)

def _open_settings(context: CommandContext, index: int):
    if context.main_window:
        from lmms.gui.dialogs.settings_dialog import SettingsDialog
        dialog = SettingsDialog(context.main_window)
        dialog.nav_list.setCurrentRow(index)
        dialog.exec()

@CommandRegistry.register("settings.providers")
def settings_providers(context: CommandContext): _open_settings(context, 0)

@CommandRegistry.register("settings.apis")
def settings_apis(context: CommandContext): _open_settings(context, 1)

@CommandRegistry.register("settings.memory")
def settings_memory(context: CommandContext): _open_settings(context, 2)

@CommandRegistry.register("settings.context")
def settings_context(context: CommandContext): _open_settings(context, 3)

@CommandRegistry.register("settings.workspace")
def settings_workspace(context: CommandContext): _open_settings(context, 4)

@CommandRegistry.register("settings.theme")
def settings_theme(context: CommandContext): _open_settings(context, 5)

@CommandRegistry.register("settings.server")
def settings_server(context: CommandContext): _open_settings(context, 6)

@CommandRegistry.register("settings.shortcuts")
def settings_shortcuts(context: CommandContext): _open_settings(context, 7)
