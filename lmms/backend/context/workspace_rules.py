"""
Hierarchical workspace instruction loader for LMMs.
Matches OpenAI Codex AGENTS.md discovery architecture:
Searches for AGENTS.md, .agents.md, LMMS.md, and CLAUDE.md from the workspace
root and across subdirectories hierarchically, merging instructions within
a bounded character budget.
"""

from __future__ import annotations

import os
from typing import List, Optional

from lmms.backend.tools.boundaries import is_within_workspace

RULE_CANDIDATES = [
    "AGENTS.md",
    "agents.md",
    ".agents.md",
    "LMMS.md",
    "CLAUDE.md",
]

MAX_RULES_CHARS = 12_000


def find_rule_files(workspace_root: str, current_dir: Optional[str] = None) -> List[str]:
    """Find all rule files hierarchically from workspace root down to current_dir."""
    if not workspace_root or not os.path.isdir(workspace_root):
        return []

    discovered = []
    seen_paths = set()

    # 1. Search root first
    for name in RULE_CANDIDATES:
        cand = os.path.join(workspace_root, name)
        if os.path.isfile(cand) and is_within_workspace(cand, workspace_root):
            if cand not in seen_paths:
                discovered.append(cand)
                seen_paths.add(cand)

    # 2. Search .lmms directory
    lmms_dir = os.path.join(workspace_root, ".lmms")
    if os.path.isdir(lmms_dir):
        for name in RULE_CANDIDATES:
            cand = os.path.join(lmms_dir, name)
            if os.path.isfile(cand) and is_within_workspace(cand, workspace_root):
                if cand not in seen_paths:
                    discovered.append(cand)
                    seen_paths.add(cand)

    # 3. If a specific subdirectory is provided, traverse up from it to workspace root
    if current_dir and os.path.isdir(current_dir) and is_within_workspace(current_dir, workspace_root):
        curr = os.path.abspath(current_dir)
        root = os.path.abspath(workspace_root)
        sub_chain = []
        while curr != root and is_within_workspace(curr, root):
            for name in RULE_CANDIDATES:
                cand = os.path.join(curr, name)
                if os.path.isfile(cand) and cand not in seen_paths:
                    sub_chain.append(cand)
                    seen_paths.add(cand)
            parent = os.path.dirname(curr)
            if parent == curr:
                break
            curr = parent
        # Append subdirectory rules from top to bottom
        discovered.extend(reversed(sub_chain))

    return discovered


def load_workspace_rules(workspace: str | None, current_dir: Optional[str] = None) -> str:
    """Return merged hierarchical workspace instructions within context limits."""
    if not workspace or workspace == "None" or not os.path.isdir(workspace):
        return ""

    rule_files = find_rule_files(workspace, current_dir)
    if not rule_files:
        return ""

    sections = []
    remaining_chars = MAX_RULES_CHARS

    for rf in rule_files:
        if remaining_chars <= 100:
            break
        try:
            rel = os.path.relpath(rf, workspace)
            with open(rf, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(remaining_chars + 1).strip()
            
            if content:
                header = f"=== Instructions from {rel} ==="
                budget_for_body = remaining_chars - len(header) - 4
                if len(content) > budget_for_body:
                    content = content[:budget_for_body] + f"\n... [Truncated {rel} to preserve budget]"
                sections.append(f"{header}\n{content}")
                remaining_chars -= len(sections[-1]) + 2
        except OSError:
            continue

    merged = "\n\n".join(sections)
    return merged.strip()
