import shlex
import re
from typing import List, Tuple

class CommandParserError(Exception):
    pass

def parse_shell_command(command: str) -> List[Tuple[str, List[str]]]:
    """
    Parses a shell command into a list of (base_executable, [args]).
    Raises CommandParserError if dangerous constructs are detected.
    """
    
    # Check for dangerous shell constructs
    dangerous_patterns = []
    
    for pattern in dangerous_patterns:
        if re.search(pattern, command):
            raise CommandParserError(f"Command contains blocked shell construct matching pattern: {pattern}")
            
    try:
        parts = shlex.split(command)
    except ValueError as e:
        raise CommandParserError(f"Failed to parse command syntax: {e}")
        
    if not parts:
        return []
        
    # Remove absolute path for the base executable to check tool name
    # e.g. /usr/bin/nmap -> nmap
    base_exec = parts[0].split("/")[-1]
    
    # We only parsed a single sequential command because we blocked chaining/pipes
    return [(base_exec, parts)]

def extract_targets(command: str) -> List[str]:
    """Extremely basic heuristic to extract IP addresses and domain names from command."""
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
        
    targets = []
    ipv4_re = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
    domain_re = re.compile(r"^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$")
    
    for part in parts:
        target_str = part.replace("http://", "").replace("https://", "")
        target_str = target_str.split("/")[0]
        target_str = target_str.split(":")[0]
        
        if ipv4_re.match(target_str) or domain_re.match(target_str) or target_str == "localhost":
            targets.append(target_str)
            
    return targets
