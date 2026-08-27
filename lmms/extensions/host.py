"""
Extension Host — manages Node.js subprocess running runner.js.

One ExtensionHost instance per ACTIVE extension.
Handles JSON-RPC to/from the runner, dispatches vscode API calls to LMMs.
"""
from __future__ import annotations
import os
import json
import shutil
import subprocess
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread

from lmms.extensions.models import ExtensionRecord, ExtState, CompatLevel

_RUNNER_JS = Path(__file__).parent / "runner.js"
_NODE_BIN  = shutil.which("node") or "node"


class ExtensionHost(QObject):
    """
    Manages the lifecycle of one extension's Node.js subprocess.

    Signals
    -------
    log_line(ext_id, level, msg)
    command_registered(ext_id, cmd_id, title)
    activated(ext_id)
    activation_failed(ext_id, error)
    rpc_request(ext_id, method, params, callback)  ← dispatched to Python API
    """

    log_line            = pyqtSignal(str, str, str)   # ext_id, level, msg
    command_registered  = pyqtSignal(str, str, str)   # ext_id, cmd_id, title
    activated           = pyqtSignal(str)
    activation_failed   = pyqtSignal(str, str)
    rpc_request         = pyqtSignal(str, str, object, object)  # ext_id, method, params, rpc_id

    def __init__(self, record: ExtensionRecord, workspace_root: str | None = None, parent=None):
        super().__init__(parent)
        self.record         = record
        self.workspace_root = workspace_root
        self._proc: subprocess.Popen | None = None
        self._read_thread = None
        self._stderr_thread = None
        self._pending: dict = {}   # rpc_id → callback
        self._counter = 0

    class WorkerThread(QThread):
        def __init__(self, target, name=""):
            super().__init__()
            self._target = target
            if name:
                self.setObjectName(name)
        def run(self):
            self._target()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        if self.record.compat == CompatLevel.INCOMPATIBLE:
            self.activation_failed.emit(self.record.ext_id, "Extension is incompatible.")
            return
        if not _RUNNER_JS.exists():
            self.activation_failed.emit(self.record.ext_id, "runner.js not found.")
            return

        manifest_path = os.path.join(self.record.path or "", "extension", "package.json")
        if not os.path.exists(manifest_path):
            # Try root package.json
            manifest_path = os.path.join(self.record.path or "", "package.json")

        if not os.path.exists(manifest_path):
            # No JS to activate — mark installed but no runtime
            self.record.log("No manifest found — install-only mode.")
            self.activation_failed.emit(self.record.ext_id, "No package.json found.")
            return

        try:
            self._proc = subprocess.Popen(
                [_NODE_BIN, str(_RUNNER_JS), manifest_path, self.record.path or ""],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                env={**os.environ, "HOME": str(Path.home())},
            )
            self._read_thread = self.WorkerThread(target=self._read_loop, name=f"ext-{self.record.ext_id}")
            self._read_thread.start()
            # Also drain stderr
            self._stderr_thread = self.WorkerThread(target=self._stderr_loop, name=f"ext-stderr-{self.record.ext_id}")
            self._stderr_thread.start()
            self.record.log("Extension host started.")
        except Exception as e:
            err = f"Failed to start Node.js host: {e}"
            self.record.log(err)
            self.activation_failed.emit(self.record.ext_id, err)

    def stop(self):
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                pass
            self._proc = None
        self.record.log("Extension host stopped.")

    # ── write JSON-RPC to Node ────────────────────────────────────────────────

    def send_to_node(self, obj: dict):
        if self._proc and self._proc.stdin:
            try:
                line = json.dumps(obj) + "\n"
                self._proc.stdin.write(line.encode())
                self._proc.stdin.flush()
            except Exception:
                pass

    def reply_rpc(self, rpc_id: str, result=None, error: str | None = None):
        msg: dict = {"id": rpc_id}
        if error:
            msg["error"] = error
        else:
            msg["result"] = result
        self.send_to_node(msg)

    # ── read loop ─────────────────────────────────────────────────────────────

    def _read_loop(self):
        proc = self._proc
        if not proc:
            return
        for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception:
                continue
            self._dispatch(msg)

    def _stderr_loop(self):
        proc = self._proc
        if not proc:
            return
        for raw in proc.stderr:
            line = raw.decode("utf-8", errors="replace").rstrip()
            if line:
                self.log_line.emit(self.record.ext_id, "stderr", line)
                self.record.log(f"[stderr] {line}")

    def _dispatch(self, msg: dict):
        method = msg.get("method")
        params = msg.get("params")
        rpc_id = msg.get("id")

        if method == "log":
            level = params.get("level", "info") if isinstance(params, dict) else "info"
            text  = params.get("msg", "") if isinstance(params, dict) else str(params)
            self.log_line.emit(self.record.ext_id, level, text)
            self.record.log(f"[{level}] {text}")

        elif method == "registerCommand":
            cmd_id = params.get("id", "") if isinstance(params, dict) else ""
            title  = params.get("title", cmd_id) if isinstance(params, dict) else cmd_id
            self.command_registered.emit(self.record.ext_id, cmd_id, title)

        elif method == "activated":
            self.record.state = ExtState.ACTIVE
            cmds = (params or {}).get("commands", []) if isinstance(params, dict) else []
            self.record.log(f"Activated — {len(cmds)} command(s)")
            self.activated.emit(self.record.ext_id)

        elif method == "activationFailed":
            err = (params or {}).get("error", "Unknown") if isinstance(params, dict) else str(params)
            self.record.state = ExtState.FAILED
            self.record.error = err
            self.record.log(f"ACTIVATION FAILED: {err}")
            self.activation_failed.emit(self.record.ext_id, err)

        elif method and rpc_id:
            # Extension is asking Python to do something (window.*, workspace.*, fs.*)
            self.rpc_request.emit(self.record.ext_id, method, params, rpc_id)

        elif rpc_id and not method:
            # Response to our call — not used currently (we only call Node for wrapup)
            pass
