"""
Tests for DNS Enumeration & Domain Intelligence Tool (Phase 4).
Verifies authoritative lookups, wildcard detection, candidate validation,
evidence classification, and argument normalization.
"""

import unittest
from unittest.mock import patch, MagicMock
from lmms.backend.tools.dns_tool import (
    DNSEnumerator,
    DNSEvidenceStatus,
    dns_enumerate_tool,
    format_dns_tool_output,
    dns_enumerate
)
from lmms.backend.orchestration.registry import ToolRegistry
from lmms.backend.orchestration.executor import UnifiedToolExecutor


class TestDNSEnumeration(unittest.TestCase):

    def setUp(self):
        self.enumerator = DNSEnumerator(timeout=1.0)

    @patch("lmms.backend.tools.dns_tool.HAS_DNSPYTHON", True)
    @patch("dns.resolver.Resolver")
    def test_01_query_records_verified(self, mock_resolver_cls):
        mock_resolver = MagicMock()
        mock_resolver_cls.return_value = mock_resolver

        # Mock A record answer
        mock_a_rdata = MagicMock()
        mock_a_rdata.__str__.return_value = "93.184.216.34"
        mock_resolver.resolve.return_value = [mock_a_rdata]

        res = self.enumerator.query_records("example.com", record_types=["A"])
        self.assertEqual(res["domain"], "example.com")
        self.assertIn("A", res["records"])
        self.assertEqual(res["records"]["A"]["status"], DNSEvidenceStatus.VERIFIED_RECORD)
        self.assertIn("93.184.216.34", res["records"]["A"]["records"])

    @patch("lmms.backend.tools.dns_tool.HAS_DNSPYTHON", True)
    @patch("dns.resolver.Resolver")
    def test_02_query_records_nxdomain(self, mock_resolver_cls):
        import dns.resolver
        mock_resolver = MagicMock()
        mock_resolver_cls.return_value = mock_resolver
        mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()

        res = self.enumerator.query_records("nonexistent-test-domain-999.xyz", record_types=["A"])
        self.assertEqual(res["records"]["A"]["status"], DNSEvidenceStatus.NEGATIVE_RESPONSE)
        self.assertEqual(res["records"]["A"]["records"], [])

    @patch("lmms.backend.tools.dns_tool.DNSEnumerator.check_wildcard")
    @patch("lmms.backend.tools.dns_tool.DNSEnumerator._get_resolver")
    def test_03_subdomain_enumeration_verified_and_negative(self, mock_get_res, mock_wildcard):
        mock_wildcard.return_value = None  # No wildcard

        mock_res = MagicMock()
        mock_get_res.return_value = mock_res

        # 'www' resolves, 'api' fails with NXDOMAIN
        import dns.resolver
        def _resolve_side_effect(qname, rtype):
            if "www." in str(qname):
                rdata = MagicMock()
                rdata.__str__.return_value = "1.2.3.4"
                return [rdata]
            raise dns.resolver.NXDOMAIN()

        mock_res.resolve.side_effect = _resolve_side_effect

        res = self.enumerator.enumerate_subdomains("example.com", candidates=["www", "api"])
        self.assertFalse(res["wildcard_detected"])
        self.assertEqual(res["candidates_tested"], 2)
        self.assertEqual(res["verified_count"], 1)
        self.assertEqual(res["discovered_subdomains"][0]["hostname"], "www.example.com")
        self.assertEqual(res["discovered_subdomains"][0]["status"], DNSEvidenceStatus.VERIFIED_RECORD)

    @patch("lmms.backend.tools.dns_tool.DNSEnumerator.check_wildcard")
    @patch("lmms.backend.tools.dns_tool.DNSEnumerator._get_resolver")
    def test_04_subdomain_wildcard_detection(self, mock_get_res, mock_wildcard):
        mock_wildcard.return_value = ["9.9.9.9"]  # Wildcard active on 9.9.9.9

        mock_res = MagicMock()
        mock_get_res.return_value = mock_res

        # Random subdomain resolves to the wildcard IP
        rdata = MagicMock()
        rdata.__str__.return_value = "9.9.9.9"
        mock_res.resolve.return_value = [rdata]

        res = self.enumerator.enumerate_subdomains("example.com", candidates=["randomsub"])
        self.assertTrue(res["wildcard_detected"])
        self.assertEqual(res["discovered_subdomains"][0]["status"], DNSEvidenceStatus.WILDCARD_MATCH)

    def test_05_format_dns_tool_output(self):
        data = {
            "domain": "markanm.com",
            "dns_records": {
                "records": {
                    "A": {"status": DNSEvidenceStatus.VERIFIED_RECORD, "records": ["104.21.5.1"]},
                    "MX": {"status": DNSEvidenceStatus.VERIFIED_RECORD, "records": [{"preference": 10, "exchange": "mail.markanm.com"}]}
                }
            },
            "subdomain_discovery": {
                "wildcard_detected": False,
                "candidates_tested": 14,
                "verified_count": 1,
                "discovered_subdomains": [
                    {"hostname": "www.markanm.com", "status": DNSEvidenceStatus.VERIFIED_RECORD, "addresses": ["104.21.5.1"]}
                ]
            }
        }
        formatted = format_dns_tool_output(data)
        self.assertIn("markanm.com", formatted)
        self.assertIn("104.21.5.1", formatted)
        self.assertIn("www.markanm.com", formatted)
        self.assertIn("[VERIFIED]", formatted)

    def test_06_executor_normalization_and_dispatch(self):
        reg = ToolRegistry()
        reg._register_default_tools()
        executor = UnifiedToolExecutor(reg)

        norm_name, norm_kwargs = executor.normalize_call("dns_lookup", {"target": "https://example.com/path", "type": "records"})
        self.assertEqual(norm_name, "dns.enumerate")
        self.assertEqual(norm_kwargs["domain"], "example.com")
        self.assertEqual(norm_kwargs["query_type"], "records")


if __name__ == "__main__":
    unittest.main()
