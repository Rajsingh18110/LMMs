"""
lmms_server.audit - Cryptographic Hash-Chained Audit Logging for MCP Tool Calls.
Stores records in ~/.lmms/audit.jsonl with 0600 file permissions and automatic secret redaction.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_AUDIT_LOG_PATH = os.path.expanduser("~/.lmms/audit.jsonl")

# Sensitive key patterns for recursive dictionary redaction
SENSITIVE_KEY_PATTERNS = re.compile(
    r"(api_?key|auth|bearer|credential|password|private_?key|secret|token)",
    re.IGNORECASE,
)

# Sensitive value pattern (API keys, tokens, high-entropy secrets)
SECRET_VALUE_PATTERNS = re.compile(
    r"(ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|bearer\s+[A-Za-z0-9_\-\.]{12,}|xox[baprs]-[A-Za-z0-9]{10,})",
    re.IGNORECASE,
)


def redact_secrets(data: Any) -> Any:
    """Recursively redacts secrets and credentials from data structures."""
    if isinstance(data, dict):
        redacted: Dict[str, Any] = {}
        for k, v in data.items():
            if SENSITIVE_KEY_PATTERNS.search(str(k)):
                redacted[k] = "***REDACTED***"
            else:
                redacted[k] = redact_secrets(v)
        return redacted
    elif isinstance(data, list):
        return [redact_secrets(item) for item in data]
    elif isinstance(data, str):
        if SECRET_VALUE_PATTERNS.search(data):
            return SECRET_VALUE_PATTERNS.sub("***REDACTED***", data)
        return data
    return data


class AuditLogger:
    """Manages appending and verifying hash-chained audit log entries."""

    def __init__(self, log_path: Optional[str] = None):
        self.log_path = Path(os.path.abspath(os.path.expanduser(log_path or DEFAULT_AUDIT_LOG_PATH)))
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Ensures parent directory has mode 0700 and log file has mode 0600."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(str(self.log_path.parent), 0o700)
        except OSError:
            pass

        if not self.log_path.exists():
            self.log_path.touch(mode=0o600, exist_ok=True)
        else:
            try:
                os.chmod(str(self.log_path), 0o600)
            except OSError:
                pass

    def _get_last_entry(self) -> Tuple[int, str]:
        """Reads the last entry from the audit log, returning (index, hash)."""
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return -1, "0" * 64

        last_line = ""
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    last_line = line_str

        if not last_line:
            return -1, "0" * 64

        try:
            entry = json.loads(last_line)
            return entry.get("index", 0), entry.get("hash", "0" * 64)
        except Exception:
            return -1, "0" * 64

    def log_call(
        self,
        server: str,
        tool: str,
        arguments: Dict[str, Any],
        duration_ms: float,
        status: str,
        result_summary: str,
        session_id: Optional[str] = None,
        origin: str = "local",
        client_peer_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Records an MCP tool invocation to the hash-chained audit log.
        Redacts sensitive tokens and binds cryptographically to the prior entry.
        """
        self._ensure_file()
        last_index, prev_hash = self._get_last_entry()
        current_index = last_index + 1

        redacted_args = redact_secrets(copy.deepcopy(arguments))
        redacted_summary = redact_secrets(result_summary)

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        entry_data: Dict[str, Any] = {
            "index": current_index,
            "timestamp": timestamp,
            "session_id": session_id or "default",
            "server": server,
            "tool": tool,
            "arguments": redacted_args,
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "result_summary": str(redacted_summary)[:500],
            "prev_hash": prev_hash,
            "origin": origin,
        }
        if client_peer_id:
            entry_data["client_peer_id"] = client_peer_id
        if client_ip:
            entry_data["client_ip"] = client_ip

        # Canonical hash computation
        canonical_str = json.dumps(entry_data, sort_keys=True, separators=(",", ":"))
        entry_hash = hashlib.sha256(f"{prev_hash}:{canonical_str}".encode("utf-8")).hexdigest()
        entry_data["hash"] = entry_hash

        line_out = json.dumps(entry_data, separators=(",", ":")) + "\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line_out)

        return entry_data

    def verify(self) -> Tuple[bool, int, Optional[str]]:
        """
        Verifies the cryptographic integrity of the entire audit chain.
        Returns (is_valid, verified_count, error_description).
        """
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return True, 0, None

        expected_prev = "0" * 64
        count = 0

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                line_str = line.strip()
                if not line_str:
                    continue

                try:
                    entry = json.loads(line_str)
                except Exception as e:
                    return False, count, f"Line {line_idx} is malformed JSON: {e}"

                if entry.get("prev_hash") != expected_prev:
                    return (
                        False,
                        count,
                        f"Line {line_idx} (index {entry.get('index')}): prev_hash mismatch. Expected {expected_prev}, got {entry.get('prev_hash')}",
                    )

                given_hash = entry.get("hash")
                data_copy = dict(entry)
                data_copy.pop("hash", None)

                canonical_str = json.dumps(data_copy, sort_keys=True, separators=(",", ":"))
                recomputed_hash = hashlib.sha256(f"{expected_prev}:{canonical_str}".encode("utf-8")).hexdigest()

                if given_hash != recomputed_hash:
                    return (
                        False,
                        count,
                        f"Line {line_idx} (index {entry.get('index')}): hash verification failed. Data has been altered.",
                    )

                expected_prev = given_hash
                count += 1

        return True, count, None

    def view(
        self,
        limit: int = 200,
        offset: int = 0,
        server: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns recent audit records with pagination.
        offset=0 returns the latest `limit` records.
        offset=200 returns the preceding `limit` records.
        """
        if not self.log_path.exists():
            return []

        entries: List[Dict[str, Any]] = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    entry = json.loads(line_str)
                    if server and entry.get("server") != server:
                        continue
                    entries.append(entry)
                except Exception:
                    continue

        if not entries:
            return []

        end_idx = len(entries) - offset
        if end_idx <= 0:
            return []
        start_idx = max(0, end_idx - limit)
        return entries[start_idx:end_idx]


default_audit_logger = AuditLogger()
