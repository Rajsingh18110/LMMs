"""
VS Code API bridge — Python side.

Receives RPC calls from runner.js (via ExtensionHost.rpc_request signal)
and dispatches them to real LMMs systems.

Supported APIs
--------------
window.*             Qt dialogs
workspace.*          workspace folder, config, openTextDocument
fs.*                 sandboxed filesystem (workspace-only)
terminal.*           LMMs terminal panel
env.*                clipboard, openExternal
workspace.getFolders workspace root

NOT SUPPORTED (gracefully ignored with log)
---------
vscode.debug
vscode.tasks
vscode.authentication
vscode.scm (source control model)
"""
from __future__ import annotations
import os
import json
import subprocess
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QObject, pyqtSlot, QMetaObject, Qt, Q_ARG
from PyQt6.QtWidgets import (
    QMessageBox, QInputDialog, QApplication
)


class VScodeApiBridge(QObject):
    """
    Singleton that handles all vscode.* RPC calls from extension hosts.

    Usage:
        bridge = VScodeApiBridge.instance()
        bridge.set_workspace_root('/my/project')

        # Connect ExtensionHost.rpc_request to bridge.handle_rpc
        host.rpc_request.connect(bridge.handle_rpc)
    """

    _instance: Optional["VScodeApiBridge"] = None

    @classmethod
    def instance(cls) -> "VScodeApiBridge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workspace_root: str | None = None
        self._hosts: dict = {}   # ext_id → ExtensionHost

    def set_workspace_root(self, root: str | None):
        self._workspace_root = root

    def register_host(self, ext_id: str, host):
        self._hosts[ext_id] = host

    def unregister_host(self, ext_id: str):
        self._hosts.pop(ext_id, None)

    # ── RPC dispatcher ────────────────────────────────────────────────────────

    @pyqtSlot(str, str, object, object)
    def handle_rpc(self, ext_id: str, method: str, params, rpc_id: str):
        host = self._hosts.get(ext_id)
        if not host:
            return

        try:
            result = self._dispatch(ext_id, method, params or [])
            host.reply_rpc(rpc_id, result=result)
        except NotImplementedError as e:
            host.reply_rpc(rpc_id, error=f"API not implemented: {e}")
        except Exception as e:
            host.reply_rpc(rpc_id, error=str(e))

    def _dispatch(self, ext_id: str, method: str, params):
        # ── window API ────────────────────────────────────────────────────────
        if method == "window.showInformationMessage":
            msg = params[0] if params else ""
            QMessageBox.information(None, f"Extension ({ext_id})", msg)
            return None

        if method == "window.showWarningMessage":
            msg = params[0] if params else ""
            QMessageBox.warning(None, f"Extension ({ext_id})", msg)
            return None

        if method == "window.showErrorMessage":
            msg = params[0] if params else ""
            QMessageBox.critical(None, f"Extension ({ext_id})", msg)
            return None

        if method == "window.showInputBox":
            opts = params[0] if params else {}
            prompt      = opts.get("prompt", "")
            placeholder = opts.get("placeHolder", "")
            value, ok   = QInputDialog.getText(None, f"Extension ({ext_id})", prompt,
                                               text=placeholder)
            return value if ok else None

        if method == "window.showQuickPick":
            items = params[0] if params else []
            opts  = params[1] if len(params) > 1 else {}
            labels = [i if isinstance(i, str) else i.get("label", str(i)) for i in items]
            item, ok = QInputDialog.getItem(
                None, f"Extension ({ext_id})",
                opts.get("placeHolder", "Select item"),
                labels, editable=False
            )
            return item if ok else None

        if method == "window.createTerminal":
            opts = params[0] if params else {}
            from lmms.gui.panels.terminal_panel import TerminalPanel
            # Find existing terminal and send shell command
            return None  # terminal created on Python side

        if method == "terminal.sendText":
            text = params[0] if params else ""
            # Would send to active terminal — hook in later
            return None

        # ── webview API ───────────────────────────────────────────────────────
        if method == "webview.setHtml":
            view_id = params[0] if params else ""
            html_content = params[1] if len(params) > 1 else ""
            from PyQt6.QtWidgets import QApplication
            
            # Find MainWindow and update the view
            for w in QApplication.topLevelWidgets():
                if hasattr(w, 'update_extension_view_html'):
                    w.update_extension_view_html(view_id, html_content)
            return None

        # ── workspace API ─────────────────────────────────────────────────────
        if method == "workspace.getFolders":
            if self._workspace_root:
                name = os.path.basename(self._workspace_root)
                return [{"name": name, "uri": {"scheme": "file",
                                               "path": self._workspace_root,
                                               "fsPath": self._workspace_root},
                         "index": 0}]
            return []

        if method == "workspace.openTextDocument":
            path_ = params[0] if params else ""
            if path_ and os.path.isfile(path_):
                try:
                    with open(path_, encoding="utf-8") as fh:
                        content = fh.read()
                    return {"uri": {"fsPath": path_}, "getText": content,
                            "languageId": _lang_from_path(path_)}
                except Exception as e:
                    raise RuntimeError(str(e))
            return None

        if method == "workspace.findFiles":
            if not self._workspace_root:
                return []
            include = params[0] if params else "**/*"
            try:
                result = subprocess.check_output(
                    ["find", self._workspace_root, "-type", "f", "-name",
                     include.replace("**/*", "*").replace("**/", "")],
                    timeout=5, text=True
                )
                return [{"fsPath": p} for p in result.splitlines() if p]
            except Exception:
                return []

        if method == "workspace.updateConfiguration":
            # No-op — config changes not persisted yet
            return None

        # ── filesystem API (sandboxed to workspace) ───────────────────────────
        if method in ("fs.readFile", "fs.writeFile", "fs.stat",
                      "fs.readDirectory", "fs.createDirectory",
                      "fs.delete", "fs.rename"):
            return self._handle_fs(method, params)

        # ── env API ───────────────────────────────────────────────────────────
        if method == "env.openExternal":
            url = params[0] if params else ""
            import subprocess as sp
            sp.Popen(["xdg-open", url])
            return None

        if method == "env.clipboard.readText":
            cb = QApplication.clipboard()
            return cb.text() if cb else ""

        if method == "env.clipboard.writeText":
            text = params[0] if params else ""
            cb = QApplication.clipboard()
            if cb:
                cb.setText(text)
            return None

        # ── executeCommand pass-through ───────────────────────────────────────
        if method == "executeCommand":
            cmd_id = params[0] if params else ""
            # Try to route to command registry
            from lmms.extensions.commands import CommandRegistry
            return CommandRegistry.instance().execute(cmd_id, *(params[1:] if params else []))

        # Gracefully ignore unknown methods
        print(f"[VScodeApiBridge] Unimplemented: {method}({params})")
        return None

    def _handle_fs(self, method: str, params):
        """Sandboxed filesystem API — only workspace paths allowed."""
        path_ = str(params[0]) if params else ""
        root  = self._workspace_root or ""

        # Security: must be inside workspace
        if root and path_:
            try:
                abs_p  = os.path.realpath(path_)
                abs_r  = os.path.realpath(root)
                if not abs_p.startswith(abs_r):
                    raise PermissionError(
                        f"Filesystem access outside workspace denied: {path_}"
                    )
            except Exception as e:
                raise PermissionError(str(e))

        if method == "fs.readFile":
            with open(path_, "rb") as fh:
                return list(fh.read())

        if method == "fs.writeFile":
            content = bytes(params[1]) if len(params) > 1 else b""
            os.makedirs(os.path.dirname(path_), exist_ok=True)
            with open(path_, "wb") as fh:
                fh.write(content)
            return None

        if method == "fs.stat":
            s = os.stat(path_)
            import stat
            ftype = 1 if os.path.isfile(path_) else 2
            return {"type": ftype, "size": s.st_size,
                    "ctime": int(s.st_ctime * 1000), "mtime": int(s.st_mtime * 1000)}

        if method == "fs.readDirectory":
            entries = []
            for entry in os.scandir(path_):
                ftype = 1 if entry.is_file() else 2
                entries.append([entry.name, ftype])
            return entries

        if method == "fs.createDirectory":
            os.makedirs(path_, exist_ok=True)
            return None

        if method == "fs.delete":
            import shutil
            if os.path.isdir(path_):
                shutil.rmtree(path_)
            elif os.path.isfile(path_):
                os.unlink(path_)
            return None

        if method == "fs.rename":
            dst = str(params[1]) if len(params) > 1 else ""
            os.rename(path_, dst)
            return None

        return None


def _lang_from_path(path_: str) -> str:
    ext = os.path.splitext(path_)[1].lower()
    return {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".html": "html", ".css": "css", ".json": "json", ".md": "markdown",
        ".rs": "rust", ".go": "go", ".c": "c", ".cpp": "cpp",
        ".java": "java", ".sh": "shellscript",
    }.get(ext, "plaintext")
