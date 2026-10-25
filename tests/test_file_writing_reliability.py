"""
Reliability and integrity tests for FileTool and canonical_file_write.
Validates read-back verification, empty files, large multi-section documents,
Unicode content, partial-write failure detection, and boundary enforcement.
"""

import os
import tempfile
import pytest
from lmms.backend.tools.files import FileTool, canonical_file_write, _write_and_verify


def test_write_empty_file_verified():
    """Verify writing an empty file produces accurate zero-byte verification metadata."""
    ft = FileTool()
    with tempfile.TemporaryDirectory() as tmpdir:
        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = tmpdir
            target = os.path.join(tmpdir, "empty.txt")

            res = ft.write(target, "")
            assert "[FILE_WRITE_VERIFIED]" in res
            assert "0 lines" in res
            assert "0 chars" in res
            assert "0 bytes" in res

            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
            assert content == ""

            # Also verify canonical_file_write
            c_res = canonical_file_write(os.path.join(tmpdir, "canonical_empty.txt"), "")
            assert c_res["status"] == "success"
            assert c_res["verified"] is True
            assert c_res["chars"] == 0
            assert c_res["bytes"] == 0
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]


def test_write_large_multisection_document_verified():
    """Verify writing a large multi-section document (~15KB) with headers, tables, code blocks."""
    ft = FileTool()
    with tempfile.TemporaryDirectory() as tmpdir:
        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = tmpdir
            target = os.path.join(tmpdir, "comprehensive_report.md")

            sections = ["# Comprehensive Engineering Report\n"]
            for i in range(1, 30):
                sections.append(f"## Section {i}: Architecture Analysis\n")
                sections.append(f"Paragraph detailing subsystem {i} specifications, metrics, and requirements.\n")
                sections.append("```python\ndef handler_{i}():\n    return 'status_ok'\n```\n\n")
            large_content = "".join(sections)

            res = ft.write(target, large_content)
            assert "[FILE_WRITE_VERIFIED]" in res
            assert f"{len(large_content)} chars" in res
            assert f"{len(large_content.encode('utf-8'))} bytes" in res

            with open(target, "r", encoding="utf-8") as f:
                persisted = f.read()
            assert persisted == large_content
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]


def test_write_unicode_content_verified():
    """Verify write integrity with multi-byte Unicode (Hindi, Emojis, Accents, Chinese)."""
    ft = FileTool()
    with tempfile.TemporaryDirectory() as tmpdir:
        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = tmpdir
            target = os.path.join(tmpdir, "unicode_test.txt")
            unicode_text = (
                "Hindi: नमस्ते दुनिया! LMMs में आपका स्वागत है।\n"
                "Emojis: 🚀 🤖 ⚡ 🔒 🌐 🛡️\n"
                "French: Café, résumé, naïve, façade, déjà vu.\n"
                "Chinese: 大模型工作室 (Large Models Machine Studio)\n"
            )

            res = ft.write(target, unicode_text)
            assert "[FILE_WRITE_VERIFIED]" in res
            assert f"{len(unicode_text)} chars" in res
            assert f"{len(unicode_text.encode('utf-8'))} bytes" in res

            with open(target, "r", encoding="utf-8") as f:
                persisted = f.read()
            assert persisted == unicode_text
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]


def test_partial_write_truncation_caught_and_reported(monkeypatch):
    """Verify simulated write truncation is caught by read-back verification and reported as integrity error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = os.path.join(tmpdir, "truncated.txt")
        full_content = "Complete 100% verified payload."

        import builtins
        orig_open = builtins.open
        def mock_open(file, mode="r", *args, **kwargs):
            if "r" in mode and str(file) == str(target):
                import io
                # Simulate truncation to 10 chars
                return io.StringIO(full_content[:10])
            return orig_open(file, mode, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", mock_open)
        success, msg, stats = _write_and_verify(target, full_content, max_retries=1)
        assert success is False
        assert "FILE_WRITE_INTEGRITY_ERROR" in msg
        assert "Expected 31 chars" in msg
        assert "read back 10 chars" in msg


def test_workspace_boundary_enforcement():
    """Verify attempting to write outside workspace directory is blocked."""
    ft = FileTool()
    with tempfile.TemporaryDirectory() as tmpdir:
        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = tmpdir
            # Attempt to write outside workspace (e.g. /etc or parent directory)
            outside_target = os.path.abspath(os.path.join(tmpdir, "..", "escaped.txt"))
            res = ft.write(outside_target, "malicious escape")
            assert "Error:" in res or "SecurityBoundaryError" in res or "Forbidden" in res
            assert not os.path.exists(outside_target)
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]
