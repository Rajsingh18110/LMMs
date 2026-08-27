"""
Extension Manager — singleton that owns all extension state.

Responsibilities:
- Install / uninstall extensions
- Persist state to ~/.lmms/extensions/installed.json
- Manage Extension Host processes
- Bridge to Command Registry and VS Code API layer
- Emit state_changed so UI can react

Usage:
    mgr = ExtensionManager.instance()
    mgr.install(ext_dict)                # async — signals fire on completion
    mgr.state_changed.connect(my_slot)   # (ext_id, new_state)
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from lmms.extensions.models import (
    ExtensionRecord, ExtState, CompatLevel, EXTENSIONS_ROOT
)
from lmms.extensions.installer import InstallThread, UninstallThread

_STATE_FILE = EXTENSIONS_ROOT / "installed.json"


class ExtensionManager(QObject):
    # (ext_id, new_state)
    state_changed  = pyqtSignal(str, str)
    # (ext_id, level, msg)
    log_emitted    = pyqtSignal(str, str, str)
    # (ext_id, cmd_id, title)
    command_added  = pyqtSignal(str, str, str)
    # progress 0-100 during install
    install_progress = pyqtSignal(str, int)

    _instance: Optional["ExtensionManager"] = None

    @classmethod
    def instance(cls) -> "ExtensionManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self._records:  dict[str, ExtensionRecord] = {}
        self._threads:  dict[str, QObject]         = {}  # ext_id → active thread
        self._hosts:    dict[str, object]           = {}  # ext_id → ExtensionHost
        self._workspace_root: str | None = None

        # Load persisted state
        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_workspace_root(self, path: str | None):
        self._workspace_root = path
        from lmms.extensions.vscode_api import VScodeApiBridge
        VScodeApiBridge.instance().set_workspace_root(path)

    def get_state(self, ext_id: str) -> ExtState:
        rec = self._records.get(ext_id)
        return rec.state if rec else ExtState.AVAILABLE

    def get_record(self, ext_id: str) -> ExtensionRecord | None:
        return self._records.get(ext_id)

    def get_installed(self) -> list[ExtensionRecord]:
        return list(self._records.values())

    def is_installed(self, ext_id: str) -> bool:
        state = self.get_state(ext_id)
        return state not in (ExtState.AVAILABLE, ExtState.UNINSTALLED)

    # ── Install ───────────────────────────────────────────────────────────────

    def install(self, ext_dict: dict):
        ns   = ext_dict.get("namespace", "")
        name = ext_dict.get("name", "")
        ext_id = f"{ns}.{name}"

        if ext_id in self._threads:
            return  # already in progress

        self._set_state(ext_id, ExtState.INSTALLING)
        self._emit_log(ext_id, "info", f"Installing {ext_id}…")

        t = InstallThread(ext_dict)
        t.progress.connect(lambda p: self.install_progress.emit(ext_id, p))
        t.log.connect(lambda msg: self._emit_log(ext_id, "info", msg))
        t.done.connect(self._on_install_done)
        t.error.connect(lambda err: self._on_install_error(ext_id, err))
        t.finished.connect(t.deleteLater)
        self._threads[ext_id] = t
        t.start()

    def _on_install_done(self, record: ExtensionRecord):
        self._records[record.ext_id] = record
        self._set_state(record.ext_id, ExtState.INSTALLED)
        self._save()
        self._emit_log(record.ext_id, "info", "✓ Installed — activating…")
        # Attempt activation
        QTimer.singleShot(500, lambda: self._activate(record.ext_id))

    def _on_install_error(self, ext_id: str, error: str):
        rec = self._records.get(ext_id)
        if rec:
            rec.error = error
            rec.state = ExtState.FAILED
        self._set_state(ext_id, ExtState.FAILED)
        self._emit_log(ext_id, "error", f"✕ Install failed: {error}")
        self._save()

    # ── Activate ──────────────────────────────────────────────────────────────

    extension_ui_registered = pyqtSignal(str, dict)  # ext_id, viewsContainers
    extension_js_activation = pyqtSignal(str, str)  # ext_id, manifest_json string

    def _activate(self, ext_id: str):
        rec = self._records.get(ext_id)
        if not rec or rec.compat == CompatLevel.INCOMPATIBLE:
            return

        # Stop any existing host
        self._stop_host(ext_id)
        
        # Check permissions for PARTIAL compat
        if rec.compat == CompatLevel.PARTIAL:
            from lmms.gui.dialogs.extension_permissions_dialog import ExtensionPermissionsDialog
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QTimer
            
            # Use active window as parent if available
            parent = QApplication.activeWindow()
            dialog = ExtensionPermissionsDialog(rec, parent)
            if dialog.exec() == 0:  # Rejected
                self._emit_log(ext_id, "warn", "Activation cancelled (permissions denied).")
                self._set_state(ext_id, ExtState.DISABLED)
                return
            
            perms = dialog.get_granted_permissions()
            rec.log(f"Permissions granted: {perms}")
            # In a real app we'd pass perms to the host. For now just log.

        self._set_state(ext_id, ExtState.ACTIVATING)
        self._emit_log(ext_id, "info", f"Starting extension host…")

        # Parse package.json for UI injection and JS activation
        manifest = {}
        if rec.path:
            pkg_path = os.path.join(rec.path, "extension", "package.json")
            if os.path.exists(pkg_path):
                try:
                    with open(pkg_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                except Exception as e:
                    self._emit_log(ext_id, "error", f"Failed to parse package.json: {e}")

        contributes = manifest.get("contributes", {})
        if contributes.get("viewsContainers") or contributes.get("views"):
            self.extension_ui_registered.emit(ext_id, contributes)

        if manifest:
            self.extension_js_activation.emit(ext_id, json.dumps(manifest))

        from lmms.extensions.host import ExtensionHost
        from lmms.extensions.vscode_api import VScodeApiBridge
        from lmms.extensions.commands import CommandRegistry

        host = ExtensionHost(rec, self._workspace_root)
        host.log_line.connect(self.log_emitted)
        host.activated.connect(self._on_activated)
        host.activation_failed.connect(self._on_activation_failed)
        host.rpc_request.connect(VScodeApiBridge.instance().handle_rpc)
        host.command_registered.connect(
            lambda eid, cid, title: self._on_command_registered(eid, cid, title)
        )

        VScodeApiBridge.instance().register_host(ext_id, host)
        self._hosts[ext_id] = host
        host.start()

    def _on_activated(self, ext_id: str):
        self._set_state(ext_id, ExtState.ACTIVE)
        self._emit_log(ext_id, "info", "✓ Active")
        self._save()

    def _on_activation_failed(self, ext_id: str, error: str):
        rec = self._records.get(ext_id)
        if rec:
            rec.error = error
        # Keep INSTALLED state (downloaded but not active)
        self._set_state(ext_id, ExtState.INSTALLED)
        self._emit_log(ext_id, "warn",
                       f"Activation failed (INSTALL_ONLY): {error}")
        self._save()

    def _on_command_registered(self, ext_id: str, cmd_id: str, title: str):
        from lmms.extensions.commands import CommandRegistry
        reg = CommandRegistry.instance()
        # Register with a callback that routes to the extension host
        host = self._hosts.get(ext_id)
        def _callback(*args):
            if host:
                host.send_to_node({"method": "executeCommand",
                                   "params": [cmd_id] + list(args)})
        reg.register(cmd_id, title, _callback, ext_id)
        self.command_added.emit(ext_id, cmd_id, title)

    # ── Uninstall ─────────────────────────────────────────────────────────────

    def uninstall(self, ext_id: str):
        rec = self._records.get(ext_id)
        if not rec:
            return
        self._stop_host(ext_id)
        self._set_state(ext_id, ExtState.UNINSTALLING)

        t = UninstallThread(ext_id, rec.path or "")
        t.done.connect(self._on_uninstall_done)
        t.error.connect(lambda err: self._emit_log(ext_id, "error", err))
        t.finished.connect(lambda: self._threads.pop(ext_id, None))
        self._threads[ext_id] = t
        t.start()

    def _on_uninstall_done(self, ext_id: str):
        self._records.pop(ext_id, None)
        self._set_state(ext_id, ExtState.UNINSTALLED)
        self._save()

    # ── Enable / Disable ──────────────────────────────────────────────────────

    def enable(self, ext_id: str):
        rec = self._records.get(ext_id)
        if rec and rec.state == ExtState.DISABLED:
            self._activate(ext_id)

    def disable(self, ext_id: str):
        self._stop_host(ext_id)
        rec = self._records.get(ext_id)
        if rec:
            rec.state = ExtState.DISABLED
        self._set_state(ext_id, ExtState.DISABLED)
        self._save()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _set_state(self, ext_id: str, state: ExtState):
        rec = self._records.get(ext_id)
        if rec:
            rec.state = state
        self.state_changed.emit(ext_id, state.value)

    def _emit_log(self, ext_id: str, level: str, msg: str):
        rec = self._records.get(ext_id)
        if rec:
            rec.log(msg)
        self.log_emitted.emit(ext_id, level, msg)

    def _stop_host(self, ext_id: str):
        h = self._hosts.pop(ext_id, None)
        if h:
            from lmms.extensions.vscode_api import VScodeApiBridge
            VScodeApiBridge.instance().unregister_host(ext_id)
            h.stop()

    def cleanup(self):
        for ext_id, t in list(self._threads.items()):
            try:
                t.quit()
                t.wait()
                t.deleteLater()
            except Exception:
                pass
        self._threads.clear()

    # ── persistence ───────────────────────────────────────────────────────────

    def _save(self):
        try:
            EXTENSIONS_ROOT.mkdir(parents=True, exist_ok=True)
            data = {k: v.to_json() for k, v in self._records.items()}
            with open(_STATE_FILE, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except Exception as e:
            print(f"[ExtensionManager] Save error: {e}")

    def _load(self):
        if not _STATE_FILE.exists():
            return
        try:
            with open(_STATE_FILE, encoding="utf-8") as fh:
                data = json.load(fh)
            for ext_id, d in data.items():
                try:
                    rec = ExtensionRecord.from_json(d)
                    # On reload, INSTALLING/ACTIVATING → INSTALLED (process died)
                    if rec.state in (ExtState.INSTALLING, ExtState.ACTIVATING,
                                     ExtState.UNINSTALLING):
                        rec.state = ExtState.INSTALLED
                    self._records[ext_id] = rec
                except Exception as e:
                    print(f"[ExtensionManager] Failed to load {ext_id}: {e}")
        except Exception as e:
            print(f"[ExtensionManager] Load error: {e}")
