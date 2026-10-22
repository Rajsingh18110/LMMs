"""
lmms_sandbox.policy - Execution policy manager and rule engine.
Loads and enforces ~/.lmms/execpolicy.toml with allow, deny, and ask actions.
"""

import os
import re
import tomllib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple


class PolicyAction(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass
class PolicyResult:
    action: PolicyAction
    reason: str
    rule_name: str = ""
    pattern: str = ""


DEFAULT_POLICY_TOML = """# ~/.lmms/execpolicy.toml
# Execution policy configuration for LMMs sandbox & command execution.

[policy]
# Default action when no specific rule matches: "allow", "ask", or "deny"
default_action = "ask"
# Sandbox mode enforcement: "auto", "always", or "never"
sandbox_mode = "auto"
# Automatically isolate network in sandboxed commands unless explicitly permitted
deny_network = true

# Explicitly allowed safe inspection / read-only commands
[[rules]]
name = "safe_read_commands"
action = "allow"
patterns = [
    "^ls(\\\\s|$)",
    "^dir(\\\\s|$)",
    "^pwd$",
    "^echo(\\\\s|$)",
    "^cat(\\\\s|$)",
    "^grep(\\\\s|$)",
    "^find(\\\\s|$)",
    "^head(\\\\s|$)",
    "^tail(\\\\s|$)",
    "^wc(\\\\s|$)",
    "^which(\\\\s|$)",
    "^whereis(\\\\s|$)",
    "^git\\\\s+(status|diff|log|branch|show|rev-parse)(\\\\s|$)",
    "^python3?\\\\s+--version$",
    "^python3?\\\\s+-m\\\\s+unittest(\\\\s|$)",
    "^pytest(\\\\s|$)",
    "^node\\\\s+--version$",
    "^whoami$",
    "^id(\\\\s|$)",
    "^uname(\\\\s|$)",
]

# Dangerously destructive commands that are ALWAYS denied
[[rules]]
name = "dangerous_primitives"
action = "deny"
patterns = [
    "rm\\\\s+-rf\\\\s+/[\\\\s$]*",
    "rm\\\\s+-rf\\\\s+~[\\\\s$]*",
    "mkfs",
    "dd\\\\s+if=",
    "chmod\\\\s+777\\\\s+/",
    ":\\\\(\\\\)\\\\s*\\\\{\\\\s*:\\\\|:&\\\\s*\\\\};:",
    "shutdown(\\\\s|$)",
    "reboot(\\\\s|$)",
    "init\\\\s+0",
    "(curl|wget).*\\\\|\\\\s*(sudo\\\\s+)?(ba)?sh",
]

# Sensitive operations that require explicit user confirmation ("ask")
[[rules]]
name = "sensitive_operations"
action = "ask"
patterns = [
    "^git\\\\s+(push|commit|reset|checkout|clean|rebase)(\\\\s|$)",
    "^npm\\\\s+(install|publish|i)(\\\\s|$)",
    "^pip3?\\\\s+install(\\\\s|$)",
    "^sudo(\\\\s|$)",
    "apt(-get)?\\\\s+(install|remove|purge)(\\\\s|$)",
    "^rm(\\\\s|$)",
    "^mv(\\\\s|$)",
    "^chmod(\\\\s|$)",
    "^chown(\\\\s|$)",
    "^make\\\\s+install(\\\\s|$)",
    "^curl(\\\\s|$)",
    "^wget(\\\\s|$)",
]

# [filesystem]
# Deny-by-default home directory isolation
isolate_home = true

# Explicit allowlisted paths under $HOME mounted read-only (e.g. local model caches)
allowlisted_home_paths = [
    "~/.cache/huggingface",
    "~/.lmms/models",
]

# Sensitive directories masked with an empty tmpfs in sandbox
hidden_paths = [
    "~/.ssh",
    "~/.gnupg",
    "~/.aws",
    "~/.config/gh",
    "~/.lmms/config",
]

# Additional host paths mounted read-only (not needed when root is already mounted read-only)
read_only_paths = []

# Writable paths (workspace is always appended automatically)
writable_paths = []
"""


class ExecPolicy:
    """Manages command execution policies and evaluates commands against rules."""

    def __init__(self, config_path: Optional[str] = None, managed_path: Optional[str] = None):
        if config_path:
            self.config_path = Path(os.path.expanduser(config_path))
        else:
            self.config_path = Path(os.path.expanduser("~/.lmms/execpolicy.toml"))

        env_managed = os.environ.get("LMMS_MANAGED_POLICY")
        if managed_path:
            self.managed_path: Optional[Path] = Path(os.path.expanduser(managed_path))
        elif env_managed:
            self.managed_path = Path(os.path.expanduser(env_managed))
        elif os.path.exists("/etc/lmms/execpolicy.toml"):
            self.managed_path = Path("/etc/lmms/execpolicy.toml")
        else:
            self.managed_path = None

        self.default_action = PolicyAction.ASK
        self.sandbox_mode = "auto"
        self.deny_network = True
        self.isolate_home = True
        self.allowlisted_home_paths: List[str] = ["~/.cache/huggingface", "~/.lmms/models"]
        self.rules: List[dict] = []
        self.hidden_paths: List[str] = []
        self.read_only_paths: List[str] = []
        self.writable_paths: List[str] = []
        self.is_managed: bool = False
        self.managed_source: Optional[str] = None

        self._load_or_create()

    def _load_or_create(self) -> None:
        """Loads existing configuration or creates the default execpolicy.toml."""
        if not self.config_path.exists():
            try:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                self.config_path.write_text(DEFAULT_POLICY_TOML, encoding="utf-8")
            except OSError:
                pass

        content = DEFAULT_POLICY_TOML
        if self.config_path.exists():
            try:
                content = self.config_path.read_text(encoding="utf-8")
            except OSError:
                pass

        try:
            data = tomllib.loads(content)
        except Exception:
            data = tomllib.loads(DEFAULT_POLICY_TOML)

        policy_section = data.get("policy", {})
        def_action_str = policy_section.get("default_action", "ask").lower()
        if def_action_str in ("allow", "ask", "deny"):
            self.default_action = PolicyAction(def_action_str)
        else:
            self.default_action = PolicyAction.ASK

        self.sandbox_mode = policy_section.get("sandbox_mode", "auto")
        self.deny_network = policy_section.get("deny_network", True)

        self.rules = data.get("rules", [])

        fs_section = data.get("filesystem", {})
        self.isolate_home = fs_section.get("isolate_home", True)
        self.allowlisted_home_paths = fs_section.get("allowlisted_home_paths", [
            "~/.cache/huggingface", "~/.lmms/models"
        ])
        self.hidden_paths = fs_section.get("hidden_paths", [
            "~/.ssh", "~/.gnupg", "~/.aws", "~/.config/gh", "~/.lmms/config"
        ])
        self.read_only_paths = fs_section.get("read_only_paths", [])
        self.writable_paths = fs_section.get("writable_paths", [])

        # Apply enterprise managed overrides if managed policy exists
        if self.managed_path and self.managed_path.exists():
            try:
                m_content = self.managed_path.read_text(encoding="utf-8")
                m_data = tomllib.loads(m_content)
                self.is_managed = True
                self.managed_source = str(self.managed_path)

                m_policy = m_data.get("policy", {})
                if "default_action" in m_policy:
                    m_def = str(m_policy["default_action"]).lower()
                    if m_def in ("allow", "ask", "deny"):
                        self.default_action = PolicyAction(m_def)

                if "sandbox_mode" in m_policy:
                    self.sandbox_mode = m_policy["sandbox_mode"]

                if "deny_network" in m_policy:
                    self.deny_network = bool(m_policy["deny_network"])

                # Managed rules take precedence ahead of user rules
                if "rules" in m_data and isinstance(m_data["rules"], list):
                    self.rules = m_data["rules"] + self.rules

                m_fs = m_data.get("filesystem", {})
                if "writable_paths" in m_fs:
                    self.writable_paths = m_fs["writable_paths"]
                if "hidden_paths" in m_fs:
                    self.hidden_paths = list(set(self.hidden_paths + m_fs["hidden_paths"]))
            except Exception:
                pass

    def _extract_subcommands(self, cmd: str) -> List[str]:
        """Extracts subcommands from compound constructs (operators, $(), backticks, sh -c)."""
        subs: List[str] = []
        
        # 1. Backticks `...`
        for bt in re.findall(r'`([^`]+)`', cmd):
            if bt.strip():
                subs.append(bt.strip())
                
        # 2. Command substitution $(...)
        for sc in re.findall(r'\$\(([^)]+)\)', cmd):
            if sc.strip():
                subs.append(sc.strip())
                
        # 3. Shell subcommands sh -c "..." or bash -c '...'
        for sc in re.findall(r'(?:ba|z)?sh\s+-c\s+["\']([^"\']+)["\']', cmd):
            if sc.strip():
                subs.append(sc.strip())

        # 4. Split by top-level operators &&, ||, ;, |, &
        clean = re.sub(r'"[^"]*"|\'[^\']*\'', ' ', cmd)
        parts = re.split(r'&&|\|\||;|\||&', clean)
        if len(parts) > 1:
            for p in parts:
                p_str = p.strip()
                if p_str:
                    subs.append(p_str)
                    
        return subs

    def _evaluate_single(self, cmd: str) -> PolicyResult:
        """Evaluates a single atomic command against allow, deny, and ask rules."""
        # 1. First pass: Evaluate explicit DENY rules
        for rule in self.rules:
            if rule.get("action") == "deny":
                for pattern in rule.get("patterns", []):
                    try:
                        if re.search(pattern, cmd, re.IGNORECASE):
                            return PolicyResult(
                                action=PolicyAction.DENY,
                                reason=f"Command matches forbidden policy rule '{rule.get('name', 'unnamed')}' (pattern: {pattern})",
                                rule_name=rule.get("name", "deny"),
                                pattern=pattern,
                            )
                    except re.error:
                        continue

        # 2. Second pass: Evaluate explicit ALLOW rules
        for rule in self.rules:
            if rule.get("action") == "allow":
                for pattern in rule.get("patterns", []):
                    try:
                        if re.search(pattern, cmd):
                            return PolicyResult(
                                action=PolicyAction.ALLOW,
                                reason=f"Allowed by policy rule '{rule.get('name', 'unnamed')}'",
                                rule_name=rule.get("name", "allow"),
                                pattern=pattern,
                            )
                    except re.error:
                        continue

        # 3. Third pass: Evaluate explicit ASK rules
        for rule in self.rules:
            if rule.get("action") == "ask":
                for pattern in rule.get("patterns", []):
                    try:
                        if re.search(pattern, cmd):
                            return PolicyResult(
                                action=PolicyAction.ASK,
                                reason=f"Confirmation required by policy rule '{rule.get('name', 'unnamed')}'",
                                rule_name=rule.get("name", "ask"),
                                pattern=pattern,
                            )
                    except re.error:
                        continue

        # 4. Fallback to default action
        return PolicyResult(
            action=self.default_action,
            reason=f"No explicit rule matched; applying default policy ({self.default_action.value})",
            rule_name="default_fallback",
        )

    def evaluate(self, command: str) -> PolicyResult:
        """
        Evaluates a shell command string against configured policy rules.
        Handles atomic and compound commands (&&, ||, ;, |, $(), backticks, sh -c).
        """
        cmd = command.strip()
        if not cmd:
            return PolicyResult(
                action=PolicyAction.DENY,
                reason="Empty command is blocked.",
                rule_name="empty_command",
            )

        # 1. Immediate full-string DENY check (catches any destructive pattern anywhere)
        for rule in self.rules:
            if rule.get("action") == "deny":
                for pattern in rule.get("patterns", []):
                    try:
                        if re.search(pattern, cmd, re.IGNORECASE):
                            return PolicyResult(
                                action=PolicyAction.DENY,
                                reason=f"Command matches forbidden policy rule '{rule.get('name', 'unnamed')}' (pattern: {pattern})",
                                rule_name=rule.get("name", "deny"),
                                pattern=pattern,
                            )
                    except re.error:
                        continue

        # 2. Extract and evaluate compound subcommands
        subcommands = self._extract_subcommands(cmd)
        if subcommands:
            results = [self._evaluate_single(s) for s in subcommands]
            for r in results:
                if r.action == PolicyAction.DENY:
                    return r
            for r in results:
                if r.action == PolicyAction.ASK:
                    return r
            if all(r.action == PolicyAction.ALLOW for r in results):
                return PolicyResult(
                    action=PolicyAction.ALLOW,
                    reason="All compound subcommands allowed by policy",
                    rule_name="compound_allow",
                )

        # 3. Fallback to standard atomic command evaluation
        return self._evaluate_single(cmd)

    def get_resolved_hidden_paths(self) -> List[str]:
        """Returns expanded absolute paths for hidden directories that exist on the system."""
        resolved = []
        for p in self.hidden_paths:
            exp = os.path.abspath(os.path.expanduser(p))
            resolved.append(exp)
        return resolved


def validate_policy_dict(data: dict) -> Tuple[bool, Optional[str]]:
    """Validates policy dictionary structure, actions, and regex patterns."""
    if not isinstance(data, dict):
        return False, "Policy data must be a dictionary"

    if "default_action" in data:
        val = str(data["default_action"]).lower()
        if val not in ("allow", "ask", "deny"):
            return False, f"Invalid default_action '{val}'. Must be 'allow', 'ask', or 'deny'"

    if "sandbox_mode" in data:
        val = str(data["sandbox_mode"]).lower()
        if val not in ("auto", "always", "never"):
            return False, f"Invalid sandbox_mode '{val}'. Must be 'auto', 'always', or 'never'"

    if "rules" in data:
        if not isinstance(data["rules"], list):
            return False, "'rules' must be a list"
        for idx, rule in enumerate(data["rules"]):
            if not isinstance(rule, dict):
                return False, f"Rule at index {idx} must be a dictionary"
            action = rule.get("action", "")
            if action not in ("allow", "ask", "deny"):
                return False, f"Rule '{rule.get('name', idx)}' has invalid action '{action}'"
            patterns = rule.get("patterns", [])
            if not isinstance(patterns, list):
                return False, f"Rule '{rule.get('name', idx)}' patterns must be a list"
            for p in patterns:
                try:
                    re.compile(p)
                except re.error as e:
                    return False, f"Rule '{rule.get('name', idx)}' contains invalid regex pattern '{p}': {e}"

    for path_key in ("writable_paths", "read_only_paths", "hidden_paths"):
        if path_key in data:
            if not isinstance(data[path_key], list) or not all(isinstance(x, str) for x in data[path_key]):
                return False, f"'{path_key}' must be a list of strings"

    return True, None


def detect_weakening(old_policy: dict, new_policy: dict) -> List[str]:
    """
    Compares old policy against proposed new policy and returns a list of
    security downgrade reasons (weakening).
    """
    warnings: List[str] = []

    # 1. Deny rules removed
    old_deny_patterns = set()
    for rule in old_policy.get("rules", []):
        if rule.get("action") == "deny":
            for p in rule.get("patterns", []):
                old_deny_patterns.add(p)

    new_deny_patterns = set()
    for rule in new_policy.get("rules", []):
        if rule.get("action") == "deny":
            for p in rule.get("patterns", []):
                new_deny_patterns.add(p)

    removed_deny = old_deny_patterns - new_deny_patterns
    if removed_deny:
        warnings.append(f"Removes {len(removed_deny)} destructive command deny rule(s): {', '.join(list(removed_deny)[:3])}")

    # 2. Network denial relaxed
    old_net = old_policy.get("deny_network", True)
    new_net = new_policy.get("deny_network", True)
    if old_net and not new_net:
        warnings.append("Enables outbound network access inside sandboxed commands")

    # 3. Home isolation relaxed
    old_home = old_policy.get("isolate_home", True)
    new_home = new_policy.get("isolate_home", True)
    if old_home and not new_home:
        warnings.append("Disables home directory isolation (~)")

    # 4. Default action relaxed
    action_rank = {"deny": 0, "ask": 1, "allow": 2}
    old_act = str(old_policy.get("default_action", "ask")).lower()
    new_act = str(new_policy.get("default_action", "ask")).lower()
    if action_rank.get(new_act, 1) > action_rank.get(old_act, 1):
        warnings.append(f"Relaxes default fallback action from '{old_act}' to '{new_act}'")

    # 5. Writable paths widened to root or home
    broad_roots = {"/", "/etc", "/usr", "/bin", "/sbin", "/home", "~", "/var"}
    new_w = {os.path.normpath(os.path.expanduser(p)) for p in new_policy.get("writable_paths", [])}
    old_w = {os.path.normpath(os.path.expanduser(p)) for p in old_policy.get("writable_paths", [])}
    widened = (new_w - old_w)
    for p in widened:
        if p in broad_roots or p == os.path.expanduser("~") or p == "/":
            warnings.append(f"Widens writable paths to include broad system directory '{p}'")

    return warnings
