"""Python extension host shim for LMMs.

This is a lightweight runtime for extensions whose manifest declares a Python
entrypoint. It keeps the extension manager unified while allowing Python-based
plugins and LMMs-specific extensions to participate in the same extension
lifecycle model.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal


class PythonExtensionHost(QObject):
    log_line = pyqtSignal(str, str, str)
    command_registered = pyqtSignal(str, str, str)
    activated = pyqtSignal(str)
    activation_failed = pyqtSignal(str, str)
    rpc_request = pyqtSignal(str, str, object, object)

    def __init__(self, record, workspace_root: str | None = None, parent=None):
        super().__init__(parent)
        self.record = record
        self.workspace_root = workspace_root
        self._proc: subprocess.Popen | None = None

    def start(self):
        if not self.record.path:
            self.activation_failed.emit(self.record.ext_id, "No extension path found.")
            return

        manifest_path = os.path.join(self.record.path, "extension", "package.json")
        if not os.path.exists(manifest_path):
            manifest_path = os.path.join(self.record.path, "package.json")

        if not os.path.exists(manifest_path):
            self.activation_failed.emit(self.record.ext_id, "Missing package.json in Python extension.")
            return

        try:
            import json
            with open(manifest_path, "r", encoding="utf-8") as fh:
                manifest = json.load(fh)
        except Exception as exc:
            self.activation_failed.emit(self.record.ext_id, f"Failed to load manifest: {exc}")
            return

        entry = manifest.get("main") or ""
        if not entry:
            self.activation_failed.emit(self.record.ext_id, "Python extension has no entrypoint.")
            return

        entry_path = os.path.join(self.record.path, "extension", entry)
        if not os.path.exists(entry_path):
            entry_path = os.path.join(self.record.path, entry)

        if not os.path.exists(entry_path):
            self.activation_failed.emit(self.record.ext_id, f"Entry point not found: {entry}")
            return

        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(self.record.path).resolve()) + os.pathsep + env.get("PYTHONPATH", "")
        try:
            self._proc = subprocess.Popen(
                [sys.executable, entry_path, "--workspace", str(self.workspace_root or os.getcwd())],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            self.log_line.emit(self.record.ext_id, "info", f"Python extension host started: {entry_path}")
            self.activated.emit(self.record.ext_id)
        except Exception as exc:
            self.activation_failed.emit(self.record.ext_id, f"Failed to start Python host: {exc}")

    def stop(self):
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                pass
            self._proc = None

    def send_to_node(self, obj: dict):
        if self._proc and self._proc.stdin:
            try:
                self._proc.stdin.write(str(obj) + "\n")
                self._proc.stdin.flush()
            except Exception:
                pass

    def reply_rpc(self, rpc_id: str, result=None, error: str | None = None):
        if error:
            self.log_line.emit(self.record.ext_id, "error", f"Python host RPC error: {error}")
        else:
            self.log_line.emit(self.record.ext_id, "info", f"Python host RPC result for {rpc_id}")
