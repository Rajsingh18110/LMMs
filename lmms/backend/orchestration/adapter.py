"""
InferenceAdapter: Normalized interface for Engine 1 (Air + Llama.cpp) and Engine 2 (PyTorch).
Handles streaming SSE events, TTFT measurement, tool call detection, and error recovery.
Preserves loaded weights across prompt and tool variations.
"""

import time
import json
import re
import requests
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator, Tuple


@dataclass
class StreamingChunk:
    token: str
    is_first_token: bool = False
    ttft_ms: int = 0
    is_done: bool = False
    error: Optional[str] = None


@dataclass
class InferenceResult:
    full_text: str
    tokens_generated: int
    ttft_ms: int
    inference_duration_ms: int
    tps: float
    detected_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    has_tool_call: bool = False
    raw_response: Optional[Any] = None
    error: Optional[str] = None


class InferenceAdapter:
    """
    Adapter bridging orchestration with Engine 1 (Llama.cpp) and Engine 2 (PyTorch).
    """

    def __init__(self, engine_url: str = "http://localhost:11435"):
        self.engine_url = engine_url

    def stream_inference(
        self,
        model_name: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.5,
        top_p: float = 0.9,
        mode: str = "fast",
        think: bool = False,
        timeout: int = 120
    ) -> Iterator[StreamingChunk]:
        """
        Streams inference from the active engine, yielding StreamingChunks with TTFT timing.
        """
        t0 = time.time()
        first_token_received = False
        ttft_ms = 0

        payload = {
            "model_name": model_name,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "top_p": top_p,
            "repetition_penalty": 1.15,
            "mode": mode.strip("/"),
            "think": think
        }

        try:
            resp = requests.post(
                f"{self.engine_url}/v1/chat/completions",
                json=payload,
                stream=True,
                timeout=(10, timeout)
            )
            resp.raise_for_status()

            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8").strip()
                if not decoded.startswith("data: "):
                    continue
                data_str = decoded[6:]
                if data_str == "[DONE]":
                    yield StreamingChunk(token="", is_done=True, ttft_ms=ttft_ms)
                    break

                try:
                    chunk_obj = json.loads(data_str)
                    token_text = ""
                    if isinstance(chunk_obj, dict):
                        # Format 1: {"message": {"content": "..."}}
                        # Format 2: {"choices": [{"delta": {"content": "..."}}]}
                        if "message" in chunk_obj and "content" in chunk_obj["message"]:
                            token_text = chunk_obj["message"]["content"]
                        elif "choices" in chunk_obj and chunk_obj["choices"]:
                            delta = chunk_obj["choices"][0].get("delta", {})
                            token_text = delta.get("content", "")
                        elif "content" in chunk_obj:
                            token_text = chunk_obj["content"]

                    if token_text:
                        is_first = False
                        if not first_token_received:
                            first_token_received = True
                            is_first = True
                            ttft_ms = int((time.time() - t0) * 1000)

                        yield StreamingChunk(
                            token=token_text,
                            is_first_token=is_first,
                            ttft_ms=ttft_ms,
                            is_done=False
                        )
                except Exception:
                    pass

        except Exception as e:
            yield StreamingChunk(token="", is_done=True, error=str(e), ttft_ms=ttft_ms)

    def extract_tool_calls(self, assistant_text: str) -> List[Dict[str, Any]]:
        """
        Extracts raw tool calls enclosed in <tool_call>...</tool_call> tags.
        Supports both JSON and python dict formatting for robust recovery.
        """
        tool_calls = []
        pattern = r"<tool_call>(.*?)</tool_call>"
        matches = re.findall(pattern, assistant_text, re.DOTALL)

        for raw_match in matches:
            raw = raw_match.strip()
            # Try JSON first
            try:
                data = json.loads(raw)
                if isinstance(data, dict) and "tool" in data:
                    tool_calls.append(data)
                    continue
            except Exception:
                pass

            # Fallback: Python literal eval
            try:
                import ast
                s = re.sub(r'\btrue\b', 'True', raw)
                s = re.sub(r'\bfalse\b', 'False', s)
                s = re.sub(r'\bnull\b', 'None', s)
                data = ast.literal_eval(s)
                if isinstance(data, dict) and "tool" in data:
                    tool_calls.append(data)
            except Exception:
                pass

        return tool_calls
