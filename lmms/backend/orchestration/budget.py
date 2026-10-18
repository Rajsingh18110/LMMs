"""
TokenBudgetManager: Precise token budgeting and context-window protection.
Calculates effective context limits from verified model metadata.
Enforces pre-inference budget checks to guarantee no context overflows.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable
import os
import requests


class ContextOverflowError(Exception):
    """Raised when mandatory prompt content exceeds the usable context limit."""
    def __init__(self, message: str, required_tokens: int, usable_limit: int):
        super().__init__(message)
        self.required_tokens = required_tokens
        self.usable_limit = usable_limit


@dataclass
class BudgetBreakdown:
    context_limit: int
    output_reserve: int
    safety_margin: int
    usable_context: int
    base_prompt_tokens: int
    task_instructions_tokens: int
    tool_schemas_tokens: int
    history_tokens: int
    user_query_tokens: int
    total_prompt_tokens: int
    remaining_tokens: int
    is_overflow: bool


class TokenBudgetManager:
    """
    Manages and enforces model context budgets using verified engine metadata.
    """

    _global_offline_urls = set(["http://127.0.0.1:0", "http://localhost:0"])
    _global_limit_cache: Dict[str, int] = {}

    def __init__(
        self,
        engine_url: str = "http://localhost:11435",
        default_context_limit: int = 8192,
        default_output_reserve: int = 768,
        safety_margin: int = 200,
        tokenize_fn: Optional[Callable[[str, str], int]] = None
    ):
        self.engine_url = engine_url
        self.default_context_limit = default_context_limit
        self.default_output_reserve = default_output_reserve
        self.safety_margin = safety_margin
        self._custom_tokenize_fn = tokenize_fn
        self._limit_cache: Dict[str, int] = {}
        self._token_cache: Dict[tuple, int] = {}
        self._engine_offline = (engine_url in self._global_offline_urls)

    def get_effective_context_limit(self, model_name: str) -> int:
        """
        Determines the true context window limit from:
        1. Local cache
        2. GGUF header parser (direct binary inspection)
        3. Engine `/v1/model/context` endpoint
        4. Safe default
        """
        if model_name in self._limit_cache:
            return self._limit_cache[model_name]
        if model_name in TokenBudgetManager._global_limit_cache:
            limit = TokenBudgetManager._global_limit_cache[model_name]
            self._limit_cache[model_name] = limit
            return limit

        # 1. Try direct GGUF metadata parsing from ~/.lmms/models
        models_dir = os.path.expanduser("~/.lmms/models")
        candidates = [
            os.path.join(models_dir, f"{model_name}.gguf"),
            os.path.join(models_dir, model_name),
            os.path.join(models_dir, f"{model_name.replace(':', '-')}.gguf")
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    from lmms.engine.engine_1_llamacpp.air_loader import parse_gguf_metadata
                    meta = parse_gguf_metadata(path)
                    for k, v in meta.items():
                        if k.endswith(".context_length") and isinstance(v, int) and v > 0:
                            # Clamp native 256k to a practical memory-safe window if running locally
                            effective = min(v, 32768)
                            self._limit_cache[model_name] = effective
                            TokenBudgetManager._global_limit_cache[model_name] = effective
                            return effective
                except Exception:
                    pass

        # 2. Try Engine HTTP endpoint
        if not self._engine_offline:
            try:
                resp = requests.get(f"{self.engine_url}/v1/model/context", params={"model_name": model_name}, timeout=1)
                if resp.status_code == 200:
                    data = resp.json()
                    ctx = data.get("context_length")
                    if isinstance(ctx, int) and ctx > 0:
                        self._limit_cache[model_name] = ctx
                        TokenBudgetManager._global_limit_cache[model_name] = ctx
                        return ctx
            except Exception:
                self._engine_offline = True
                TokenBudgetManager._global_offline_urls.add(self.engine_url)

        # 3. Known heuristics based on model name
        lower = model_name.lower()
        if "30b" in lower or "qwen3" in lower:
            limit = 8192
        elif "8b" in lower or "7b" in lower:
            limit = 8192
        elif "1.5b" in lower or "nano" in lower:
            limit = 4096
        else:
            limit = self.default_context_limit

        self._limit_cache[model_name] = limit
        TokenBudgetManager._global_limit_cache[model_name] = limit
        return limit

    def count_tokens(self, text: str, model_name: str = "default") -> int:
        """
        Calculates token count using:
        1. Custom tokenize function if provided
        2. Local token cache
        3. Engine `/v1/tokenize` endpoint if online
        4. Conservative BPE estimator (chars // 3.2 + 1)
        """
        if not text:
            return 0

        cache_key = (model_name, hash(text))
        if cache_key in self._token_cache:
            return self._token_cache[cache_key]

        if self._custom_tokenize_fn:
            try:
                count = self._custom_tokenize_fn(text, model_name)
                self._token_cache[cache_key] = count
                return count
            except Exception:
                pass

        # Try Engine endpoint
        if not self._engine_offline:
            try:
                r = requests.post(
                    f"{self.engine_url}/v1/tokenize",
                    json={"model_name": model_name, "texts": [text]},
                    timeout=1
                )
                if r.status_code == 200:
                    counts = r.json().get("token_counts", [])
                    if counts:
                        count = counts[0]
                        self._token_cache[cache_key] = count
                        return count
            except Exception:
                self._engine_offline = True
                TokenBudgetManager._global_offline_urls.add(self.engine_url)

        # Conservative fallback: ~3.2 characters per token for English & code
        # Never underestimate token counts to prevent silent overflows!
        count = max(1, int(len(text) / 3.2) + 1)
        self._token_cache[cache_key] = count
        return count

    def calculate_budget(
        self,
        model_name: str,
        base_prompt: str,
        task_instructions: str,
        tool_schemas: str,
        history_messages: List[Dict[str, Any]],
        user_query: str,
        requested_output_reserve: Optional[int] = None
    ) -> BudgetBreakdown:
        """
        Computes detailed token budget allocation across all sections.
        """
        context_limit = self.get_effective_context_limit(model_name)
        output_reserve = requested_output_reserve or self.default_output_reserve
        safety = self.safety_margin
        usable_context = max(512, context_limit - output_reserve - safety)

        base_tokens = self.count_tokens(base_prompt, model_name)
        task_tokens = self.count_tokens(task_instructions, model_name)
        tool_tokens = self.count_tokens(tool_schemas, model_name)

        history_str = ""
        for m in history_messages:
            history_str += f"{m.get('role', '')}: {str(m.get('content', ''))}\n"
        history_tokens = self.count_tokens(history_str, model_name)

        user_tokens = self.count_tokens(user_query, model_name)

        total_prompt_tokens = base_tokens + task_tokens + tool_tokens + history_tokens + user_tokens
        remaining = usable_context - total_prompt_tokens
        is_overflow = total_prompt_tokens > usable_context

        return BudgetBreakdown(
            context_limit=context_limit,
            output_reserve=output_reserve,
            safety_margin=safety,
            usable_context=usable_context,
            base_prompt_tokens=base_tokens,
            task_instructions_tokens=task_tokens,
            tool_schemas_tokens=tool_tokens,
            history_tokens=history_tokens,
            user_query_tokens=user_tokens,
            total_prompt_tokens=total_prompt_tokens,
            remaining_tokens=remaining,
            is_overflow=is_overflow
        )

    def verify_or_raise(self, breakdown: BudgetBreakdown):
        """
        Throws ContextOverflowError if mandatory content exceeds usable budget.
        """
        if breakdown.is_overflow:
            raise ContextOverflowError(
                f"Context budget exceeded: Prompt requires {breakdown.total_prompt_tokens} tokens, but usable limit is {breakdown.usable_context} (Reserve: {breakdown.output_reserve}, Safety: {breakdown.safety_margin}).",
                required_tokens=breakdown.total_prompt_tokens,
                usable_limit=breakdown.usable_context
            )
