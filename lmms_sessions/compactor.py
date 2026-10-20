"""
lmms_sessions.compactor - Context Compactor with Lossless Guarantees and Local Model Summarization.
Preserves system prompt, pinned items, open tasks, and recent N turns.
Saves pre-compact history to SQLite so messages can always be restored.
"""

from typing import Callable, List, Optional, Tuple

from lmms_sessions.models import CompactionResult, SessionMessage
from lmms_sessions.store import SessionStore


def default_estimate_tokens(text: str) -> int:
    """Fast local token estimation heuristic (~4 characters per token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


class SessionCompactor:
    """
    Manages manual and automatic context compaction.
    Auto-compact triggers at configurable context window threshold (default 80%).
    """

    def __init__(
        self,
        auto_compact_ratio: float = 0.8,
        default_last_n_turns: int = 4,
        context_window: int = 4096,
    ):
        self.auto_compact_ratio = auto_compact_ratio
        self.default_last_n_turns = default_last_n_turns
        self.context_window = context_window

    def should_auto_compact(
        self,
        current_tokens: int,
        context_window: Optional[int] = None,
        ratio: Optional[float] = None,
    ) -> bool:
        """Determines if token count has reached the auto-compaction threshold (default 80%)."""
        limit = context_window or self.context_window
        threshold = ratio if ratio is not None else self.auto_compact_ratio
        return current_tokens >= int(limit * threshold)

    def compact(
        self,
        session_id: str,
        store: SessionStore,
        summarizer: Optional[Callable[[List[SessionMessage]], str]] = None,
        last_n_turns: Optional[int] = None,
    ) -> CompactionResult:
        """
        Compacts the session context:
        - Keeps system prompt
        - Keeps pinned messages
        - Keeps open tasks / plan items
        - Keeps the last N turns
        - Summarizes intermediate dialogue turns
        - Stores snapshot in DB for rollback
        - Fallback: if summarizer fails, leaves message history 100% intact.
        """
        all_messages = store.get_messages(session_id)
        if not all_messages:
            return CompactionResult(
                success=True,
                tokens_before=0,
                tokens_after=0,
                summary="Session has no messages to compact.",
                messages_compacted=0,
            )

        n_turns = last_n_turns if last_n_turns is not None else self.default_last_n_turns
        recent_count = n_turns * 2  # Each turn consists of user + assistant pair

        # Calculate initial token count
        tokens_before = sum(
            m.token_count if m.token_count > 0 else default_estimate_tokens(m.content)
            for m in all_messages
        )

        # Segregate messages into preserved vs compaction candidates
        # 1. System messages (always kept)
        system_messages = [m for m in all_messages if m.role == "system"]
        non_system = [m for m in all_messages if m.role != "system"]

        if len(non_system) <= recent_count:
            # Not enough dialogue turns to require compaction
            return CompactionResult(
                success=True,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                summary="Conversation is within recent turn limit; no compaction needed.",
                messages_compacted=0,
            )

        # 2. Recent turns (always kept at tail)
        recent_messages = non_system[-recent_count:]
        middle_candidates = non_system[:-recent_count]

        # 3. Pinned items and open tasks inside middle candidates (always kept!)
        pinned_messages: List[SessionMessage] = []
        messages_to_summarize: List[SessionMessage] = []

        for m in middle_candidates:
            is_task = bool(m.metadata.get("is_task", False) or m.metadata.get("plan", False))
            if m.pinned or is_task:
                pinned_messages.append(m)
            else:
                messages_to_summarize.append(m)

        if not messages_to_summarize:
            return CompactionResult(
                success=True,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                summary="All historical messages are pinned or system prompts; nothing to compact.",
                messages_compacted=0,
            )

        # 4. Generate summary using provided summarizer or fallback
        summary_text = ""
        try:
            if summarizer is not None:
                summary_text = summarizer(messages_to_summarize)
            else:
                # Default structured heuristic summary
                topics = []
                for m in messages_to_summarize:
                    prefix = f"[{m.role.upper()}]: "
                    first_line = m.content.strip().splitlines()[0] if m.content.strip() else ""
                    if first_line:
                        topics.append(f"{prefix}{first_line[:120]}")
                summary_text = (
                    "Summary of previous discussion:\n"
                    + "\n".join(f"- {t}" for t in topics[:15])
                )

            if not summary_text or not summary_text.strip():
                raise ValueError("Summarizer returned empty summary.")

        except Exception as e:
            # CRITICAL LOSSLESS GUARANTEE:
            # If summarization fails, NEVER lose messages. Keep original history intact!
            return CompactionResult(
                success=False,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                summary="",
                messages_compacted=0,
                error=f"Compaction aborted to prevent message loss: {e}",
            )

        # 5. Save pre-compact snapshot in DB
        store.save_compaction(
            session_id=session_id,
            tokens_before=tokens_before,
            tokens_after=0,  # Updated after building new set
            summary=summary_text,
            pre_compact_messages=all_messages,
        )

        # 6. Build new message list
        summary_msg_content = f"[Context Compaction Summary of previous {len(messages_to_summarize)} turns]:\n{summary_text.strip()}"
        summary_tokens = default_estimate_tokens(summary_msg_content)

        # Assemble new message payload
        new_payload: List[dict] = []

        # 1. System messages
        for sys_msg in system_messages:
            new_payload.append({
                "role": sys_msg.role,
                "content": sys_msg.content,
                "pinned": sys_msg.pinned,
                "token_count": sys_msg.token_count,
                "created_at": sys_msg.created_at,
                "metadata": sys_msg.metadata,
            })

        # 2. Compacted summary message
        new_payload.append({
            "role": "assistant",
            "content": summary_msg_content,
            "pinned": False,
            "token_count": summary_tokens,
            "created_at": None,
            "metadata": {"is_compaction_summary": True},
        })

        # 3. Pinned items from historical middle
        for pin_msg in pinned_messages:
            new_payload.append({
                "role": pin_msg.role,
                "content": pin_msg.content,
                "pinned": pin_msg.pinned,
                "token_count": pin_msg.token_count,
                "created_at": pin_msg.created_at,
                "metadata": pin_msg.metadata,
            })


        # 4. Recent turns
        for rec_msg in recent_messages:
            new_payload.append({
                "role": rec_msg.role,
                "content": rec_msg.content,
                "pinned": rec_msg.pinned,
                "token_count": rec_msg.token_count,
                "created_at": rec_msg.created_at,
                "metadata": rec_msg.metadata,
            })

        # Reconstruct in DB atomically in one transaction
        store.replace_messages(session_id, new_payload)


        new_messages = store.get_messages(session_id)
        tokens_after = sum(
            m.token_count if m.token_count > 0 else default_estimate_tokens(m.content)
            for m in new_messages
        )

        return CompactionResult(
            success=True,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            summary=summary_text,
            messages_compacted=len(messages_to_summarize),
        )
