import os
import json
import pytest
from lmms.backend.core.registry.online_models import OnlineModelRegistry
from lmms.backend.providers.online_client import OnlineModelClient
from lmms.backend.core.registry.provider_presets import PROVIDER_PRESETS


def test_online_model_registry_crud(tmp_path, monkeypatch):
    test_cfg = str(tmp_path / "online_models.json")
    monkeypatch.setattr("lmms.backend.core.registry.online_models.ONLINE_MODELS_FILE", test_cfg)

    # Empty initially
    assert len(OnlineModelRegistry.list_models()) == 0
    assert OnlineModelRegistry.get_active_model() is None
    assert OnlineModelRegistry.get_active_type() == "offline"

    # Add Sarvam AI
    key1 = OnlineModelRegistry.add_model(
        name="Sarvam 2B Indic",
        provider_id="sarvam",
        provider_name="Sarvam AI",
        model_id="sarvam-2b",
        p_type="openai_compatible",
        base_url="https://api.sarvam.ai/v1",
        api_key="secret-key-12345",
        category="indian_ai",
        set_active=True
    )

    assert key1 == "sarvam:sarvam-2b"
    assert OnlineModelRegistry.is_online_model("sarvam:sarvam-2b")
    assert OnlineModelRegistry.is_online_model("sarvam-2b")
    assert OnlineModelRegistry.get_active_type() == "online"

    active = OnlineModelRegistry.get_active_model()
    assert active is not None
    assert active["name"] == "Sarvam 2B Indic"

    # Safe listing masks keys
    models = OnlineModelRegistry.list_models(safe=True)
    assert len(models) == 1
    assert "secr••••••••2345" in models[0]["api_key_masked"]

    # Add Custom Webhook
    key2 = OnlineModelRegistry.add_model(
        name="My Custom Webhook",
        provider_id="custom_webhook",
        provider_name="Custom Webhook",
        model_id="custom-agent-v1",
        p_type="custom_webhook",
        base_url="https://my-webhook.domain.com/v1",
        api_key="token-abc",
        category="custom",
        set_active=False
    )
    assert len(OnlineModelRegistry.list_models()) == 2

    # Switch active
    OnlineModelRegistry.set_active_model(key2, "online")
    assert OnlineModelRegistry.get_active_model()["key"] == key2

    # Remove model
    assert OnlineModelRegistry.remove_model(key1) is True
    assert len(OnlineModelRegistry.list_models()) == 1


def test_indian_providers_in_presets():
    assert "sarvam" in PROVIDER_PRESETS
    assert "krutrim" in PROVIDER_PRESETS
    assert "two_ai" in PROVIDER_PRESETS
    assert "bharatgpt" in PROVIDER_PRESETS
    assert "custom_webhook" in PROVIDER_PRESETS

    assert PROVIDER_PRESETS["sarvam"]["category"] == "indian_ai"
    assert "sarvam-2b" in PROVIDER_PRESETS["sarvam"]["models"]
    assert "Krutrim-spectre-v2" in PROVIDER_PRESETS["krutrim"]["models"]


def test_api_key_sanitization_and_env_block():
    raw_env_paste = """MODEL_BASE_URL=https://nvidia.com
MODEL_API_KEY=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
NEMOTRON_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b"""

    cleaned = OnlineModelClient.sanitize_api_key(raw_env_paste)
    assert cleaned == "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"
    assert "\n" not in cleaned
    assert "\r" not in cleaned

    # Test quotes and whitespace
    assert OnlineModelClient.sanitize_api_key(' "sk-test-12345" \n') == "sk-test-12345"


def test_nvidia_nim_preset():
    assert "nvidia" in PROVIDER_PRESETS
    assert PROVIDER_PRESETS["nvidia"]["base_url"] == "https://integrate.api.nvidia.com/v1"
    assert "nvidia/nemotron-3.5-super-vl-120b-a12b" in PROVIDER_PRESETS["nvidia"]["models"]


def test_clean_model_display_name(tmp_path, monkeypatch):
    test_cfg = str(tmp_path / "online_models.json")
    monkeypatch.setattr("lmms.backend.core.registry.online_models.ONLINE_MODELS_FILE", test_cfg)

    from lmms.backend.main import get_clean_model_display_name

    # Unregistered key returns itself
    assert get_clean_model_display_name("unknown:key") == "unknown:key"
    assert get_clean_model_display_name(None) == "None"

    # Add a model and check clean name
    key = OnlineModelRegistry.add_model(
        name="NVIDIA Nemotron 3.5 Super VL",
        provider_id="nvidia",
        provider_name="NVIDIA NIM",
        model_id="nvidia/nemotron-3.5-super-vl-120b-a12b",
        p_type="openai_compatible",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="nvapi-test",
        category="global",
        set_active=True
    )

    clean_name = get_clean_model_display_name(key)
    assert clean_name == "nvidia/nemotron-3.5-super-vl-120b-a12b"


def test_search_provider_depth():
    from lmms.backend.tools.search_provider import DDGSSearchProvider
    provider = DDGSSearchProvider()
    results = provider.search("Linux operating system", max_results=24)
    assert isinstance(results, list)
    assert len(results) > 0
    assert len(results) <= 24
    for r in results:
        assert "title" in r
        assert "url" in r
        assert "snippet" in r


