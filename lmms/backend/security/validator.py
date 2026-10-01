"""Compatibility helpers for validating scoped security commands."""

from lmms.backend.security.command_parser import CommandParserError, extract_targets, parse_shell_command
from lmms.backend.security.scope import is_scope_active, load_scope
from lmms.backend.security.target_validator import is_target_authorized


DESTRUCTIVE_TOOLS = {
    "sqlmap", "metasploit", "msfconsole", "msfvenom", "hydra", "medusa",
    "ncrack", "john", "hashcat", "dd", "mkfs", "fdisk",
}
SCOPED_TOOLS = {
    "nmap", "curl", "wget", "ping", "nc", "netcat", "tcpdump",
    "dig", "host", "traceroute", "netstat", "arp", "route",
}


def extract_targets_from_command(command: str) -> list[str]:
    return extract_targets(command)


def validate_security_command(workspace: str, command: str) -> tuple[bool, str]:
    """Validate scoped network/security commands without executing them."""
    try:
        parsed = parse_shell_command(command)
    except CommandParserError as exc:
        return False, str(exc)

    if not parsed:
        return False, "Empty command."

    tool_name = parsed[0][0]
    if tool_name in DESTRUCTIVE_TOOLS:
        return False, f"{tool_name} is a destructive tool and is blocked."
    if tool_name not in SCOPED_TOOLS:
        return True, "Non-security command allowed."

    scope = load_scope(workspace)
    if not is_scope_active(scope):
        return False, "Scope is not active."
    if tool_name not in scope.get("allowed_tools", []):
        return False, f"Tool '{tool_name}' is not in allowed_tools."
    if not scope.get("network_actions_allowed", False):
        return False, "Network actions are disabled in scope."

    for target in extract_targets(command):
        if not is_target_authorized(target, scope.get("authorized_targets", [])):
            return False, f"Target '{target}' is NOT in authorized_targets."
    return True, "Allowed by active scope."
