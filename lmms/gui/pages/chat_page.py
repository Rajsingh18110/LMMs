import os
import markdown
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QTextBrowser, QFrame, QFileDialog, QLabel
)
from PyQt6.QtCore import Qt, pyqtSlot
from lmms.backend.services.chat_service import ChatService
from lmms.backend.agents.core_agents.agents.manager import AgentManager

class ChatPage(QWidget):
    def __init__(self):
        super().__init__()
        # Temporary instance for MVP, later we'll inject this via a manager
        self.agent_manager = AgentManager(workspace_dir=os.path.expanduser("~/.lmms/workspaces/default"))
        self.chat_service = ChatService(self.agent_manager)
        
        self.chat_service.response_finished.connect(self.on_response_finished)
        self.chat_service.error_occurred.connect(self.on_error_occurred)
        self.chat_service.chunk_received.connect(self.on_chunk_received)

        self.messages = []
        self.attached_files = []
        self.is_streaming = False
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Chat Section ---
        self.chat_container = QWidget()
        chat_layout = QVBoxLayout(self.chat_container)
        chat_layout.setContentsMargins(20, 20, 20, 20)
        chat_layout.setSpacing(15)

        # Message History
        self.chat_history = QTextBrowser()
        self.chat_history.setOpenExternalLinks(True)
        self.chat_history.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                border: none;
                font-size: 15px;
                line-height: 1.5;
            }
        """)
        
        # Display welcome message
        self.append_message("system", "Welcome to LMMs! I'm your local AI powerhouse. How can I help you today?")
        
        chat_layout.addWidget(self.chat_history, stretch=1)

        # Input Area Container
        input_container = QFrame()
        input_container.setObjectName("InputContainer")
        input_container.setStyleSheet("""
            QFrame#InputContainer {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(10, 10, 10, 10)

        self.attachment_container = QWidget()
        self.attachment_layout = QHBoxLayout(self.attachment_container)
        self.attachment_layout.setContentsMargins(0, 0, 0, 0)
        self.attachment_container.setVisible(False)

        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Type a message or command (e.g., /fast, /code, /help)...")
        self.input_field.setMaximumHeight(100)
        self.input_field.setStyleSheet("border: none; background: transparent;")
        
        # Send Button Row
        btn_row = QHBoxLayout()
        self.attach_btn = QPushButton("📎 Attach")
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.clicked.connect(self.attach_files)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("PrimaryButton")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self.send_message)
        
        btn_row.addWidget(self.attach_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.send_btn)

        input_layout.addWidget(self.attachment_container)
        input_layout.addWidget(self.input_field)
        input_layout.addLayout(btn_row)

        chat_layout.addWidget(input_container)
        
        main_layout.addWidget(self.chat_container)

    def attach_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Attach", "", "All Files (*)")
        if files:
            for f in files:
                if len(self.attached_files) >= 20:
                    break
                if f not in self.attached_files:
                    self.attached_files.append(f)
            self.update_attachment_ui()

    def remove_attachment(self, file_path):
        if file_path in self.attached_files:
            self.attached_files.remove(file_path)
            self.update_attachment_ui()

    def update_attachment_ui(self):
        # Clear current tags
        while self.attachment_layout.count():
            item = self.attachment_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.attached_files:
            self.attachment_container.setVisible(False)
            return

        self.attachment_container.setVisible(True)
        for f in self.attached_files:
            tag = QFrame()
            tag.setStyleSheet("background-color: #21262d; border-radius: 4px; border: 1px solid #30363d;")
            tag_layout = QHBoxLayout(tag)
            tag_layout.setContentsMargins(5, 2, 5, 2)
            
            lbl = QLabel(os.path.basename(f))
            lbl.setStyleSheet("color: #c9d1d9; font-size: 11px;")
            
            rm_btn = QPushButton("x")
            rm_btn.setStyleSheet("color: #ff7b72; border: none; background: transparent; font-weight: bold;")
            rm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            rm_btn.clicked.connect(lambda checked, path=f: self.remove_attachment(path))
            
            tag_layout.addWidget(lbl)
            tag_layout.addWidget(rm_btn)
            self.attachment_layout.addWidget(tag)
            
        self.attachment_layout.addStretch()

    def render_messages(self):
        html = ""
        for msg in self.messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                name = "You"
                color = "#c9d1d9"
                bg = "#21262d"
            elif role == "system":
                name = "System"
                color = "#8b949e"
                bg = "transparent"
            else:
                name = "Assistant"
                color = "#e5e7eb"
                bg = "transparent"

            html_content = markdown.markdown(content, extensions=['fenced_code', 'tables'])
            html += f"""
            <div style="margin-bottom: 20px; padding: 10px; background-color: {bg}; border-radius: 8px;">
                <b style="color: #58a6ff;">{name}</b>
                <div style="margin-top: 5px; color: {color};">{html_content}</div>
            </div>
            """
        self.chat_history.setHtml(html)
        scrollbar = self.chat_history.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self.render_messages()

    def start_new_chat(self):
        self.messages.clear()
        self.append_message("system", "Started a new conversation. How can I help you?")

    @pyqtSlot()
    def send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            return
            
        self.input_field.clear()
        self.append_message("user", text)
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Thinking...")

        self.chat_service.start_chat(text)

    @pyqtSlot(str)
    def on_chunk_received(self, text):
        if not self.is_streaming:
            self.messages.append({"role": "assistant", "content": text})
            self.is_streaming = True
        else:
            self.messages[-1]["content"] = text
        self.render_messages()

    @pyqtSlot(str)
    def on_response_finished(self, status):
        self.is_streaming = False
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")

    @pyqtSlot(str)
    def on_error_occurred(self, error_msg):
        self.is_streaming = False
        self.append_message("system", f"<b>Error:</b> {error_msg}")

    def cleanup(self):
        if hasattr(self, 'chat_service') and self.chat_service.isRunning():
            self.chat_service.quit()
            self.chat_service.wait()
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")
