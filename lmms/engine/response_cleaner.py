import re


_META_PREFIXES = (
    "the user ",
    "the previous response",
    "user asks",
    "user says",
    "according to ",
    "we need",
    "i should",
    "i will",
    "i'll",
    "ill ",
    "now i ",
    "since this is",
    "this is a normal",
    "no tool",
    "tool usage",
    "let me",
)

_META_PHRASES = (
    "system rules",
    "system instruction",
    "identity rules",
    "normal conversational request",
    "tool usage needed",
    "tool usage is needed",
    "tool usage not needed",
    "no tool usage",
    "no tool needed",
    "without introducing myself",
    "respond appropriately",
    "answer naturally",
    "say hello back",
)


def _looks_like_reasoning_sentence(sentence: str) -> bool:
    lowered = sentence.strip().strip("-*` ").lower()
    if not lowered:
        return True
    return lowered.startswith(_META_PREFIXES) or any(phrase in lowered for phrase in _META_PHRASES)


def strip_hidden_reasoning(text: str) -> str:
    """Remove hidden reasoning even when small models forget <think> tags."""
    if not isinstance(text, str):
        return text

    cleaned = text.strip()
    if not cleaned:
        return ""

    if "</think>" in cleaned:
        cleaned = cleaned.rsplit("</think>", 1)[-1].strip()
    cleaned = re.sub(r"<think>.*?(</think>|$)", "", cleaned, flags=re.DOTALL).strip()

    marker_match = None
    for match in re.finditer(r"(?is)(?:^|\n)\s*(?:final answer|answer|response)\s*[:：]\s*", cleaned):
        marker_match = match
    if marker_match and marker_match.end() < len(cleaned):
        cleaned = cleaned[marker_match.end():].strip()

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    drop_count = 0
    for sentence in sentences:
        if _looks_like_reasoning_sentence(sentence):
            drop_count += 1
            continue
        break

    if drop_count:
        remainder = " ".join(sentences[drop_count:]).strip()
        if remainder:
            return remainder
        if _looks_like_reasoning_sentence(cleaned):
            return ""

    return cleaned
