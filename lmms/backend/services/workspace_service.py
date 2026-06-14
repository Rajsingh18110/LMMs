import os
import json

STATE_FILE = os.path.expanduser("~/.lmms/layout_state.json")

class WorkspaceService:
    @staticmethod
    def _ensure_dir():
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

    @staticmethod
    def save_workspace_state(state_dict: dict):
        WorkspaceService._ensure_dir()
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state_dict, f, indent=4)
        except Exception as e:
            import lmms.gui.core.ui
            lmms.ui.show_error(f"Failed to save workspace state: {e}")

    @staticmethod
    def load_workspace_state() -> dict:
        if not os.path.exists(STATE_FILE):
            return {}
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            import lmms.gui.core.ui
            lmms.ui.show_error(f"Failed to load workspace state: {e}")
            return {}

    @staticmethod
    def capture_state(main_window) -> dict:
        """Captures the GUI state to save."""
        state = {
            "window_geometry": main_window.saveGeometry().data().hex() if main_window else "",
            "window_state": main_window.saveState().data().hex() if main_window else "",
            "inner_window_geometry": main_window.inner_window.saveGeometry().data().hex() if main_window and hasattr(main_window, 'inner_window') else "",
            "inner_window_state": main_window.inner_window.saveState().data().hex() if main_window and hasattr(main_window, 'inner_window') else "",
            "canvas_content": main_window.canvas_tab.toPlainText() if main_window and hasattr(main_window, 'canvas_tab') else "",
        }
        return state

    @staticmethod
    def apply_state(main_window, state: dict):
        """Applies the loaded state to the GUI."""
        from PyQt6.QtCore import QByteArray
        if not main_window:
            return
            
        if "window_geometry" in state and state["window_geometry"]:
            main_window.restoreGeometry(QByteArray.fromHex(state["window_geometry"].encode()))
        if "window_state" in state and state["window_state"]:
            main_window.restoreState(QByteArray.fromHex(state["window_state"].encode()))
        if "inner_window_geometry" in state and state["inner_window_geometry"] and hasattr(main_window, 'inner_window'):
            main_window.inner_window.restoreGeometry(QByteArray.fromHex(state["inner_window_geometry"].encode()))
        if "inner_window_state" in state and state["inner_window_state"] and hasattr(main_window, 'inner_window'):
            main_window.inner_window.restoreState(QByteArray.fromHex(state["inner_window_state"].encode()))
        if "canvas_content" in state and state["canvas_content"]:
            main_window.canvas_tab.setPlainText(state["canvas_content"])
