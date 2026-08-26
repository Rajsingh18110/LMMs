"""
chat_page.py

Main chat interface page for LMMs.

Signal architecture:
    ChatService → ChatEvent → on_event_received() → message state → UI update

Each ChatEvent is routed by type:
  reasoning_delta  → message.thought  → ThoughtPanelWidget
  assistant_delta  → message.content  → ChatTextBrowser(s)
  tool_*           → message.tool_events (future TaskPanel)
  completed        → finish_generation(done)
  error            → finish_generation(error)
  no_response      → finish_generation(error, "No response")
  cancelled        → finish_generation(cancelled)
"""
import os
import threading
import re as _re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QFrame, QFileDialog, QLabel, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer, pyqtSignal

from lmms.backend.services.chat_service import ChatService
from lmms.backend.services.chat_event import ChatEvent
from lmms.backend.agents.core_agents.agents.manager import AgentManager
from lmms.gui.state.chat_message import ChatMessage
from lmms.gui.widgets.chat import ChatInputEdit, MessageListWidget
from lmms.backend.config.config import ConfigManager


class ChatPage(QWidget):
    def __init__(self):
        super().__init__()
        workspace_dir = ConfigManager().get("workspace_dir", os.path.expanduser("~/.lmms/workspaces/default"))
        self.agent_manager = AgentManager(
            workspace_dir=workspace_dir
        )
        self.chat_service = ChatService(self.agent_manager)

        # Connect ChatService signals
        self.chat_service.event_received.connect(self.on_event_received)
        self.chat_service.response_finished.connect(self.on_response_finished)
        self.chat_service.error_occurred.connect(self.on_error_occurred)
        self.chat_service.cancelled.connect(self.on_cancelled)
        self.chat_service.no_response.connect(self.on_no_response)

        # Message state
        self.messages: list[ChatMessage] = []
        self.attached_files: list[str] = []
        self.is_streaming = False

        # Active generation tracking by stable message ID
        self.active_message_id: str | None = None

        # Timer to throttle UI updates at 20fps
        self.update_timer = QTimer()
        self.update_timer.setInterval(50)
        self.update_timer.timeout.connect(self.flush_ui_update)

        # Pending deltas accumulated between timer ticks
        self._pending_content = ""
        self._pending_thought = ""
        self._has_pending = False

        self.init_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # UI Construction
    # ─────────────────────────────────────────────────────────────────────────
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Chat Area ─────────────────────────────────────────────────────
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        self.message_list = MessageListWidget()
        self.message_list.link_clicked.connect(self.on_link_clicked)
        self.message_list.edit_requested.connect(self.on_edit_requested)
        self.message_list.delete_requested.connect(self.on_delete_requested)
        self.message_list.retry_requested.connect(self.on_retry_requested)
        chat_layout.addWidget(self.message_list, stretch=1)

        # ── Input Area ────────────────────────────────────────────────────
        input_outer = QHBoxLayout()
        input_outer.setContentsMargins(16, 0, 16, 14)

        input_container = QFrame()
        input_container.setObjectName("ChatInputFrame")
        input_container.setStyleSheet("""
            QFrame#ChatInputFrame {
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 8px;
            }
            QFrame#ChatInputFrame:focus-within {
                border-color: #2563eb;
            }
        """)
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(10, 8, 10, 6)
        input_layout.setSpacing(4)

        # Attachment chips
        self.attachment_container = QWidget()
        self.attachment_layout = QHBoxLayout(self.attachment_container)
        self.attachment_layout.setContentsMargins(0, 0, 0, 0)
        self.attachment_container.setVisible(False)
        input_layout.addWidget(self.attachment_container)

        # Text input
        self.input_field = ChatInputEdit()
        self.input_field.setObjectName("chatInput")
        self.input_field.setStyleSheet(
            "border: none; background: transparent; color: #e5e7eb; font-size: 14px;"
        )
        self.input_field.setPlaceholderText("Message LMMs…")
        self.input_field.setMaximumHeight(140)
        self.input_field.send_callback = self.send_message
        self.input_field.files_pasted.connect(self.add_attached_files)
        input_layout.addWidget(self.input_field)

        # Bottom toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 2, 0, 0)
        toolbar.setSpacing(6)

        self.attach_btn = QPushButton("+")
        self.attach_btn.setToolTip("Attach file")
        self.attach_btn.setFixedSize(26, 26)
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                color: #c9d1d9; font-size: 20px; font-weight: normal; border-radius: 4px;
            }
            QPushButton:hover { background: #1f2937; color: #ffffff; }
        """)
        self.attach_btn.clicked.connect(self.attach_files)

        self.model_combo = QComboBox()
        self.model_combo.setFixedHeight(24)
        self.model_combo.setStyleSheet("""
            QComboBox {
                background: #1f2937; border: 1px solid #374151;
                border-radius: 4px; color: #9ca3af;
                font-size: 11px; padding: 2px 8px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #111827; color: #e5e7eb;
                selection-background-color: #2563eb;
                border: 1px solid #374151;
            }
        """)
        self.refresh_models()

        self.mic_btn = QPushButton("🎙️")
        self.mic_btn.setToolTip("Voice Input (Coming Soon)")
        self.mic_btn.setFixedSize(26, 26)
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                color: #8b949e; font-size: 14px; border-radius: 4px;
            }
            QPushButton:hover { background: #1f2937; color: #c9d1d9; }
        """)

        self.send_btn = QPushButton("➔")
        self.send_btn.setFixedSize(30, 30)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_send_ready()

        toolbar.addWidget(self.attach_btn)
        toolbar.addWidget(self.model_combo)
        toolbar.addStretch()
        toolbar.addWidget(self.mic_btn)
        toolbar.addWidget(self.send_btn)
        input_layout.addLayout(toolbar)

        input_outer.addWidget(input_container)
        chat_layout.addLayout(input_outer)
        main_layout.addWidget(chat_container)

        self.start_new_chat()

    # ── Send button states ────────────────────────────────────────────────────
    def _set_send_ready(self):
        try:
            self.send_btn.clicked.disconnect()
        except TypeError:
            pass
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setText("➔")
        self.send_btn.setFixedSize(30, 30)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: #2563eb; color: #fff;
                border-radius: 15px; border: none;
                font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { background: #3b82f6; }
            QPushButton:disabled { background: #1f2937; color: #6b7280; }
        """)
        self.input_field.setReadOnly(False)

    # Keep old name for backward compat
    def set_send_btn_ready(self):
        self._set_send_ready()

    def set_send_btn_stop(self):
        try:
            self.send_btn.clicked.disconnect()
        except TypeError:
            pass
        self.send_btn.clicked.connect(self.stop_generation)
        self.send_btn.setText("■")
        self.send_btn.setFixedSize(30, 30)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: #374151; color: #f87171;
                border-radius: 15px; border: none;
                font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #4b5563; }
        """)
        self.input_field.setReadOnly(True)

    # ─────────────────────────────────────────────────────────────────────────
    def update_workspace(self, folder: str):
        self.agent_manager = AgentManager(workspace_dir=folder)
        self.chat_service = ChatService(self.agent_manager)
        
        # Re-connect signals to new ChatService
        self.chat_service.event_received.connect(self.on_event_received)
        self.chat_service.response_finished.connect(self.on_response_finished)
        self.chat_service.error_occurred.connect(self.on_error_occurred)
        self.chat_service.cancelled.connect(self.on_cancelled)
        self.chat_service.no_response.connect(self.on_no_response)

    # ─────────────────────────────────────────────────────────────────────────
    # Model management
    # ─────────────────────────────────────────────────────────────────────────
    def refresh_models(self):
        from lmms.backend.core.registry.model_registry import ModelRegistry
        models = ModelRegistry.list()
        
        # We only want to show Text or Vision models (no Audio/ImageGeneration models for normal chat usually, but fine to show all enabled for now)
        models = [m for m in models if m.get("enabled", True)]
        
        # Sort by display name
        models.sort(key=lambda x: x.get("display_name", ""))
        
        self.model_combo.clear()
        
        if not models:
            self.model_combo.addItem("No Models")
        else:
            saved_model_id = ConfigManager().get("chat_selected_model", "")
            idx = 0
            for i, m in enumerate(models):
                d_name = m.get("display_name") or m.get("model_id") or m.get("id", "Unknown")
                p_id = m.get("provider_id") or m.get("provider", "Unknown")
                full_name = f"{d_name} ({p_id})"
                self.model_combo.addItem(full_name, userData=m.get("internal_id", m.get("id")))
                
                if m.get("internal_id", m.get("id")) == saved_model_id:
                    idx = i
                    
            self.model_combo.setCurrentIndex(idx)
            
        # Connect change event to save preference
        try: self.model_combo.currentIndexChanged.disconnect()
        except: pass
        
        def on_index_changed(index):
            if index >= 0:
                data = self.model_combo.itemData(index)
                if data:
                    ConfigManager().set("chat_selected_model", data)
                    
        self.model_combo.currentIndexChanged.connect(on_index_changed)

    # ─────────────────────────────────────────────────────────────────────────
    # File attachment
    # ─────────────────────────────────────────────────────────────────────────
    def attach_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files to Attach", "", "All Files (*)"
        )
        self.add_attached_files(files)

    def add_attached_files(self, files: list[str]):
        for f in files:
            if f not in self.attached_files and len(self.attached_files) < 20:
                self.attached_files.append(f)
        self.update_attachment_ui()

    def remove_attachment(self, file_path: str):
        if file_path in self.attached_files:
            self.attached_files.remove(file_path)
        self.update_attachment_ui()

    def update_attachment_ui(self):
        while self.attachment_layout.count():
            item = self.attachment_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.attached_files:
            self.attachment_container.setVisible(False)
            return
        self.attachment_container.setVisible(True)
        for f in self.attached_files:
            chip = QFrame()
            chip.setStyleSheet(
                "background: #1f2937; border-radius: 4px; border: 1px solid #374151;"
            )
            cl = QHBoxLayout(chip)
            cl.setContentsMargins(5, 2, 5, 2)
            cl.setSpacing(4)
            lbl = QLabel(os.path.basename(f))
            lbl.setStyleSheet("color: #9ca3af; font-size: 11px;")
            rm = QPushButton("×")
            rm.setStyleSheet(
                "color: #ef4444; border: none; background: transparent; font-size: 13px;"
            )
            rm.setCursor(Qt.CursorShape.PointingHandCursor)
            rm.clicked.connect(lambda _, p=f: self.remove_attachment(p))
            cl.addWidget(lbl)
            cl.addWidget(rm)
            self.attachment_layout.addWidget(chip)
        self.attachment_layout.addStretch()

    # ─────────────────────────────────────────────────────────────────────────
    # Send / Stop
    # ─────────────────────────────────────────────────────────────────────────
    def start_new_chat(self):
        self.message_list.clear()

    @pyqtSlot()
    def send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text and not self.attached_files:
            return
        if self.is_streaming:
            return

        # Build the full prompt for the backend (includes file contents)
        full_text = text
        num_attached = len(self.attached_files)

        if self.attached_files:
            if full_text:
                full_text += "\n\n"
            full_text += "[Attached Files]:\n"
            for file_path in self.attached_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as fh:
                        full_text += f"\n--- {os.path.basename(file_path)} ---\n{fh.read()}\n"
                except Exception as e:
                    full_text += f"\n--- {os.path.basename(file_path)} ---\n[Error: {e}]\n"
            self.attached_files.clear()
            self.update_attachment_ui()
            display_msg = (
                f"{text}\n\n📎 *{num_attached} file(s) attached*" if text
                else f"📎 *{num_attached} file(s) attached*"
            )
        else:
            display_msg = text  # Just the plain text — no permission label

        self.input_field.clear()

        # Create and display user message
        user_msg = ChatMessage(role="user", content=display_msg)
        self.messages.append(user_msg)
        self.message_list.add_message(user_msg)

        # Determine active model name
        active_model = self.model_combo.currentData()
        if not active_model:
            active_model = "LMMs Engine"

        # Create assistant placeholder
        asst_msg = ChatMessage(
            role="assistant",
            status="generating",
            model_name=self.model_combo.currentText().strip() or active_model
        )
        self.messages.append(asst_msg)
        self.message_list.add_message(asst_msg)

        # Track active generation by stable ID
        self.active_message_id = asst_msg.id
        self.is_streaming = True
        self._pending_content = ""
        self._pending_thought = ""
        self._has_pending = False
        self.set_send_btn_stop()

        # Start backend generation — pass message_id so ChatService can tag events
        self.chat_service.start_chat(full_text, message_id=asst_msg.id, model_name=active_model)

    def stop_generation(self):
        self.chat_service.cancel()

    # ─────────────────────────────────────────────────────────────────────────
    # Event routing
    # ─────────────────────────────────────────────────────────────────────────
    @pyqtSlot(object)
    def on_event_received(self, event: ChatEvent):
        """Route a ChatEvent to the correct message state field."""
        if event.message_id != self.active_message_id:
            return  # Stale event from a cancelled generation

        if event.type == "reasoning_delta":
            self._pending_thought += event.content
            self._has_pending = True
            if not self.update_timer.isActive():
                self.update_timer.start()

        elif event.type == "assistant_delta":
            self._pending_content += event.content
            self._has_pending = True
            if not self.update_timer.isActive():
                self.update_timer.start()

        # Future: tool_started, tool_finished, task_started, task_step → TaskPanel
        # For now, silently accept them

    @pyqtSlot()
    def flush_ui_update(self):
        """Apply accumulated deltas to the active message and redraw."""
        if not self._has_pending:
            return
        msg = self._active_message()
        if not msg:
            self.update_timer.stop()
            return

        if self._pending_thought:
            msg.thought += self._pending_thought
            self._pending_thought = ""
        if self._pending_content:
            msg.content += self._pending_content
            self._pending_content = ""
        self._has_pending = False

        self.message_list.update_message(msg)

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle signals
    # ─────────────────────────────────────────────────────────────────────────
    @pyqtSlot(str)
    def on_response_finished(self, _status: str):
        self.finish_generation()

    @pyqtSlot()
    def on_cancelled(self):
        self.finish_generation(is_cancelled=True)

    @pyqtSlot()
    def on_no_response(self):
        msg = self._active_message()
        if msg and not msg.content.strip():
            msg.content = (
                "No response received.\n\n"
                "Check that the model is loaded and the engine is running."
            )
        self.finish_generation(is_error=True)

    @pyqtSlot(str)
    def on_error_occurred(self, error_msg: str):
        msg = self._active_message()
        if msg:
            msg.content = f"Generation failed: {error_msg}"
        self.finish_generation(is_error=True)

    def finish_generation(self, is_error: bool = False, is_cancelled: bool = False):
        self.is_streaming = False
        self.update_timer.stop()

        # Final flush
        if self._has_pending:
            self.flush_ui_update()

        msg = self._active_message()
        if msg:
            if is_error:
                msg.set_status("error")
            elif is_cancelled:
                msg.set_status("cancelled")
            else:
                msg.set_status("done")
            self.message_list.update_message(msg)

        self.active_message_id = None
        self._pending_content = ""
        self._pending_thought = ""
        self._has_pending = False
        self._set_send_ready()

    # ─────────────────────────────────────────────────────────────────────────
    # Message lookup helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _active_message(self) -> ChatMessage | None:
        if not self.active_message_id:
            return None
        return self._find_message(self.active_message_id)

    def _find_message(self, msg_id: str) -> ChatMessage | None:
        for m in self.messages:
            if m.id == msg_id:
                return m
        return None

    def _find_paired_assistant(self, user_msg_id: str) -> ChatMessage | None:
        for i, m in enumerate(self.messages):
            if m.id == user_msg_id:
                if i + 1 < len(self.messages) and self.messages[i + 1].role == "assistant":
                    return self.messages[i + 1]
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Message actions: Edit / Delete / Retry
    # ─────────────────────────────────────────────────────────────────────────
    def on_edit_requested(self, msg_id: str):
        if self.is_streaming:
            return
        user_msg = self._find_message(msg_id)
        if not user_msg or user_msg.role != "user":
            return
        # Restore plain text to input field (strip any markdown/HTML)
        plain = _re.sub(r'<[^>]+>', '', user_msg.content).strip()
        self.input_field.setPlainText(plain)
        self.input_field.setFocus()
        # Remove associated assistant response
        paired = self._find_paired_assistant(msg_id)
        if paired:
            self.message_list.remove_message(paired.id)
            self.messages = [m for m in self.messages if m.id != paired.id]
        self.message_list.remove_message(msg_id)
        self.messages = [m for m in self.messages if m.id != msg_id]

    def on_delete_requested(self, msg_id: str):
        if self.is_streaming:
            return
        user_msg = self._find_message(msg_id)
        if not user_msg or user_msg.role != "user":
            return
        paired = self._find_paired_assistant(msg_id)
        if paired:
            self.message_list.remove_message(paired.id)
            self.messages = [m for m in self.messages if m.id != paired.id]
        self.message_list.remove_message(msg_id)
        self.messages = [m for m in self.messages if m.id != msg_id]

    def on_retry_requested(self, asst_msg_id: str):
        if self.is_streaming:
            return
        asst_msg = self._find_message(asst_msg_id)
        if not asst_msg or asst_msg.role != "assistant":
            return
        # Find the preceding user message
        user_msg = None
        for i, m in enumerate(self.messages):
            if m.id == asst_msg_id and i > 0 and self.messages[i - 1].role == "user":
                user_msg = self.messages[i - 1]
                break
        if not user_msg:
            return
        # Remove old assistant message
        self.message_list.remove_message(asst_msg_id)
        self.messages = [m for m in self.messages if m.id != asst_msg_id]
        # Create fresh assistant message
        # Create fresh assistant message
        active_model_id = self.model_combo.currentData()
        if not active_model_id: active_model_id = "LMMs Engine"
        display_model = self.model_combo.currentText().strip() or active_model_id
        
        new_asst = ChatMessage(role="assistant", status="generating", model_name=display_model)
        self.messages.append(new_asst)
        self.message_list.add_message(new_asst)
        self.active_message_id = new_asst.id
        self.is_streaming = True
        self._pending_content = ""
        self._pending_thought = ""
        self._has_pending = False
        self.set_send_btn_stop()
        # Re-send original prompt (strip HTML from display_msg)
        plain_prompt = _re.sub(r'<[^>]+>', '', user_msg.content).strip()
        self.chat_service.start_chat(plain_prompt, message_id=new_asst.id, model_name=active_model_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Misc
    # ─────────────────────────────────────────────────────────────────────────
    def on_link_clicked(self, url: str):
        if url.startswith(("http://", "https://")):
            import webbrowser
            webbrowser.open(url)
