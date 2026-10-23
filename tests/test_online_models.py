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
