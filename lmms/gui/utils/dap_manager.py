import subprocess
import json
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
from lmms.gui.utils.output_channel import OutputChannelRegistry

class DAPManager(QObject):
    # DAP server response/event → JS or Python (forwarded as needed)
    messageReceived = pyqtSignal(str)

    def __init__(self, command: list, parent=None):
        super().__init__(parent)
        self.command    = command
        self.process    = None
        self._thread    = None
        self.is_running = False
        self.seq        = 1

    class ReadThread(QThread):
        def __init__(self, dap_manager):
            super().__init__()
            self.dap_manager = dap_manager
            
        def run(self):
            self.dap_manager._read_loop()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        if not self.command:
            return
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
            )
            self.is_running = True
            self._thread = self.ReadThread(self)
            self._thread.start()
            OutputChannelRegistry.get_instance().append("DAP", f"[DAP] Process started (PID {self.process.pid}): {self.command}")
        except FileNotFoundError:
            OutputChannelRegistry.get_instance().append("DAP", f"[DAP] Command not found: {self.command[0]}")
            self.command = []
        except Exception as e:
            OutputChannelRegistry.get_instance().append("DAP", f"[DAP] Failed to start {self.command}: {e}")
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
        OutputChannelRegistry.get_instance().append("DAP", "[DAP] Stopped.")

    # ── write (Python → DAP) ─────────────────────────────────────────────────────

    @pyqtSlot(str)
    def sendMessage(self, message: str):
        if not self.process or not self.is_running:
            return
        try:
            body   = message.encode("utf-8")
            header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
            self.process.stdin.write(header + body)
            self.process.stdin.flush()
        except Exception as e:
            OutputChannelRegistry.get_instance().append("DAP", f"[DAP] Write error: {e}")

    def send_request(self, command: str, arguments: dict = None):
        msg = {
            "seq": self.seq,
            "type": "request",
            "command": command
        }
        if arguments:
            msg["arguments"] = arguments
            
        self.seq += 1
        self.sendMessage(json.dumps(msg))

    # ── read loop (DAP → Python) ──────────────────────────────────────────────────

    def _read_loop(self):
        while self.is_running and self.process:
            try:
                content_length = 0
                while True:
                    raw = self.process.stdout.readline()
                    if not raw:
                        self.is_running = False
                        return
                    line = raw.decode("utf-8", errors="replace").rstrip()
                    if not line:
                        break
                    if line.lower().startswith("content-length:"):
                        content_length = int(line.split(":", 1)[1].strip())

                if content_length <= 0:
                    continue

                body_bytes = self.process.stdout.read(content_length)
                body       = body_bytes.decode("utf-8", errors="replace")

                self.messageReceived.emit(body)
            except Exception as e:
                if self.is_running:
                    OutputChannelRegistry.get_instance().append("DAP", f"[DAP] Read error: {e}")
                break
