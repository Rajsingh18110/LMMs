"""
ContextCompactor: Intelligent conversation history and tool observation compaction.
Preserves recent conversational continuity, decisions, constraints, and pending tool state.
Compacts older observations and history only when budget pressure demands it.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import re


@dataclass
class CompactionReport:
    original_turns: int
    compacted_turns: int
    observations_pruned: int
    tokens_saved_estimate: int
    summary_applied: bool = False


class ContextCompactor:
    """
    Budget-driven context compactor.
    Prunes stale tool observations and condenses older conversation turns.
    """

    def __init__(
        self,
        recent_turns_to_preserve: int = 8,
        max_observation_chars: int = 4000,
        token_count_fn: Optional[Any] = None
    ):
        self.recent_turns_to_preserve = recent_turns_to_preserve
        self.max_observation_chars = max_observation_chars
        self.token_count_fn = token_count_fn

    def compact(
        self,
        messages: List[Dict[str, Any]],
        usable_budget: int,
        current_prompt_tokens: int,
        model_name: str = "default"
    ) -> Tuple[List[Dict[str, Any]], CompactionReport]:
        """
        Executes multi-stage compaction if current_prompt_tokens exceeds usable_budget.
        Stage 1: Truncate oversized <observation> blocks from older turns.
        Stage 2: Condense older tool observations while keeping conversational flow intact.
        Stage 3: Summarize oldest turns into an executive summary bullet list.
        """
        original_turns = len(messages)
        obs_pruned = 0
        tokens_saved = 0

        # If already fits comfortably in budget, do nothing!
        if current_prompt_tokens <= usable_budget:
            return list(messages), CompactionReport(
                original_turns=original_turns,
                compacted_turns=original_turns,
                observations_pruned=0,
                tokens_saved_estimate=0,
                summary_applied=False
            )

        compacted = [dict(m) for m in messages]

        # Stage 1: Compact bulky <observation> blocks from history turns
        # In budget overflow, inspect any prior turn with an oversized observation
        effective_max_obs = min(self.max_observation_chars, max(800, int(usable_budget * 1.5)))
        for idx in range(1, len(compacted) - 1):
            content = compacted[idx].get("content")
            if isinstance(content, str) and "<observation>" in content:
                if len(content) > effective_max_obs:
                    before_len = len(content)
                    compacted[idx]["content"] = self._compact_observation(content, max_chars=effective_max_obs)
                    obs_pruned += 1
                    tokens_saved += max(0, (before_len - len(compacted[idx]["content"])) // 3)

        current_tokens = self._estimate_tokens(compacted, model_name)
        if current_tokens <= usable_budget:
            return compacted, CompactionReport(
                original_turns=original_turns,
                compacted_turns=len(compacted),
                observations_pruned=obs_pruned,
                tokens_saved_estimate=tokens_saved,
                summary_applied=False
            )

        # Stage 2: Condense older observation turns instead of deleting conversation turns
        cutoff_index = max(1, len(compacted) - self.recent_turns_to_preserve)
        for idx in range(1, cutoff_index):
            msg = compacted[idx]
            if msg.get("role") in ("user", "tool") and "<observation>" in str(msg.get("content", "")):
                summary_note = self._extract_summary_line(str(msg.get("content", "")))
                compacted[idx]["content"] = f"<observation>\n[Past Step Output: {summary_note}]\n</observation>"
                obs_pruned += 1
                tokens_saved += 120

        current_tokens = self._estimate_tokens(compacted, model_name)
        if current_tokens <= usable_budget:
            return compacted, CompactionReport(
                original_turns=original_turns,
                compacted_turns=len(compacted),
                observations_pruned=obs_pruned,
                tokens_saved_estimate=tokens_saved,
                summary_applied=False
            )

        summary_applied = False
        # Stage 3: Condense oldest turns into an explicit summary message
        # Trigger when still overflowing and there are conversation turns to summarize
        current_tokens = self._estimate_tokens(compacted, model_name)
        if current_tokens > usable_budget and len(compacted) >= 3:
            system_msg = compacted[0] if compacted and compacted[0].get("role") == "system" else None
            start_idx = 1 if system_msg else 0

            # Scale preserved turns by budget pressure
            if usable_budget < 250:
                recent_to_keep = min(2, max(1, len(compacted) - start_idx - 1))
            else:
                recent_to_keep = min(self.recent_turns_to_preserve, max(2, len(compacted) - start_idx - 2))

            end_idx = len(compacted) - recent_to_keep
            if end_idx > start_idx:
                turns_to_summarize = compacted[start_idx:end_idx]
                summary_text = self._build_turn_summary(turns_to_summarize)

                new_messages = []
                if system_msg:
                    new_messages.append(system_msg)

                new_messages.append({
                    "role": "user",
                    "content": f"[Previous Conversation Context Summary]\n{summary_text}\n[End of Context Summary]"
                })
                new_messages.append({
                    "role": "assistant",
                    "content": "Understood. I have recorded the previous conversation context and task history."
                })
                new_messages.extend(compacted[end_idx:])

                before_summary_tokens = current_tokens
                current_tokens = self._estimate_tokens(new_messages, model_name)
                tokens_saved += max(100, before_summary_tokens - current_tokens)
                summary_applied = True
                compacted = new_messages

                if current_tokens <= usable_budget:
                    return new_messages, CompactionReport(
                        original_turns=original_turns,
                        compacted_turns=len(new_messages),
                        observations_pruned=obs_pruned,
                        tokens_saved_estimate=tokens_saved,
                        summary_applied=True
                    )

        # Stage 4: Aggressive truncation of oversized history messages if still overflowing
        current_tokens = self._estimate_tokens(compacted, model_name)
        if current_tokens > usable_budget and len(compacted) > 2:
            excess_tokens = current_tokens - usable_budget + 100
            chars_to_cut = excess_tokens * 4
            for idx in range(1, len(compacted) - 1):
                msg_content = str(compacted[idx].get("content", ""))
                if len(msg_content) > 1000:
                    cut = min(chars_to_cut, len(msg_content) - 500)
                    if cut > 0:
                        compacted[idx]["content"] = (
                            msg_content[:500]
                            + f"\n... [Truncated {cut} characters to prevent context overflow] ...\n"
                            + msg_content[-200:]
                        )
                        chars_to_cut -= cut
                        tokens_saved += cut // 3
                        if chars_to_cut <= 0:
                            break

        return compacted, CompactionReport(
            original_turns=original_turns,
            compacted_turns=len(compacted),
            observations_pruned=obs_pruned,
            tokens_saved_estimate=tokens_saved,
            summary_applied=summary_applied
        )

    def _compact_observation(self, observation_str: str, max_chars: Optional[int] = None) -> str:
        """
        Extracts head and tail of an observation to preserve critical status and return values.
        """
        limit = max_chars if max_chars is not None else self.max_observation_chars
        match = re.search(r"<observation>(.*?)</observation>", observation_str, re.DOTALL)
        body = match.group(1).strip() if match else observation_str

        head_len = int(limit * 0.7)
        tail_len = int(limit * 0.3)

        if len(body) <= limit:
            return observation_str

        condensed_body = (
            body[:head_len]
            + f"\n... [Truncated {len(body) - head_len - tail_len} characters to preserve memory] ...\n"
            + body[-tail_len:]
        )
        return f"<observation>\n{condensed_body}\n</observation>"

    def _extract_summary_line(self, observation_str: str) -> str:
        """Extracts first 120 characters or key status from an observation."""
        clean = re.sub(r"<.*?>", "", observation_str).strip()
        lines = [line.strip() for line in clean.splitlines() if line.strip()]
        if lines:
            return lines[0][:150]
        return "Tool completed."

    def _build_turn_summary(self, turns: List[Dict[str, Any]]) -> str:
        """Constructs a deterministic executive summary preserving key facts (paths, URLs, values, decisions)."""
        summary_bullets = []
        for t in turns:
            role = t.get("role", "unknown")
            content = str(t.get("content", "")).strip()

            # Extract key facts to preserve across compaction
            paths = re.findall(r"(?:/[\w.-]+)+\.[a-zA-Z0-9]+|\b\w+\.(?:py|json|md|txt|html|js|ts|cpp|h|sh|log)\b", content)
            urls = re.findall(r"https?://[^\s)\]'\"]+", content)
            identifiers = re.findall(r"\b(?:port\s+\d+|pid\s+\d+|\d+\.\d+(?:gb|mb|s|ms)?|cve-\d{4}-\d+|#\d+|\b\d{4,5}\b)\b", content, re.IGNORECASE)
            
            decisions = []
            for dec_kw in ["decided", "agreed", "must not", "always use", "never", "selected", "chose", "confirmed", "require"]:
                if dec_kw in content.lower():
                    sentences = re.split(r"[.!?\n]", content)
                    for s in sentences:
                        if dec_kw in s.lower() and len(s.strip()) > 5:
                            decisions.append(s.strip()[:100])
                            break

            facts = []
            if paths:
                facts.append(f"files: {', '.join(sorted(set(paths))[:4])}")
            if urls:
                facts.append(f"urls: {', '.join(sorted(set(urls))[:2])}")
            if identifiers:
                facts.append(f"values: {', '.join(sorted(set(identifiers))[:3])}")
            if decisions:
                facts.append(f"decision: '{decisions[0]}'")

            snippet = content.replace("\n", " ")[:120]
            if facts:
                bullet = f"- {role.capitalize()}: {snippet} [{'; '.join(facts)}]"
            else:
                bullet = f"- {role.capitalize()}: {snippet}"
            summary_bullets.append(bullet)

        return "\n".join(summary_bullets[:12])

    def _estimate_tokens(self, messages: List[Dict[str, Any]], model_name: str) -> int:
        if self.token_count_fn:
            total = 0
            for m in messages:
                content = str(m.get("content", ""))
                total += self.token_count_fn(content, model_name)
            return total
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        return int(total_chars / 3.2) + 1
