"""Load project-scoped instructions for the interactive coding agent."""

import os

from lmms.backend.tools.boundaries import is_within_workspace


RULES_FILENAME = "LMMS.md"
MAX_RULES_CHARS = 12_000


def load_workspace_rules(workspace: str | None) -> str:
    """Return trusted workspace rules without allowing them to consume all context."""
    if not workspace or workspace == "None" or not os.path.isdir(workspace):
        return ""

    rules_path = os.path.join(workspace, RULES_FILENAME)
    if not is_within_workspace(rules_path, workspace) or not os.path.isfile(rules_path):
        return ""

    try:
        with open(rules_path, "r", encoding="utf-8") as rules_file:
            rules = rules_file.read(MAX_RULES_CHARS + 1)
    except OSError:
        return ""

    if len(rules) > MAX_RULES_CHARS:
        rules = rules[:MAX_RULES_CHARS] + "\n[LMMS.md truncated at 12,000 characters]"
    return rules.strip()
