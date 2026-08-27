import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QLineEdit, QLabel
from PyQt6.QtCore import pyqtSlot, Qt

class DebugConsoleTab(QWidget):
    def __init__(self, dap_manager=None):
        super().__init__()
        self.dap_manager = dap_manager
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        self.output_area = QPlainTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setStyleSheet("background-color: #1e1e1e; color: #c9d1d9; border: none; font-family: monospace;")
        
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Evaluate expression...")
        self.input_line.setStyleSheet("""
            QLineEdit {
                background-color: #161b22; color: #c9d1d9; 
                border: 1px solid #30363d; border-radius: 4px; 
                padding: 6px; font-family: monospace;
            }
            QLineEdit:focus { border-color: #58a6ff; }
        """)
        self.input_line.returnPressed.connect(self.evaluate_expression)
        
        self.layout.addWidget(self.output_area)
        self.layout.addWidget(self.input_line)
        
        if self.dap_manager:
            self.set_dap_manager(self.dap_manager)
            
    def set_dap_manager(self, dap_manager):
        self.dap_manager = dap_manager
        self.dap_manager.messageReceived.connect(self.on_dap_message)
        
    @pyqtSlot(str)
    def on_dap_message(self, message: str):
        try:
            msg = json.loads(message)
            if msg.get("type") == "event" and msg.get("event") == "output":
                output = msg.get("body", {}).get("output", "")
                self.output_area.appendPlainText(output.strip())
            elif msg.get("type") == "response" and msg.get("command") == "evaluate":
                if msg.get("success"):
                    result = msg.get("body", {}).get("result", "")
                    self.output_area.appendPlainText(f"<- {result}")
                else:
                    err = msg.get("message", "Evaluation failed")
                    self.output_area.appendPlainText(f"Error: {err}")
        except Exception:
            pass

    @pyqtSlot()
    def evaluate_expression(self):
        expr = self.input_line.text().strip()
        if not expr or not self.dap_manager or not self.dap_manager.is_running:
            return
            
        self.output_area.appendPlainText(f"-> {expr}")
        self.input_line.clear()
        
        self.dap_manager.send_request("evaluate", {
            "expression": expr,
            "context": "repl"
        })
