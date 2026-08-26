"""
LSPManager — stdio ↔ JSON-RPC bridge between Monaco (JS) and a local LSP server.

One instance is shared across all editor tabs (singleton via code_editor._get_lsp).
"""
import subprocess
import threading
import json
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class LSPManager(QObject):
    # LSP server response → JS (forwarded by PythonBridge.sendLspMessage)
    messageReceived = pyqtSignal(str)

    def __init__(self, command: list, parent=None):
        super().__init__(parent)
        self.command    = command
        self.process    = None
        self._thread    = None
        self.is_running = False

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        if not self.command:
            return  # no LSP available
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,   # raw bytes — Content-Length framing
            )
            self.is_running = True
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()
            print(f"[LSP] Process started (PID {self.process.pid}): {self.command}")
        except FileNotFoundError:
            print(f"[LSP] Command not found: {self.command[0]}. LSP disabled.")
            self.command = []
        except Exception as e:
            print(f"[LSP] Failed to start {self.command}: {e}")
            self.command = []

    def stop(self):
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                pass
            self.process = None
        print("[LSP] Stopped.")

    # ── write (JS → LSP) ─────────────────────────────────────────────────────

    @pyqtSlot(str)
    def sendMessage(self, message: str):
        """Forward a JSON-RPC message from the Monaco client to the LSP server."""
        if not self.process or not self.is_running:
            return
        try:
            body   = message.encode("utf-8")
            header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
            self.process.stdin.write(header + body)
            self.process.stdin.flush()
        except Exception as e:
            print(f"[LSP] Write error: {e}")

    # ── read loop (LSP → JS) ──────────────────────────────────────────────────

    def _read_loop(self):
        """
        Reads Content-Length–framed JSON-RPC from the LSP process stdout and
        emits `messageReceived` so PythonBridge can forward it to the JS client.
        """
        while self.is_running and self.process:
            try:
                content_length = 0
                # Read headers
                while True:
                    raw = self.process.stdout.readline()
                    if not raw:
                        # EOF — process died
                        self.is_running = False
                        return
                    line = raw.decode("utf-8", errors="replace").rstrip()
                    if not line:
                        break   # empty line = end of headers
                    if line.lower().startswith("content-length:"):
                        content_length = int(line.split(":", 1)[1].strip())

                if content_length <= 0:
                    continue

                body_bytes = self.process.stdout.read(content_length)
                body       = body_bytes.decode("utf-8", errors="replace")

                # Side-effect: feed diagnostics to DiagnosticManager
                self._handle_diagnostics(body)

                # Forward to Monaco
                self.messageReceived.emit(body)

            except Exception as e:
                if self.is_running:
                    print(f"[LSP] Read error: {e}")
                break

    def _handle_diagnostics(self, body: str):
        try:
            msg = json.loads(body)
            if msg.get("method") == "textDocument/publishDiagnostics":
                params      = msg.get("params", {})
                uri         = params.get("uri")
                diagnostics = params.get("diagnostics", [])
                if uri:
                    from lmms.gui.utils.diagnostic_manager import DiagnosticManager
                    DiagnosticManager.get_instance().update_diagnostics(uri, diagnostics)
        except Exception:
            pass
