import re
import shlex
from typing import Tuple, List, Optional
from lmms.backend.security.scope import load_scope, validate_target

# Tools that trigger target validation
SECURITY_TOOLS = {"nmap", "curl", "ping", "wget", "nc", "netcat", "dig", "host", "nslookup", "nikto", "gobuster", "ffuf", "wfuzz"}

# Strictly prohibited tools (destructive/unauthorized)
DESTRUCTIVE_TOOLS = {"sqlmap", "metasploit", "msfconsole", "msfvenom", "hydra", "medusa", "ncrack", "john", "hashcat", "rm -rf", "dd"}

def extract_targets_from_command(command: str) -> List[str]:
    """Extremely basic heuristic to extract IP addresses and domain names from command."""
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
        
    targets = []
    # simple IPv4 regex
    ipv4_re = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
    # simple domain regex
    domain_re = re.compile(r"^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$")
    
    for part in parts:
        # Strip URL schemes if present
        target_str = part.replace("http://", "").replace("https://", "")
        # Remove paths
        target_str = target_str.split("/")[0]
        # Remove ports
        target_str = target_str.split(":")[0]
        
        if ipv4_re.match(target_str) or domain_re.match(target_str):
            targets.append(target_str)
            
    return targets

def validate_security_command(workspace: str, command: str) -> Tuple[bool, str]:
    """
    Validates a command against the workspace scope.
    Returns (is_allowed, reason).
    """
    if not workspace or workspace == "None":
        return True, "No workspace scope applied."

    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
        
    if not parts:
        return True, "Empty command"
        
    base_cmd = parts[0]
    
    # Block destructive tools unconditionally
    if base_cmd in DESTRUCTIVE_TOOLS or any(dt in command for dt in DESTRUCTIVE_TOOLS):
        return False, f"Command contains prohibited destructive tool: {base_cmd}"

    # If it's a security/network tool, we must validate against scope
    if base_cmd in SECURITY_TOOLS:
        scope = load_scope(workspace)
        
        # Default behavior: Offline only
        if not scope:
            # Allow local targets
            targets = extract_targets_from_command(command)
            for t in targets:
                if not validate_target(t, ["127.0.0.1", "localhost"]):
                    return False, f"No scope file found. Offline mode restricts target {t}"
            return True, "Offline local target allowed."
            
        if not scope.get("network_actions_allowed", False):
            return False, "Network actions are explicitly disabled in scope."
            
        if base_cmd not in scope.get("allowed_tools", []):
            return False, f"Tool '{base_cmd}' is not in allowed_tools scope."
            
        targets = extract_targets_from_command(command)
        for t in targets:
            if not validate_target(t, scope.get("authorized_targets", [])):
                return False, f"Target '{t}' is NOT in authorized_targets scope."
                
    return True, "Command allowed by scope."
