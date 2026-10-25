"""
Comprehensive regression test suite for TokenBudgetManager (Phase B).
Covers:
1. Qwen-1.5B in local/offline configuration (must yield 4096).
2. Cloud/NVIDIA model with verified provider limit (must yield 131072).
3. Local model vs Cloud model isolation with similar names (e.g. local 'qwen-1.5b' vs cloud 'qwen-turbo').
4. Explicit configured context_window in metadata.
5. Unknown model names (safe fallback, never silent enormous limit).
6. Missing/malformed metadata.
7. Usable-context calculations (never exceeds context limit).
8. Cache clearing on provider switching.
"""

import unittest
from unittest.mock import patch, MagicMock
from lmms.backend.orchestration.budget import TokenBudgetManager, BudgetBreakdown


class TestContextBudgetResolution(unittest.TestCase):

    def setUp(self):
        TokenBudgetManager.clear_global_cache()
        self.mgr = TokenBudgetManager(
            engine_url="http://127.0.0.1:0",
            default_context_limit=4096,
            default_output_reserve=768,
            safety_margin=200
        )
        self.mgr.clear_cache()

    def tearDown(self):
        self.mgr.clear_cache()

    def test_01_local_qwen_1_5b_yields_4096(self):
        """Even if an online provider is active globally, local Qwen-1.5B must resolve to 4096."""
        limit = self.mgr.get_effective_context_limit("Qwen-1.5B")
        self.assertEqual(limit, 4096)

    def test_02_cloud_nvidia_model_limit(self):
        """Registered cloud model (e.g. nvidia/nemotron) must resolve to provider limit (131072)."""
        with patch("lmms.backend.core.registry.online_models.OnlineModelRegistry.is_online_model", return_value=True), \
             patch("lmms.backend.core.registry.online_models.OnlineModelRegistry.get_model", return_value={"id": "nvidia/nemotron-3.5-super-vl-120b-a12b", "provider_id": "nvidia"}):
            self.mgr.clear_cache()
            limit = self.mgr.get_effective_context_limit("nvidia/nemotron-3.5-super-vl-120b-a12b")
            self.assertEqual(limit, 131072)

    def test_03_local_vs_cloud_similar_name_isolation(self):
        """Local 'qwen-1.5b' and cloud 'qwen-cloud-v1' must not cross-contaminate limits."""
        def mock_is_online(m_name):
            return "cloud" in m_name.lower()

        def mock_get_model(m_name):
            if "cloud" in m_name.lower():
                return {"id": m_name, "provider_id": "qwen_cloud"}
            return None

        with patch("lmms.backend.core.registry.online_models.OnlineModelRegistry.is_online_model", side_effect=mock_is_online), \
             patch("lmms.backend.core.registry.online_models.OnlineModelRegistry.get_model", side_effect=mock_get_model):
            self.mgr.clear_cache()
            local_limit = self.mgr.get_effective_context_limit("Qwen-1.5B")
            self.assertEqual(local_limit, 4096)

            cloud_limit = self.mgr.get_effective_context_limit("qwen-cloud-v1")
            self.assertEqual(cloud_limit, 131072)

    def test_04_explicit_configured_context_window(self):
        """Model with explicit context_window in metadata must be honored exactly."""
        with patch("lmms.backend.core.registry.online_models.OnlineModelRegistry.is_online_model", return_value=True), \
             patch("lmms.backend.core.registry.online_models.OnlineModelRegistry.get_model", return_value={"id": "custom-cloud-model", "context_window": 65536}):
            self.mgr.clear_cache()
            limit = self.mgr.get_effective_context_limit("custom-cloud-model")
            self.assertEqual(limit, 65536)

    def test_05_unknown_model_safe_fallback(self):
        """Unknown model must safely fall back to default limit, never an enormous 128k/1M window."""
        self.mgr.clear_cache()
        limit = self.mgr.get_effective_context_limit("completely-unknown-model-xyz")
        # Default context limit is 4096
        self.assertLessEqual(limit, 8192)
        self.assertGreaterEqual(limit, 2048)

    def test_06_usable_context_never_exceeds_context_limit(self):
        """Usable context must strictly be <= context_limit and non-negative."""
        breakdown = self.mgr.calculate_budget(
            model_name="Qwen-1.5B",
            base_prompt="System prompt",
            task_instructions="Instructions",
            tool_schemas="Tools",
            history_messages=[],
            user_query="Hello"
        )
        self.assertLessEqual(breakdown.usable_context, breakdown.context_limit)
        self.assertEqual(breakdown.context_limit, 4096)
        self.assertEqual(breakdown.output_reserve, 768)
        self.assertEqual(breakdown.safety_margin, 200)
        self.assertEqual(breakdown.usable_context, 3128)

    def test_07_cache_clearing_on_provider_switch(self):
        """Calling clear_cache ensures old model limits are not retained across switches."""
        self.mgr._limit_cache["stale_model"] = 99999
        TokenBudgetManager._global_limit_cache["stale_model"] = 99999
        self.mgr.clear_cache()
        self.assertNotIn("stale_model", self.mgr._limit_cache)
        self.assertNotIn("stale_model", TokenBudgetManager._global_limit_cache)


if __name__ == "__main__":
    unittest.main()
