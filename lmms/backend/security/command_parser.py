import shlex
import re
from typing import List, Tuple

class CommandParserError(Exception):
    def __init__(self, message: str, construct: str = "", reason: str = "", remedy: str = ""):
        super().__init__(message)
        self.message = message
        self.construct = construct
        self.reason = reason
        self.remedy = remedy

BLOCKED_CONSTRUCT_DETAILS = [
    (r"&&", "logical AND chaining ('&&')",
     "Command chaining via '&&' is blocked by security policy to prevent uninspected multi-command execution.",
     "Execute commands sequentially as separate, individual tool calls instead of chaining with '&&'."),
    (r";", "semicolon command chaining (';')",
     "Command chaining via ';' is blocked by security policy to prevent sequential command injection.",
     "Execute commands sequentially as separate, individual tool calls instead of chaining with ';'."),
    (r"\|\|", "logical OR chaining ('||')",
     "Conditional command chaining via '||' is blocked by security policy.",
     "Execute commands individually and inspect return codes explicitly."),
    (r"\|", "shell pipeline ('|')",
     "Shell pipelines ('|') are blocked in direct command execution.",
     "Run individual commands or use file reading/writing tools instead of piping."),
    (r">", "output redirection ('>')",
     "Shell output redirection is blocked to prevent unmonitored host file writes.",
     "Use the 'files.write' tool to create or modify files safely within the workspace boundary."),
    (r"<", "input redirection ('<')",
     "Shell input redirection is blocked to prevent file descriptor tampering.",
     "Use the 'files.read' tool to inspect file contents or pass arguments directly."),
    (r"\$\(", "subshell command substitution ('$()')",
     "Command substitution via '$()' is blocked to prevent nested uninspected command execution.",
     "Run the subshell command first in a separate step and pass its output explicitly."),
    (r"`", "backtick command substitution ('`')",
     "Backtick command substitution is blocked to prevent nested uninspected command execution.",
     "Run the subshell command first in a separate step and pass its output explicitly."),
    (r"&(?!\w)", "background execution ('&')",
     "Background process execution is blocked to ensure synchronous process lifecycle tracking.",
     "Run commands synchronously without backgrounding '&'."),
    (r"(?<![-./])\bsudo\b", "privilege escalation ('sudo')",
     "Root privilege escalation via 'sudo' is strictly forbidden.",
     "Execute commands with normal workspace privileges without sudo."),
    (r"(?<![-./])\bsu\b", "privilege escalation ('su')",
     "Switching user accounts via 'su' is strictly forbidden.",
     "Execute commands with normal workspace privileges without su."),
    (r"(?<![-./])\bbash\b", "nested shell invocation ('bash')",
     "Nested shell execution via 'bash' is blocked to prevent policy bypass.",
     "Execute the target binary or script directly without invoking bash."),
    (r"(?<![-./])\bsh\b", "nested shell invocation ('sh')",
     "Nested shell execution via 'sh' is blocked to prevent policy bypass.",
     "Execute the target binary or script directly without invoking sh."),
    (r"(?<![-./])\bzsh\b", "nested shell invocation ('zsh')",
     "Nested shell execution via 'zsh' is blocked to prevent policy bypass.",
     "Execute the target binary or script directly without invoking zsh."),
    (r"(?<![-./])\beval\b", "dynamic code evaluation ('eval')",
     "Dynamic evaluation via 'eval' is blocked to prevent arbitrary code execution.",
     "Execute static commands directly without eval."),
    (r"(?<![-./])\benv\b", "environment override wrapper ('env')",
     "Arbitrary environment overrides via 'env' are restricted.",
     "Execute the target command directly without environment wrapper.")
]

def parse_shell_command(command: str) -> List[Tuple[str, List[str]]]:
    """
    Parses a shell command into a list of (base_executable, [args]).
    Raises CommandParserError if dangerous constructs are detected with actionable remediation.
    """
    if not command or not command.strip():
        return []

    for pattern, name, reason, remedy in BLOCKED_CONSTRUCT_DETAILS:
        if re.search(pattern, command):
            err_msg = f"Command contains blocked construct {name}: {reason} Remedy: {remedy}"
            raise CommandParserError(err_msg, construct=name, reason=reason, remedy=remedy)
            
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
