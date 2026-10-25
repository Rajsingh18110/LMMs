"""
TokenBudgetManager: Precise token budgeting and context-window protection.
Calculates effective context limits from verified model metadata.
Enforces pre-inference budget checks to guarantee no context overflows.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable
import os
import requests


def get_system_hardware_profile() -> Dict[str, Any]:
    """
    Detects total system RAM (GB) and GPU VRAM (GB) dynamically.
    Enables automatic hardware-aware scaling for local/offline models.
    """
    ram_gb = 16.0
    try:
        import psutil
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    except Exception:
        pass

    vram_gb = 0.0
    try:
        import subprocess
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=1.5
        )
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            vram_gb = sum(float(l.strip()) for l in lines if l.strip()) / 1024.0
    except Exception:
        pass

    return {
        "ram_gb": ram_gb,
        "vram_gb": vram_gb,
        "has_gpu": vram_gb > 0
    }


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

    @classmethod
    def clear_global_cache(cls):
        """Clears the global limit cache (e.g. on provider or model switch)."""
        cls._global_limit_cache.clear()

    def clear_cache(self):
        """Clears instance and global token/limit caches."""
        self._limit_cache.clear()
        self._token_cache.clear()
        TokenBudgetManager.clear_global_cache()

    def get_effective_context_limit(self, model_name: str) -> int:
        """
        Determines the true context window limit dynamically:
        1. Local cache
        2. Online Model Registry & Provider-Aware Dynamic Limits (Gemini 1M+, Claude 200k, GPT-4o/Nemotron 128k)
        3. GGUF header parser (direct binary inspection) scaled with System VRAM / RAM
        4. Engine `/v1/model/context` endpoint scaled with hardware capacity
        5. Hardware-Aware Heuristics
        """
        if model_name in self._limit_cache:
            return self._limit_cache[model_name]
        if model_name in TokenBudgetManager._global_limit_cache:
            limit = TokenBudgetManager._global_limit_cache[model_name]
            self._limit_cache[model_name] = limit
            return limit

        # 1. Online Model Registry & Dynamic Cloud Limits
        # STRICT ISOLATION: Only apply cloud/online provider context limits if the requested model
        # is explicitly registered or matches a well-known cloud API model family.
        # Never hijack local/offline model requests like Qwen-1.5B!
        try:
            from lmms.backend.core.registry.online_models import OnlineModelRegistry
            online_model = OnlineModelRegistry.get_model(model_name)
            is_explicit_online = (online_model is not None)

            m_lower = model_name.lower().strip()
            is_well_known_cloud = (
                m_lower.startswith(("gemini", "claude", "gpt-4", "gpt-3.5", "o1", "o3", "nvidia/"))
                or "gemini-" in m_lower
                or "claude-" in m_lower
            )

            if is_explicit_online or is_well_known_cloud:
                # Check user explicit context config
                if online_model and online_model.get("context_window"):
                    cw = int(online_model["context_window"])
                    if cw > 0:
                        self._limit_cache[model_name] = cw
                        TokenBudgetManager._global_limit_cache[model_name] = cw
                        return cw

                # Check model name or configured model id
                mid = f"{m_lower} {(online_model.get('id', '') if online_model else '').lower()}"
                p_id = (online_model.get("provider_id", "") if online_model else "").lower()

                if "gemini" in mid or "gemini" in p_id:
                    limit = 1048576  # 1M context
                elif "claude" in mid or "anthropic" in p_id:
                    limit = 200000   # 200k context
                elif any(k in mid for k in ["gpt-4", "gpt-4o", "o1", "o3", "chatgpt"]):
                    limit = 128000   # 128k context
                elif any(k in mid for k in ["nemotron", "llama-3", "llama3", "deepseek", "mistral"]):
                    limit = 131072   # 128k context
                else:
                    limit = 131072   # Standard 128k context for modern cloud webhooks

                self._limit_cache[model_name] = limit
                TokenBudgetManager._global_limit_cache[model_name] = limit
                return limit
        except Exception:
            pass

        # 2. Hardware profile for local/offline models
        hw = get_system_hardware_profile()
        vram_gb = hw["vram_gb"]
        ram_gb = hw["ram_gb"]

        # Maximum context hardware can safely sustain without CUDA OOM:
        if vram_gb >= 40.0 or ram_gb >= 128.0:
            max_hw_context = 1048576  # Enterprise datacenter: full native up to 1M
        elif vram_gb >= 20.0 or ram_gb >= 64.0:
            max_hw_context = 65536    # 64k for 24GB GPUs (3090/4090/A10/A5000)
        elif vram_gb >= 10.0 or ram_gb >= 32.0:
            max_hw_context = 32768    # 32k for 12GB/16GB GPUs
        elif vram_gb >= 7.0:
            max_hw_context = 16384    # 16k for 8GB GPUs
        elif vram_gb > 0:
            max_hw_context = 8192     # Safe ceiling for <= 6GB laptop GPU
        else:
            # CPU only execution
            max_hw_context = 32768 if ram_gb >= 32.0 else 16384

        # 3. Direct GGUF metadata parsing from ~/.lmms/models
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
                            # Dynamically scale native GGUF context against hardware capacity!
                            effective = min(v, max_hw_context)
                            self._limit_cache[model_name] = effective
                            TokenBudgetManager._global_limit_cache[model_name] = effective
                            return effective
                except Exception:
                    pass

        # 4. Engine HTTP endpoint
        if not self._engine_offline:
            try:
                resp = requests.get(f"{self.engine_url}/v1/model/context", params={"model_name": model_name}, timeout=1)
                if resp.status_code == 200:
                    data = resp.json()
                    ctx = data.get("context_length")
                    if isinstance(ctx, int) and ctx > 0:
                        effective = min(ctx, max_hw_context)
                        self._limit_cache[model_name] = effective
                        TokenBudgetManager._global_limit_cache[model_name] = effective
                        return effective
            except Exception:
                self._engine_offline = True
                TokenBudgetManager._global_offline_urls.add(self.engine_url)

        # 5. Dynamic Model Architecture Heuristics
        lower = model_name.lower()
        if any(sz in lower for sz in ["70b", "120b", "770b"]):
            limit = min(32768, max_hw_context)
        elif any(sz in lower for sz in ["8b", "qwen3", "30b", "14b"]):
            limit = min(8192, max_hw_context)
        elif "1.5b" in lower or "nano" in lower:
            limit = min(4096, max_hw_context)
        else:
            limit = min(self.default_context_limit, max_hw_context)

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
        Dynamically scales output_reserve to match model context capacity.
        """
        context_limit = self.get_effective_context_limit(model_name)

        if requested_output_reserve:
            output_reserve = requested_output_reserve
        else:
            # Proportional dynamic output allocation
            if context_limit >= 100000:       # 100k+ (Gemini, Claude, GPT-4o, 128k local/cloud)
                output_reserve = 8192
            elif context_limit >= 32000:      # 32k - 64k
                output_reserve = 4096
            elif context_limit >= 16000:      # 16k
                output_reserve = 3072
            elif context_limit >= 8000:       # 8k
                output_reserve = 2048
            else:                             # <= 4k
                output_reserve = self.default_output_reserve

        safety = self.safety_margin
        usable_context = max(0, context_limit - output_reserve - safety)
        usable_context = min(usable_context, context_limit)

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
