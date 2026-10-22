import os
import tempfile
import unittest

from lmms.backend.notifications import send_notification
from lmms.backend.security.keyring import KeyringVault
from lmms.backend.telemetry.metrics import MetricsTracker


class TestNotificationsAndKeyring(unittest.TestCase):

    def test_send_notification(self):
        # Should gracefully succeed on any platform (notify-send or stderr fallback)
        res = send_notification("LMMs Test", "Test message from automated suite")
        self.assertTrue(res)

    def test_keyring_vault_crud_and_permissions(self):
        with tempfile.TemporaryDirectory() as td:
            cred_file = os.path.join(td, "test_creds.json")
            vault = KeyringVault(storage_path=cred_file)

            # File created with 0600
            mode = oct(os.stat(cred_file).st_mode & 0o777)
            self.assertEqual(mode, "0o600")

            # Set keys
            vault.set_key("OPENAI_API_KEY", "sk-test123456789")
            vault.set_key("ANTHROPIC_API_KEY", "sk-ant-test98765")

            # Get keys
            self.assertEqual(vault.get_key("openai_api_key"), "sk-test123456789")
            self.assertEqual(vault.get_key("ANTHROPIC_API_KEY"), "sk-ant-test98765")
            self.assertIsNone(vault.get_key("NON_EXISTENT"))

            # List
            services = vault.list_services()
            self.assertEqual(services, ["anthropic_api_key", "openai_api_key"])

            # Delete
            deleted = vault.delete_key("openai_api_key")
            self.assertTrue(deleted)
            self.assertIsNone(vault.get_key("openai_api_key"))

    def test_metrics_tracker_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            metrics_file = os.path.join(td, "test_metrics.json")
            tracker = MetricsTracker(storage_path=metrics_file)

            tracker.record_tokens(prompt_tokens=150, completion_tokens=50, duration_s=1.2)
            tracker.record_tool_call(tool_name="terminal.run", duration_s=0.45, success=True)
            tracker.record_tool_call(tool_name="file.read", duration_s=0.05, success=True)
            tracker.record_tool_call(tool_name="file.read", duration_s=0.08, success=False)

            summary = tracker.get_summary()
            self.assertEqual(summary["total_tokens"], 200)
            self.assertEqual(summary["total_requests"], 1)
            self.assertEqual(summary["tools_used"], 2)
            self.assertEqual(summary["tools_summary"]["file.read"]["invocations"], 2)
            self.assertEqual(summary["tools_summary"]["file.read"]["successes"], 1)
            self.assertEqual(summary["tools_summary"]["file.read"]["failures"], 1)

            # Verify reload from disk
            tracker2 = MetricsTracker(storage_path=metrics_file)
            summary2 = tracker2.get_summary()
            self.assertEqual(summary2["total_tokens"], 200)


if __name__ == "__main__":
    unittest.main()
