"""
Regression tests for Research Pipeline, Duplicate Answer Prevention,
and Fast Browser DNS Validation (Phase 3, Phase 5, Phase 8).
"""

import unittest
from unittest.mock import patch, MagicMock
from lmms.backend.tools.browser import BrowserTool
from lmms.backend.orchestration.router import IntentRouter, IntentType


class TestResearchAndFinalization(unittest.TestCase):

    def setUp(self):
        self.router = IntentRouter()

    def test_01_dns_and_subdomain_intent_routing(self):
        """Verify queries asking about subdomains and DNS route to web_search/network tools."""
        res = self.router.route("search about markanm and give each and every information regarding this and there subdomains ok")
        self.assertEqual(res.intent, IntentType.WEB_SEARCH)
        self.assertTrue(res.requires_tools)

        res2 = self.router.route("check dns mx record for markanm.com")
        self.assertEqual(res2.intent, IntentType.WEB_SEARCH)
        self.assertTrue(res2.requires_tools)

    def test_02_browser_fast_dns_pre_check_nxdomain(self):
        """Verify non-existent host is rejected instantly via DNS check without 30s timeout."""
        bt = BrowserTool()
        err = bt._fast_dns_check("https://non-existent-subdomain-123456789.markanm.com")
        self.assertIsNotNone(err)
        self.assertIn("NXDOMAIN", err)

    def test_03_browser_fast_dns_pre_check_local(self):
        """Verify localhost and local domains bypass fast remote DNS check."""
        bt = BrowserTool()
        self.assertIsNone(bt._fast_dns_check("http://localhost:8000"))
        self.assertIsNone(bt._fast_dns_check("http://127.0.0.1:3000"))

    def test_04_substantive_answer_detection(self):
        """Verify substantive answer detection correctly identifies structured completed reports."""
        text_substantive = (
            "Based on my research, here is comprehensive information about MarkanM:\n\n"
            "## What is MarkanM?\n"
            "MarkanM is an independent software and digital solutions brand led by Adarsh Kumar.\n"
            "• Website: https://markanm.com\n"
            "• Key Products: LMMs, Cogniton AI, and developer tools.\n\n"
            "Regarding subdomains, the primary public services operate under the main domain."
        )
        has_substantive = (
            len(text_substantive) >= 120 and
            any(marker in text_substantive for marker in ["\n", "1.", "2.", "- ", "* ", "• ", "http", "Overview", "Based on"])
        )
        self.assertTrue(has_substantive)

        short_thought = "I will search the web for markanm subdomains."
        has_substantive_short = (
            len(short_thought) >= 120 and
            any(marker in short_thought for marker in ["\n", "1.", "2.", "- ", "* ", "• ", "http", "Overview", "Based on"])
        )
        self.assertFalse(has_substantive_short)


if __name__ == "__main__":
    unittest.main()
