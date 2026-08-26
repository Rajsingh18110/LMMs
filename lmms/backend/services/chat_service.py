"""
chat_service.py

ChatService — QThread that bridges the async Agent Runtime with the Qt GUI.

Responsibilities:
  1. Run the async AgentManager.execute_task() in a dedicated event loop
  2. Parse raw chunk stream into structured ChatEvent objects
  3. Emit ChatEvents via Qt signals so ChatPage can update state cleanly

Chunk parsing rules:
  - <think>...</think>  → ChatEvent(type="reasoning_delta")
  - <system_log>...</system_log> → silently dropped
  - Everything else → ChatEvent(type="assistant_delta")

This ensures the GUI never displays routing logs or agent debug output
as visible reasoning or assistant text.
"""
import re
import asyncio
import sys
from dataclasses import replace as dc_replace
from PyQt6.QtCore import QThread, pyqtSignal

from lmms.backend.agents.core_agents.agents.manager import AgentManager
from lmms.backend.agents.core_agents.agents.context import ExecutionContext
from lmms.backend.tasks.core_tasks.tasks.task import Task
from lmms.backend.services.chat_event import ChatEvent


# Regex patterns for chunk classification
_RE_THINK_OPEN   = re.compile(r'<think>', re.DOTALL)
_RE_THINK_CLOSE  = re.compile(r'</think>', re.DOTALL)
_RE_SYSLOG_FULL  = re.compile(r'<system_log>.*?(</system_log>|$)', re.DOTALL)
_RE_SYSLOG_OPEN  = re.compile(r'<system_log>', re.DOTALL)


