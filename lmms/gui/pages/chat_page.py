import os
import markdown
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QTextBrowser, QFrame, QFileDialog, QLabel
)
from PyQt6.QtCore import Qt, pyqtSlot
from lmms.backend.services.chat_service import ChatService
from lmms.backend.agents.core_agents.agents.manager import AgentManager

class ChatInputEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.send_callback = None
        
    def keyPressEvent(self, event):
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            if self.send_callback:
                self.send_callback()
            event.accept()
        else:
            super().keyPressEvent(event)

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
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        # Message History
        self.chat_history = QTextBrowser()
        self.chat_history.setOpenExternalLinks(False) # We handle links manually for Copy Code
        self.chat_history.anchorClicked.connect(self.on_anchor_clicked)
        self.chat_history.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                border: none;
                font-size: 15px;
                line-height: 1.5;
            }
        """)
        
        self.code_blocks = {} # id -> code content
        
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

        self.input_field = ChatInputEdit()
        self.input_field.setObjectName("chatInput")
        self.input_field.setStyleSheet("border: none; background: transparent;")
        self.input_field.setPlaceholderText("Type a message or command (e.g., /fast, /code, /help)...")
        self.input_field.setMaximumHeight(100)
        
        # Send Button Row and Model Selector
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 5, 0, 0)
        
        from PyQt6.QtWidgets import QComboBox
        self.model_combo = QComboBox()
        self.refresh_models()
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        self.model_combo.setStyleSheet("""
            QComboBox {
                background: transparent;
                border: none;
                color: #8b949e;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        
        self.approvals_combo = QComboBox()
        self.approvals_combo.addItems(["🛡 Default", "🛡 Auto"])
        self.approvals_combo.setStyleSheet("""
            QComboBox {
                background: transparent;
                border: none;
                color: #8b949e;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        
        self.attach_btn = QPushButton("+")
        self.attach_btn.setObjectName("attachBtn")
        self.attach_btn.setToolTip("Attach Context")
        self.attach_btn.setFixedSize(24, 24)
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8b949e;
                font-size: 18px;
                padding: 0px;
            }
            QPushButton:hover {
                color: #c9d1d9;
            }
        """)
        self.attach_btn.clicked.connect(self.attach_files)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setMinimumSize(85, 26)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #30363d;
                color: #ffffff;
                border-radius: 13px;
                border: none;
                font-size: 13px;
                font-weight: bold;
                padding: 0px 10px;
            }
            QPushButton:hover {
                background-color: #58a6ff;
            }
        """)
        self.send_btn.clicked.connect(self.send_message)
        
        bottom_row.addWidget(self.attach_btn)
        bottom_row.addWidget(self.model_combo)
        bottom_row.addWidget(self.approvals_combo)
        bottom_row.addStretch()
        bottom_row.addWidget(self.send_btn)

        input_layout.addWidget(self.attachment_container)
        input_layout.addWidget(self.input_field)
        self.input_field.send_callback = self.send_message
        input_layout.addLayout(bottom_row)

        chat_layout_wrapper = QHBoxLayout()
        chat_layout_wrapper.setContentsMargins(10, 5, 10, 15)
        chat_layout_wrapper.addWidget(input_container)
        
        chat_layout.addLayout(chat_layout_wrapper)
        
        main_layout.addWidget(self.chat_container)

    def attach_files(self):
        files = []
        import sys
        use_zenity = False
        if sys.platform.startswith("linux"):
            import subprocess, shutil
            if shutil.which('zenity'):
                use_zenity = True
                try:
                    result = subprocess.run(['zenity', '--file-selection', '--multiple', '--title=Select Files to Attach'], capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout.strip():
                        files = result.stdout.strip().split('|')
                except Exception:
                    use_zenity = False
                
        if not use_zenity and not files:
            from PyQt6.QtWidgets import QFileDialog
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
        import re
        import uuid
        
        html = ""
        self.code_blocks.clear()
        
        for msg in self.messages:
            role = msg["role"]
            content = msg["content"]
            
            # Strip out internal think and tool_call tags from being displayed
            content = re.sub(r'<think>.*?(</think>|$)', '', content, flags=re.DOTALL).strip()
            content = re.sub(r'<tool_call>.*?(</tool_call>|$)', '', content, flags=re.DOTALL).strip()
            
            try:
                from lmms.engine.response_cleaner import strip_hidden_reasoning
                if role == "assistant":
                    content = strip_hidden_reasoning(content)
            except Exception:
                pass

            html_content = markdown.markdown(content, extensions=['fenced_code', 'tables'])
            
            # Inject Copy Code buttons
            def replace_code_block(match):
                code_id = str(uuid.uuid4())
                import html as html_lib
                code = match.group(1)
                raw_code = html_lib.unescape(code)
                raw_code = re.sub(r'<[^>]+>', '', raw_code)
                self.code_blocks[code_id] = raw_code
                return f'<div style="background-color: #0d1117; padding: 8px; border: 1px solid #30363d; border-radius: 5px; margin-bottom: 10px;"><div style="text-align: right;"><a href="copy:{code_id}" style="color: #58a6ff; text-decoration: none; font-size: 12px; font-weight: bold;">[Copy Code]</a></div><pre style="margin: 0; padding-top: 5px;"><code>{code}</code></pre></div>'
            
            html_content = re.sub(r'<pre><code>(.*?)</code></pre>', replace_code_block, html_content, flags=re.DOTALL)
            
            if role == "user":
                html += f"""
                <div style="text-align: right; margin: 10px 0;">
                    <span style="background-color: #2b2d31; color: white; padding: 10px 15px; border-radius: 8px; display: inline-block;">
                        <b style="color: #58a6ff;">You</b><br>
                        {html_content}
                    </span>
                </div>
                """
            elif role == "system":
                html += f"""
                <div style="text-align: center; margin: 10px 0;">
                    <span style="background-color: transparent; color: #8b949e; padding: 10px 15px; display: inline-block; text-align: center;">
                        <b style="color: #58a6ff;">System</b><br>
                        {html_content}
                    </span>
                </div>
                """
            else:
                html += f"""
                <div style="text-align: left; margin: 10px 0;">
                    <span style="background-color: transparent; color: #cccccc; padding: 10px 15px; display: inline-block;">
                        <b style="color: #58a6ff;">Assistant</b><br>
                        {html_content}
                    </span>
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
        if not text and not self.attached_files:
            return
            
        full_text = text
        num_attached = len(self.attached_files)
        if self.attached_files:
            if full_text:
                full_text += "\n\n"
            full_text += "[Attached Files]:\n"
            import os
            for file_path in self.attached_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        file_content = f.read()
                        full_text += f"\n--- {os.path.basename(file_path)} ---\n{file_content}\n"
                except Exception as e:
                    full_text += f"\n--- {os.path.basename(file_path)} ---\n[Error reading file: {e}]\n"
            
            # Clear attachments after processing
            self.attached_files.clear()
            self.update_attachment_ui()
            
            # Append a UI-friendly message for the user's view
            if text:
                display_msg = f"{text}\n\n📎 *Attached {num_attached} files*"
            else:
                display_msg = f"📎 *Attached {num_attached} files*"
        else:
            display_msg = text

        self.input_field.clear()
        self.append_message("user", display_msg)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Stop")
        try:
            self.send_btn.clicked.disconnect()
        except TypeError:
            pass
        self.send_btn.clicked.connect(self.stop_generation)
        
        self.chat_service.start_chat(full_text)

    @pyqtSlot(str)
    def on_chunk_received(self, chunk: str):
        from lmms.engine.response_cleaner import strip_hidden_reasoning
        # Do not render internal thinking tags in the UI
        clean_text = strip_hidden_reasoning(chunk)
        
        is_thinking = "<think>" in chunk and chunk.count("<think>") > chunk.count("</think>")
        if is_thinking:
            indicator = "\n\n*🧠 Model is thinking...*"
            if not clean_text.strip():
                clean_text = indicator.strip()
            else:
                clean_text += indicator
                
        if clean_text:
            if not self.is_streaming:
                self.messages.append({"role": "assistant", "content": clean_text})
                self.is_streaming = True
            else:
                self.messages[-1]["content"] = clean_text
            self.render_messages()

    @pyqtSlot(str)
    def on_response_finished(self, status):
        self.is_streaming = False
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")

    @pyqtSlot(str)
    def on_error_occurred(self, error_msg):
        self.is_streaming = False
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")
        self.append_message("system", f"<b>Error:</b> {error_msg}")

    def on_anchor_clicked(self, url):
        url_str = url.toString()
        if url_str.startswith("copy:"):
            code_id = url_str.split("copy:")[1]
            if code_id in self.code_blocks:
                from PyQt6.QtWidgets import QApplication
                QApplication.clipboard().setText(self.code_blocks[code_id])
                # Show subtle notification in input field placeholder
                original_placeholder = self.input_field.placeholderText()
                self.input_field.setPlaceholderText("Code copied to clipboard!")
                import threading
                def reset_placeholder():
                    self.input_field.setPlaceholderText(original_placeholder)
                threading.Timer(2.0, reset_placeholder).start()
        else:
            import webbrowser
            webbrowser.open(url_str)

    def cleanup(self):
        self.is_streaming = False
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")
        try:
            self.send_btn.clicked.disconnect()
        except TypeError:
            pass
        self.send_btn.clicked.connect(self.send_message)

    def stop_generation(self):
        if hasattr(self, 'chat_service') and self.chat_service.isRunning():
            self.chat_service.terminate()
            self.chat_service.wait()
        self.cleanup()
        self.append_message("system", "\n[Generation Stopped by User]\n")

    def refresh_models(self):
        try:
            import requests
            r = requests.get("http://localhost:11435/v1/models/list", timeout=1)
            if r.status_code == 200:
                models = r.json().get("models", [])
                self.model_combo.blockSignals(True)
                self.model_combo.clear()
                self.model_combo.addItem("☁ Cloud: openai")
                for m in models:
                    name = m["name"] if isinstance(m, dict) else m
                    self.model_combo.addItem(f"🖥 Local: {name}")
                self.model_combo.blockSignals(False)
            
            r_active = requests.get("http://localhost:11435/v1/models/ps", timeout=1)
            if r_active.status_code == 200:
                active = r_active.json().get("loaded_models", [])
                if active:
                    active_name = active[0]
                    for i in range(self.model_combo.count()):
                        if active_name in self.model_combo.itemText(i):
                            self.model_combo.blockSignals(True)
                            self.model_combo.setCurrentIndex(i)
                            self.model_combo.blockSignals(False)
                            break
        except Exception:
            self.model_combo.addItems(["🖥 Local: default", "☁ Cloud: openai"])

    def on_model_changed(self, text: str):
        if not text or "Local:" not in text:
            return
        model_name = text.split("Local: ")[-1].strip()
        import threading
        def do_load():
            try:
                import requests
                requests.post("http://localhost:11435/v1/models/load", json={"model_name": model_name}, timeout=10)
            except Exception:
                pass
        threading.Thread(target=do_load, daemon=True).start()
