# Copyright 2026 LMMs Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Unified Online Model Client.
Dispatches streaming chat completions to online providers (Anthropic, OpenAI,
Gemini, DeepSeek, Groq, Sarvam AI, Krutrim, and Custom Webhooks).
Emits standard SSE lines (data: {...}) matching LMMs engine streaming contract.
"""

from __future__ import annotations

import json
import re
import time
from typing import Dict, List, Any, Generator, Optional
import requests

from lmms.backend.core.registry.online_models import OnlineModelRegistry


class OnlineModelClient:
    """Dispatches completions to cloud LLM providers and custom webhook endpoints."""

    @staticmethod
    def sanitize_api_key(raw_key: str) -> str:
        """Sanitizes API keys, removing newlines, quotes, or accidental env-variable prefixes."""
        if not raw_key:
            return ""
        raw = str(raw_key).strip()

        # Check for multi-line or single-line env variable assignment (e.g. MODEL_API_KEY=nvapi-... or API_KEY="sk-...")
        match = re.search(r'(?:API_KEY|TOKEN|SECRET|KEY)\s*[:=]\s*["\']?([^\s"\']+)["\']?', raw, re.IGNORECASE)
        if match:
            return match.group(1).replace("\r", "").replace("\n", "").strip()

        # Check for known API key signatures in multi-line paste
        for line in raw.splitlines():
            line_str = line.strip()
            m = re.search(r'(?:nvapi-[A-Za-z0-9_-]+|sk-[A-Za-z0-9_-]+|AIza[A-Za-z0-9_-]+|gsk_[A-Za-z0-9_-]+)', line_str)
            if m:
                return m.group(0)

        # Remove newlines, returns, leading/trailing whitespace, and enclosing quotes
        clean = raw.replace("\r", "").replace("\n", "").strip().strip("\"'")
        return clean

    @staticmethod
    def _sanitize_headers(headers: Dict[str, Any]) -> Dict[str, str]:
        """Cleanses all header keys and values to strictly comply with HTTP RFC specifications."""
        clean = {}
        for k, v in headers.items():
            if not k:
                continue
            clean_k = str(k).replace("\r", "").replace("\n", "").strip()
            clean_v = str(v).replace("\r", "").replace("\n", "").strip()
            clean[clean_k] = clean_v
        return clean

    @staticmethod
    def stream_chat(
        model_name: str,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = 0.7,
        top_p: Optional[float] = 0.95,
        max_tokens: Optional[int] = 4096,
        mode: Optional[str] = "deep",
        think: Optional[bool] = True,
        timeout: int = 120
    ) -> Generator[bytes, None, None]:
        """
        Streams completions from the online provider.
        Yields bytes in standard SSE chunks: b'data: {"choices":[{"delta":{"content":"..."}}]}\n\n'
        """
        model_info = OnlineModelRegistry.get_model(model_name)
        if not model_info:
            err = f"Online model '{model_name}' not found in registry."
            yield f'data: {{"error": "{err}"}}\n\n'.encode("utf-8")
            yield b"data: [DONE]\n\n"
            return

        p_type = model_info.get("type", "openai_compatible")
        base_url = model_info.get("base_url", "").rstrip("/")
        api_key = model_info.get("api_key", "")
        model_id = model_info.get("id", model_name)
        custom_headers = model_info.get("custom_headers", {})

        if p_type == "anthropic":
            yield from OnlineModelClient._stream_anthropic(
                base_url=base_url or "https://api.anthropic.com/v1",
                api_key=api_key,
                model_id=model_id,
                messages=messages,
                temperature=temperature or 0.7,
                max_tokens=max_tokens or 4096,
                custom_headers=custom_headers,
                timeout=timeout
            )
        elif p_type == "gemini" and "generativelanguage.googleapis.com" in base_url and not base_url.endswith("/openai"):
            yield from OnlineModelClient._stream_gemini_native(
                base_url=base_url,
                api_key=api_key,
                model_id=model_id,
                messages=messages,
                temperature=temperature or 0.7,
                max_tokens=max_tokens or 4096,
                timeout=timeout
            )
        else:
            # Standard OpenAI-compatible (OpenAI, DeepSeek, Groq, Mistral, Sarvam AI, Krutrim, Custom Webhook)
            yield from OnlineModelClient._stream_openai_compatible(
                base_url=base_url,
                api_key=api_key,
                model_id=model_id,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                custom_headers=custom_headers,
                timeout=timeout
            )

    @staticmethod
    def _stream_openai_compatible(
        base_url: str,
        api_key: str,
        model_id: str,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = 0.7,
        top_p: Optional[float] = 0.95,
        max_tokens: Optional[int] = 4096,
        custom_headers: Optional[Dict[str, str]] = None,
        timeout: int = 120
    ) -> Generator[bytes, None, None]:
        # Auto-correct NVIDIA model name prefix if pointing to integrate.api.nvidia.com
        if "integrate.api.nvidia.com" in base_url and not model_id.startswith("nvidia/") and not model_id.startswith("meta/") and not model_id.startswith("mistralai/"):
            model_id = f"nvidia/{model_id}"

        endpoint = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
        if not base_url.endswith("/v1") and not base_url.endswith("/chat/completions"):
            endpoint = f"{base_url}/v1/chat/completions"

        headers = {"Content-Type": "application/json"}
        clean_key = OnlineModelClient.sanitize_api_key(api_key)
        if clean_key:
            headers["Authorization"] = f"Bearer {clean_key}"
        if custom_headers and isinstance(custom_headers, dict):
            headers.update(custom_headers)
        headers = OnlineModelClient._sanitize_headers(headers)

        # Normalize messages (ensure content is string)
        clean_messages = []
        for m in messages:
            content = m.get("content", "")
            if not isinstance(content, str):
                content = str(content)
            clean_messages.append({"role": m.get("role", "user"), "content": content})

        payload = {
            "model": model_id,
            "messages": clean_messages,
            "stream": True,
            "temperature": temperature if temperature is not None else 0.7,
        }
        if top_p is not None:
            payload["top_p"] = top_p
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        req_timeout = timeout if timeout and timeout > 120 else 180
        try:
            with requests.post(endpoint, json=payload, headers=headers, stream=True, timeout=(20, req_timeout)) as resp:
                if resp.status_code != 200:
                    err_msg = resp.text[:300]
                    yield f'data: {{"error": "HTTP {resp.status_code}: {err_msg}"}}\n\n'.encode("utf-8")
                    yield b"data: [DONE]\n\n"
                    return

                for line in resp.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode("utf-8") if isinstance(line, bytes) else str(line)
                    if line_str.startswith("data: "):
                        payload_str = line_str[6:].strip()
                        if payload_str == "[DONE]":
                            yield b"data: [DONE]\n\n"
                            break
                        try:
                            d = json.loads(payload_str)
                            delta = d.get("choices", [{}])[0].get("delta", {}) if d.get("choices") else {}
                            content = delta.get("content")
                            reasoning = delta.get("reasoning_content")
                            
                            text_to_emit = ""
                            delta_obj = {}
                            if reasoning:
                                delta_obj["reasoning_content"] = reasoning
                                # Keep internal reasoning isolated so it never leaks into user chat
                                text_to_emit = ""
                            if content:
                                delta_obj["content"] = content
                                text_to_emit = content
                            elif not reasoning and not content and "content" in d:
                                text_to_emit = d.get("content", "")
                                delta_obj["content"] = text_to_emit

                            # Yield dual-compatible SSE chunk (only emit when there is real user-facing content)
                            if text_to_emit:
                                norm_chunk = {
                                    "content": text_to_emit,
                                    "choices": [{"delta": {"content": text_to_emit}}]
                                }
                                yield f"data: {json.dumps(norm_chunk)}\n\n".encode("utf-8")
                        except Exception:
                            yield line + b"\n"
                    else:
                        yield line + b"\n"
        except Exception as e:
            yield f'data: {{"error": "{str(e)}"}}\n\n'.encode("utf-8")
            yield b"data: [DONE]\n\n"

    @staticmethod
    def _stream_anthropic(
        base_url: str,
        api_key: str,
        model_id: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        custom_headers: Optional[Dict[str, str]] = None,
        timeout: int = 120
    ) -> Generator[bytes, None, None]:
        endpoint = f"{base_url.rstrip('/')}/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        if custom_headers and isinstance(custom_headers, dict):
            headers.update(custom_headers)

        system_prompt = ""
        anthropic_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_prompt += f"{content}\n\n"
            else:
                anthropic_messages.append({
                    "role": "assistant" if role == "assistant" else "user",
                    "content": str(content)
                })

        if not anthropic_messages:
            anthropic_messages.append({"role": "user", "content": "Hello"})

        payload = {
            "model": model_id,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }
        if system_prompt.strip():
            payload["system"] = system_prompt.strip()

        req_timeout = timeout if timeout and timeout > 120 else 180
        try:
            with requests.post(endpoint, json=payload, headers=headers, stream=True, timeout=(20, req_timeout)) as resp:
                if resp.status_code != 200:
                    err_msg = resp.text[:300]
                    yield f'data: {{"error": "Anthropic HTTP {resp.status_code}: {err_msg}"}}\n\n'.encode("utf-8")
                    yield b"data: [DONE]\n\n"
                    return

                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8")
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            ev = json.loads(data_str)
                            ev_type = ev.get("type")
                            if ev_type == "content_block_delta":
                                delta = ev.get("delta", {})
                                text = delta.get("text", "")
                                if text:
                                    chunk = {"choices": [{"delta": {"content": text}}]}
                                    yield f"data: {json.dumps(chunk)}\n\n".encode("utf-8")
                            elif ev_type == "message_stop":
                                break
                        except Exception:
                            pass
                yield b"data: [DONE]\n\n"
        except Exception as e:
            yield f'data: {{"error": "{str(e)}"}}\n\n'.encode("utf-8")
            yield b"data: [DONE]\n\n"

    @staticmethod
    def _stream_gemini_native(
        base_url: str,
        api_key: str,
        model_id: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120
    ) -> Generator[bytes, None, None]:
        url = f"{base_url.rstrip('/')}/models/{model_id}:streamGenerateContent?key={api_key}&alt=sse"
        contents = []
        for m in messages:
            role = "model" if m.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": str(m.get("content", ""))}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        try:
            with requests.post(url, json=payload, stream=True, timeout=(10, timeout)) as resp:
                if resp.status_code != 200:
                    yield f'data: {{"error": "Gemini HTTP {resp.status_code}: {resp.text[:300]}"}}\n\n'.encode("utf-8")
                    yield b"data: [DONE]\n\n"
                    return

                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8")
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for p in parts:
                                    txt = p.get("text", "")
                                    if txt:
                                        chunk = {"choices": [{"delta": {"content": txt}}]}
                                        yield f"data: {json.dumps(chunk)}\n\n".encode("utf-8")
                        except Exception:
                            pass
                yield b"data: [DONE]\n\n"
        except Exception as e:
            yield f'data: {{"error": "{str(e)}"}}\n\n'.encode("utf-8")
            yield b"data: [DONE]\n\n"

    @staticmethod
    def test_connection(
        p_type: str,
        base_url: str,
        api_key: str,
        model_id: str = "",
        custom_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Runs a fast live ping to verify endpoint and API key validity."""
        base_url = base_url.rstrip("/")

        clean_key = OnlineModelClient.sanitize_api_key(api_key)
        if "integrate.api.nvidia.com" in base_url and not model_id.startswith("nvidia/") and not model_id.startswith("meta/") and not model_id.startswith("mistralai/"):
            model_id = f"nvidia/{model_id}"

        if p_type == "anthropic":
            test_url = f"{base_url}/messages"
            headers = {
                "x-api-key": clean_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            if custom_headers:
                headers.update(custom_headers)
            headers = OnlineModelClient._sanitize_headers(headers)
            payload = {
                "model": model_id or "claude-3-5-haiku-20241022",
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5
            }
            try:
                r = requests.post(test_url, json=payload, headers=headers, timeout=8)
                if r.status_code == 200:
                    return {"success": True, "message": "Successfully authenticated with Anthropic Claude."}
                return {"success": False, "error": f"Anthropic error (HTTP {r.status_code}): {r.text[:200]}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        elif p_type == "gemini" and "generativelanguage.googleapis.com" in base_url and not base_url.endswith("/openai"):
            test_url = f"{base_url}/models?key={clean_key}"
            try:
                r = requests.get(test_url, timeout=8)
                if r.status_code == 200:
                    return {"success": True, "message": "Successfully authenticated with Google Gemini."}
                return {"success": False, "error": f"Gemini error (HTTP {r.status_code}): {r.text[:200]}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        else:
            # OpenAI compatible / Webhooks
            test_url = f"{base_url}/models" if not base_url.endswith("/models") else base_url
            if not base_url.endswith("/v1") and not base_url.endswith("/models") and not base_url.endswith("/chat/completions"):
                test_url = f"{base_url}/v1/models"

            headers = {}
            if clean_key:
                headers["Authorization"] = f"Bearer {clean_key}"
            if custom_headers:
                headers.update(custom_headers)
            headers = OnlineModelClient._sanitize_headers(headers)

            try:
                r = requests.get(test_url, headers=headers, timeout=8)
                if r.status_code == 200:
                    return {"success": True, "message": f"Successfully connected (HTTP {r.status_code})."}
                elif r.status_code in [401, 403]:
                    return {"success": False, "error": f"Authentication failed (HTTP {r.status_code}). Check API Key."}
                else:
                    # Some proxies or webhooks do not support /models, try a lightweight completion
                    comp_url = f"{base_url}/chat/completions" if not base_url.endswith("/v1") else f"{base_url}/chat/completions"
                    payload = {
                        "model": model_id or "default",
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 5
                    }
                    r2 = requests.post(comp_url, json=payload, headers=headers, timeout=8)
                    if r2.status_code == 200:
                        return {"success": True, "message": f"Successfully verified endpoint (HTTP 200)."}
                    return {"success": False, "error": f"Endpoint responded with HTTP {r2.status_code}: {r2.text[:200]}"}
            except Exception as e:
                return {"success": False, "error": f"Connection failed: {str(e)}"}