class ChatService(QThread):
    # Typed event signal — replaces the old chunk_received(str)
    event_received = pyqtSignal(object)   # ChatEvent

    # Lifecycle signals
    response_finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    cancelled = pyqtSignal()
    no_response = pyqtSignal()

    def __init__(self, agent_manager: AgentManager):
        super().__init__()
        self.agent_manager = agent_manager
        self.prompt: str = ""
        self.image_path: str | None = None
        self.active_message_id: str = ""
        self._is_cancelled = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._main_task = None

    def start_chat(self, prompt: str, message_id: str, image_path: str | None = None, model_name: str | None = None):
        self.prompt = prompt
        self.active_message_id = message_id
        self.image_path = image_path
        self.model_name = model_name
        self._is_cancelled = False
        self.start()

    def cancel(self):
        self._is_cancelled = True
        if self._loop and self._main_task and not self._main_task.done():
            self._loop.call_soon_threadsafe(self._main_task.cancel)

    # ── Thread entry point ────────────────────────────────────────────────────
    def run(self):
        try:
            if sys.platform == "win32":
                self._loop = asyncio.ProactorEventLoop()
            else:
                self._loop = asyncio.SelectorEventLoop()
            asyncio.set_event_loop(self._loop)

            context = ExecutionContext(
                task=Task(
                    id="chat-1",
                    title="User Prompt",
                    description=self.prompt
                ),
                memory=[{"role": "user", "content": self.prompt}],
                selected_model=self.model_name
            )

            visible_deltas = 0

            async def run_async():
                nonlocal visible_deltas
                # Buffer for handling partial think tags across chunk boundaries
                buf = ""
                in_think = False
                in_syslog = False
                has_emitted = False

                try:
                    async for raw_chunk in self.agent_manager.execute_task(context):
                        if self._is_cancelled:
                            break

                        if hasattr(raw_chunk, 'type') and (hasattr(raw_chunk, 'content') or hasattr(raw_chunk, 'reasoning')):
                            # Direct GenerationEvent routing
                            t = raw_chunk.type
                            if t == "thinking_delta": t = "reasoning_delta"
                            if t == "content_delta": t = "assistant_delta"
                            
                            c = raw_chunk.content if t == "assistant_delta" else raw_chunk.reasoning
                            
                            if t in ("reasoning_delta", "assistant_delta"):
                                evt = ChatEvent(
                                    type=t,
                                    message_id=self.active_message_id,
                                    content=c or ""
                                )
                                visible_deltas += 1
                                self.event_received.emit(evt)
                        else:
                            # String legacy buffer logic
                            buf += str(raw_chunk)
                            events, buf, in_think, in_syslog, has_emitted = self._parse_buffer(
                                buf, in_think, in_syslog, has_emitted
                            )
                            for evt in events:
                                if evt.type in ("reasoning_delta", "assistant_delta"):
                                    visible_deltas += 1
                                self.event_received.emit(evt)

                    # Flush remaining buffer
                    if buf.strip():
                        clean = _RE_SYSLOG_FULL.sub("", buf).strip()
                        if clean:
                            evt = ChatEvent(
                                type="reasoning_delta" if in_think else "assistant_delta",
                                message_id=self.active_message_id,
                                content=clean
                            )
                            visible_deltas += 1
                            self.event_received.emit(evt)

                except asyncio.CancelledError:
                    pass

            self._main_task = self._loop.create_task(run_async())
            try:
                self._loop.run_until_complete(self._main_task)
            except asyncio.CancelledError:
                pass
            finally:
                self._loop.close()
                self._loop = None

            if self._is_cancelled:
                self.cancelled.emit()
            elif visible_deltas == 0:
                self.no_response.emit()
            else:
                self.response_finished.emit("done")

        except Exception as e:
            self.error_occurred.emit(str(e))

    # ── Chunk parser ──────────────────────────────────────────────────────────
    def _parse_buffer(
        self, buf: str, in_think: bool, in_syslog: bool, has_emitted: bool
    ) -> tuple[list[ChatEvent], str, bool, bool, bool]:
        """
        Parse `buf` into a list of ChatEvents.
        Returns (events, remaining_buf, in_think, in_syslog, has_emitted).

        Strategy:
          Walk through the buffer character by character looking for tag
          boundaries. When a complete segment is identified, emit it as the
          appropriate event type. Partial tags are left in the buffer for the
          next call.
        """
        events: list[ChatEvent] = []
        mid = self.active_message_id
        pos = 0
        text = buf

        while pos < len(text):
            if in_syslog:
                close = text.find("</system_log>", pos)
                if close == -1:
                    # Incomplete syslog tag — buffer everything from the possible start of the closing tag
                    # Actually, if we are inside a tag, we just buffer everything until we see the close.
                    last_lt = text.rfind("</", pos)
                    if last_lt != -1 and len(text) - last_lt < len("</system_log>"):
                        return events, text[pos:], in_think, in_syslog, has_emitted
                    return events, text[pos:], in_think, in_syslog, has_emitted
                pos = close + len("</system_log>")
                in_syslog = False
                continue

            if in_think:
                close = text.find("</think>", pos)
                if close == -1:
                    # Emit what we are SURE is not part of the closing tag
                    last_lt = text.rfind("</", pos)
                    if last_lt != -1 and len(text) - last_lt < len("</think>"):
                        seg = text[pos:last_lt]
                        if seg:
                            events.append(ChatEvent(
                                type="reasoning_delta",
                                message_id=mid,
                                content=seg
                            ))
                            has_emitted = True
                        return events, text[last_lt:], in_think, in_syslog, has_emitted
                    else:
                        seg = text[pos:]
                        if seg:
                            events.append(ChatEvent(
                                type="reasoning_delta",
                                message_id=mid,
                                content=seg
                            ))
                            has_emitted = True
                        return events, "", in_think, in_syslog, has_emitted
                seg = text[pos:close]
                if seg:
                    events.append(ChatEvent(
                        type="reasoning_delta",
                        message_id=mid,
                        content=seg
                    ))
                    has_emitted = True
                pos = close + len("</think>")
                in_think = False
                continue

            # Normal (assistant) mode — look for next tag
            if not has_emitted and not in_think and not in_syslog:
                # Buffer initial characters to detect implicit reasoning
                if len(text[pos:]) < 40 and not any(c in text[pos:] for c in ".!?\n"):
                    if not text[pos:].lstrip().startswith("<"):
                        return events, text[pos:], in_think, in_syslog, has_emitted
                
                # We have enough to check for implicit reasoning
                from lmms.engine.response_cleaner import _looks_like_reasoning_sentence
                import re
                chunk = text[pos:]
                first_sentence = re.split(r'[\.\!\?\n]', chunk, maxsplit=1)[0]
                if _looks_like_reasoning_sentence(first_sentence):
                    in_think = True
                    continue

            think_pos = text.find("<think>", pos)
            syslog_pos = text.find("<system_log>", pos)
            think_close_pos = text.find("</think>", pos)

            candidates = [p for p in (think_pos, syslog_pos) if p != -1]
            if think_close_pos != -1:
                # If we see a stray </think> before any opening tags, we just strip it
                if not candidates or think_close_pos < min(candidates):
                    # Emit up to stray tag
                    seg = text[pos:think_close_pos]
                    if seg:
                        events.append(ChatEvent(
                            type="assistant_delta",
                            message_id=mid,
                            content=seg
                        ))
                        has_emitted = True
                    pos = think_close_pos + len("</think>")
                    continue

            if not candidates:
                # Check for partial opening tags at the end of the buffer
                last_lt = text.rfind("<", pos)
                if last_lt != -1 and len(text) - last_lt < len("<system_log>"):
                    # Might be a partial tag, emit up to the '<' and buffer the rest
                    seg = text[pos:last_lt]
                    if seg:
                        events.append(ChatEvent(
                            type="assistant_delta",
                            message_id=mid,
                            content=seg
                        ))
                        has_emitted = True
                    return events, text[last_lt:], in_think, in_syslog, has_emitted

                # No tags and no partial tags, emit remainder as assistant delta
                seg = text[pos:]
                if seg:
                    seg = seg.replace("</think>", "")
                    if seg:
                        events.append(ChatEvent(
                            type="assistant_delta",
                            message_id=mid,
                            content=seg
                        ))
                        has_emitted = True
                return events, "", in_think, in_syslog, has_emitted

            next_tag = min(candidates)

            # Emit text before the tag
            seg = text[pos:next_tag]
            if seg:
                seg = seg.replace("</think>", "")
                if seg:
                    events.append(ChatEvent(
                        type="assistant_delta",
                        message_id=mid,
                        content=seg
                    ))
                    has_emitted = True
            pos = next_tag

            if think_pos == next_tag:
                pos += len("<think>")
                in_think = True
            else:
                pos += len("<system_log>")
                in_syslog = True

        return events, "", in_think, in_syslog, has_emitted