def test_robust_parse_xml_and_nemotron_tool_calls():
    from lmms.backend.main import robust_parse_tool_call

    # Nemotron XML format 1 (files.list with kwargs tag)
    tc1 = """<tool_call>
<function=files.list>
<kwargs>
{"path":"/home/kali/heretic"}
</parameter>
</function>
</tool_call>"""
    res1 = robust_parse_tool_call(tc1)
    assert res1["tool"] == "files.list"
    assert res1["kwargs"] == {"path": "/home/kali/heretic"}

    # Nemotron XML format 2 (terminal.run with parameter=command)
    tc2 = """<tool_call>
<function=terminal.run>
<parameter=command>
ls -la /home/kali/heretic
</parameter>
</function>
</tool_call>"""
    res2 = robust_parse_tool_call(tc2)
    assert res2["tool"] == "terminal.run"
    assert res2["kwargs"] == {"command": "ls -la /home/kali/heretic"}

    # Nemotron XML format 3 (cat README.md)
    tc3 = """<function=terminal.run>
<parameter=command>
cat README.md
</parameter>
</function>"""
    res3 = robust_parse_tool_call(tc3)
    assert res3["tool"] == "terminal.run"
    assert res3["kwargs"] == {"command": "cat README.md"}

    # OpenAI format
    tc4 = '<tool_call>{"name": "files.read", "arguments": {"path": "README.md"}}</tool_call>'
    res4 = robust_parse_tool_call(tc4)
    assert res4["tool"] == "files.read"
    assert res4["kwargs"] == {"path": "README.md"}


def test_dynamic_context_window_online_and_local(tmp_path, monkeypatch):
    from lmms.backend.orchestration.budget import TokenBudgetManager

    mgr = TokenBudgetManager(engine_url="http://127.0.0.1:0")

    # Online models get dynamic native context
    assert mgr.get_effective_context_limit("gemini-2.5-pro") >= 1000000
    assert mgr.get_effective_context_limit("claude-3-7-sonnet") >= 200000
    assert mgr.get_effective_context_limit("nvidia/nemotron-3.5-super-vl-120b-a12b") == 131072
    assert mgr.get_effective_context_limit("gpt-4o") == 128000

    # Large local models (70B, 770B) get hardware-scaled context, not arbitrary 4096
    local_770b_ctx = mgr.get_effective_context_limit("deepseek-v3-770b")
    assert local_770b_ctx >= 8192


def test_dynamic_output_reserve_scaling():
    from lmms.backend.orchestration.budget import TokenBudgetManager

    mgr = TokenBudgetManager(engine_url="http://127.0.0.1:0")

    # 128k context model gets generous dynamic output reserve (8192 tokens), never hardcoded 768!
    b_128k = mgr.calculate_budget(
        model_name="nvidia/nemotron-3.5-super-vl-120b-a12b",
        base_prompt="System prompt",
        task_instructions="Do task",
        tool_schemas="",
        history_messages=[],
        user_query="Hello"
    )
    assert b_128k.output_reserve == 8192
    assert b_128k.usable_context > 100000

    # 8k context model scales appropriately
    b_8k = mgr.calculate_budget(
        model_name="small-model:8b",
        base_prompt="System prompt",
        task_instructions="",
        tool_schemas="",
        history_messages=[],
        user_query="Hello"
    )
    assert b_8k.output_reserve >= 1024


def test_openai_streaming_tool_call_accumulation(monkeypatch):
    import requests
    from unittest.mock import MagicMock

    # Simulate SSE lines with fragmented OpenAI tool calls
    sse_lines = [
        b'data: {"choices":[{"delta":{"role":"assistant","content":null,"tool_calls":[{"index":0,"id":"call-123","type":"function","function":{"name":"files.read","arguments":""}}]}}]}\n',
        b'data: {"choices":[{"delta":{"content":null,"tool_calls":[{"index":0,"function":{"arguments":"{\\"path\\": "}}]}}]}\n',
        b'data: {"choices":[{"delta":{"content":null,"tool_calls":[{"index":0,"function":{"arguments":"\\"/home/kali/heretic/setup.py\\"}"}}]}}]}\n',
        b'data: {"choices":[{"finish_reason":"tool_calls"}]}\n',
        b'data: [DONE]\n'
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_lines.return_value = sse_lines
    mock_resp.__enter__.return_value = mock_resp

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: mock_resp)

    chunks = list(OnlineModelClient._stream_openai_compatible(
        base_url="https://api.test.com/v1",
        api_key="sk-test",
        model_id="test-model",
        messages=[{"role": "user", "content": "read setup.py"}]
    ))

    combined = b"".join(chunks).decode("utf-8")
    assert 'files.read' in combined
    assert '/home/kali/heretic/setup.py' in combined
    # Extract SSE content JSON
    for line in combined.splitlines():
        if line.startswith("data: {"):
            d = json.loads(line[6:])
            content = d.get("content", "")
            if "<tool_call>" in content:
                assert '<tool_call>{"tool": "files.read", "kwargs": {"path": "/home/kali/heretic/setup.py"}}</tool_call>' == content
