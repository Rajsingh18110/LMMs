"""
Command Registry — central registry for VS Code-compatible commands.

Supports:
- Extension-registered commands (from runner.js via host)
- Built-in LMMs commands
- Command Palette integration
"""
from __future__ import annotations
from typing import Callable, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal


class CommandRegistry(QObject):
    command_registered = pyqtSignal(str, str)   # id, title
    command_removed    = pyqtSignal(str)          # id
    command_executed   = pyqtSignal(str, object)  # id, result

    _instance: Optional["CommandRegistry"] = None

    @classmethod
    def instance(cls) -> "CommandRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cmds: dict[str, dict] = {}   # id → {title, callback, ext_id}

    def register(self, cmd_id: str, title: str,
                 callback: Callable | None = None,
                 ext_id: str = "") -> "Disposable":
        self._cmds[cmd_id] = {
            "title":    title,
            "callback": callback,
            "ext_id":   ext_id,
        }
        self.command_registered.emit(cmd_id, title)
        return Disposable(lambda: self.unregister(cmd_id))

    def unregister(self, cmd_id: str):
        self._cmds.pop(cmd_id, None)
        self.command_removed.emit(cmd_id)

    def execute(self, cmd_id: str, *args) -> Any:
        entry = self._cmds.get(cmd_id)
        if not entry:
            raise KeyError(f"Command not found: {cmd_id}")
        cb = entry.get("callback")
        result = cb(*args) if cb else None
        self.command_executed.emit(cmd_id, result)
        return result

    def get_all(self) -> list[dict]:
        return [
            {"id": k, "title": v["title"], "ext_id": v["ext_id"]}
            for k, v in self._cmds.items()
        ]

    def has(self, cmd_id: str) -> bool:
        return cmd_id in self._cmds


class Disposable:
    def __init__(self, dispose_fn: Callable):
        self._fn = dispose_fn
        self._disposed = False

    def dispose(self):
        if not self._disposed:
            self._disposed = True
            self._fn()

    def __del__(self):
        self.dispose()
