"""
lmms_server.audit_cli - CLI interface for `lmms audit view` and `lmms audit verify`.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from lmms_server.audit import default_audit_logger


def handle_audit_cli(argv: List[str]) -> int:
    """Entrypoint for `lmms audit <subcommand>`."""
    parser = argparse.ArgumentParser(prog="lmms audit", description="LMMs Cryptographic Audit Log")
    subparsers = parser.add_subparsers(dest="subcommand", help="Audit subcommands")

    # `lmms audit view`
    view_parser = subparsers.add_parser("view", help="View recent audit log entries")
    view_parser.add_argument("--limit", type=int, default=20, help="Maximum entries to display (default: 20)")
    view_parser.add_argument("--server", type=str, default=None, help="Filter entries by MCP server name")
    view_parser.add_argument("--json", action="store_true", help="Output raw JSON format")

    # `lmms audit verify`
    verify_parser = subparsers.add_parser("verify", help="Verify cryptographic hash chain integrity")

    args = parser.parse_args(argv)

    if args.subcommand == "view":
        entries = default_audit_logger.view(limit=args.limit, server=args.server)
        if getattr(args, "json", False):
            sys.stdout.write(json.dumps(entries, indent=2) + "\n")
            return 0

        if not entries:
            sys.stdout.write("No audit log records found.\n")
            return 0

        sys.stdout.write(f"\n{'='*75}\n")
        sys.stdout.write(f"  LMMs Audit Trail (Latest {len(entries)} Entries)\n")
        sys.stdout.write(f"{'='*75}\n")
        for e in entries:
            idx = e.get("index", 0)
            ts = e.get("timestamp", "")
            srv = e.get("server", "")
            tool = e.get("tool", "")
            status = e.get("status", "")
            dur = e.get("duration_ms", 0)
            h = e.get("hash", "")[:12]
            sys.stdout.write(f"[{idx:04d}] {ts} | {srv}:{tool} ({status}, {dur}ms) [hash: {h}...]\n")
            args_str = json.dumps(e.get("arguments", {}), separators=(", ", ": "))
            if len(args_str) > 80:
                args_str = args_str[:77] + "..."
            sys.stdout.write(f"       args: {args_str}\n")
            summary = e.get("result_summary", "")
            if summary:
                if len(summary) > 80:
                    summary = summary[:77] + "..."
                sys.stdout.write(f"       summary: {summary}\n")
        sys.stdout.write(f"{'='*75}\n\n")
        return 0

    elif args.subcommand == "verify":
        is_valid, count, err = default_audit_logger.verify()
        if is_valid:
            sys.stdout.write(f"✔ Audit log verified: {count} hash-chained records intact (zero tampering detected).\n")
            return 0
        else:
            sys.stderr.write(f"✖ Audit log integrity failure: {err}\n")
            return 1

    else:
        parser.print_help()
        return 1
