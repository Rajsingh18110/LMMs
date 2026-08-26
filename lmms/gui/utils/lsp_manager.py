import subprocess
import threading
import json
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

class LSPManager(QObject):
    # Signals for communicating with Monaco (JS)
    messageReceived = pyqtSignal(str)
    
    def __init__(self, command, parent=None):
        super().__init__(parent)
        self.command = command
        self.process = None
        self.thread = None
        self.is_running = False

    def start(self):
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False # Use bytes for raw Content-Length HTTP-like headers
            )
            self.is_running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
        except Exception as e:
            print(f"Failed to start LSP {self.command}: {e}")

    def stop(self):
        self.is_running = False
        if self.process:
            self.process.terminate()
            self.process = None

    @pyqtSlot(str)
    def sendMessage(self, message):
        """Called from JS to send JSON-RPC to the native LSP process"""
        if self.process and self.is_running:
            try:
                # message is a JSON string
                body = message.encode('utf-8')
                header = f"Content-Length: {len(body)}\r\n\r\n".encode('utf-8')
                self.process.stdin.write(header + body)
                self.process.stdin.flush()
            except Exception as e:
                print(f"Error writing to LSP: {e}")

    def _read_loop(self):
        """Reads JSON-RPC from the native LSP process and sends it to JS"""
        while self.is_running and self.process:
            try:
                # Read headers
                content_length = 0
                while True:
                    line = self.process.stdout.readline()
                    if not line:
                        break
                    line = line.decode('utf-8').strip()
                    if not line:
                        break # Empty line signifies end of headers
                    if line.lower().startswith("content-length:"):
                        content_length = int(line.split(":")[1].strip())
                        
                if content_length > 0:
                    body = self.process.stdout.read(content_length).decode('utf-8')
                    # Emit to Qt, which forwards to JS via QWebChannel
                    self.messageReceived.emit(body)
            except Exception as e:
                if self.is_running:
                    print(f"LSP Read Error: {e}")
                break
