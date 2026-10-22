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

"""Unit tests for Provider Registry and 50+ Provider Presets."""

import pytest
from lmms.backend.core.registry.provider_presets import PROVIDER_PRESETS
from lmms.backend.core.registry.provider_registry import ProviderRegistry


class TestProviderRegistryPresets:
    """Verifies the 50+ provider preset catalog and connection testing."""

    def test_presets_catalog_coverage(self):
        presets = ProviderRegistry.list_presets()
        assert len(presets) >= 50
        # Check essential local providers
        assert "ollama" in presets
        assert "vllm" in presets
        assert "lm_studio" in presets
        assert "llama_cpp" in presets
        assert "jan" in presets
        assert "localai" in presets

        # Check essential cloud providers
        assert "openai" in presets
        assert "anthropic" in presets
        assert "gemini" in presets
        assert "groq" in presets
        assert "deepseek" in presets
        assert "mistral" in presets
        assert "openrouter" in presets
        assert "together" in presets
        assert "fireworks" in presets

    def test_preset_instantiation(self, tmp_path, monkeypatch):
        test_file = str(tmp_path / "providers.json")
        monkeypatch.setattr("lmms.backend.core.registry.provider_registry.PROVIDERS_FILE", test_file)

        pid = ProviderRegistry.create_from_preset("groq", api_key="gsk-testkey123")
        assert pid is not None

        prov = ProviderRegistry.get(pid)
        assert prov is not None
        assert prov["name"] == "Groq Fast LPU"
        assert prov["type"] == "openai_compatible"
        assert prov["api_key"] == "gsk-testkey123"
        assert "https://api.groq.com/openai/v1" in prov["base_url"]
        assert "llama-3.3-70b-versatile" in prov["default_model"]
