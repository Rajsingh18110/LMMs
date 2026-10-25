from lmms.backend.security.models import ToolRequest, PermissionResult
from lmms.backend.security.tool_registry import registry
from lmms.backend.security.scope import load_scope, is_scope_active
from lmms.backend.security.target_validator import is_target_authorized
from lmms.backend.security.command_parser import parse_shell_command, extract_targets, CommandParserError
from lmms.backend.tools.boundaries import is_within_workspace
from lmms.cli.permission_prompt import is_command_always_allowed

class PermissionManager:
    
    def check_permission(self, request: ToolRequest) -> PermissionResult:
        # Check session or persistent allowlist first
        check_target = request.kwargs.get("command", "") or request.tool_name
        if is_command_always_allowed(check_target):
            return PermissionResult(allowed=True, reason="Always allowed by session or settings configuration.", risk_level="safe", requires_confirmation=False)

        tool_def = registry.get_tool(request.tool_name)
        
        # 1. Special handling for terminal commands
        if request.tool_name == "terminal.run":
            command = request.kwargs.get("command", "")
            from lmms_sandbox.runner import default_runner
            pol_res = default_runner.evaluate_command(command)
            is_managed = getattr(default_runner.policy, "is_managed", False)

            if pol_res.action.value == "deny":
                return PermissionResult(allowed=False, reason=f"BLOCKED by execpolicy: {pol_res.reason}", risk_level="critical")

            try:
                parsed_cmds = parse_shell_command(command)
            except CommandParserError as e:
                return PermissionResult(allowed=False, reason=str(e), risk_level="critical")

            if not parsed_cmds:
                return PermissionResult(allowed=False, reason="Empty command", risk_level="safe")

            inner_tool_name = parsed_cmds[0][0]
            inner_tool_def = registry.get_tool(inner_tool_name)
            if inner_tool_def:
                tool_def = inner_tool_def
            else:
                # If command is not in the basic registry, treat as unregistered tool
                # On low or medium-outside, will require confirmation
                from lmms.backend.security.models import ToolDefinition
                tool_def = ToolDefinition(name=inner_tool_name, category="system", risk_level="medium")

        # 2. If tool is still not resolved
        if not tool_def:
            return PermissionResult(allowed=False, reason=f"Tool '{request.tool_name}' is not registered.", risk_level="high")

        # Extract effective targets (paths, URLs, domains)
        targets = []
        if request.tool_name == "terminal.run":
            targets = extract_targets(request.kwargs.get("command", ""))
        elif request.tool_name in ["browser.open_url", "browser.click_element", "browser.fill_form", "browser.scrape", "web_search", "browser.open_authenticated"]:
            url = request.kwargs.get("url", "")
            if url:
                targets = extract_targets(url)
            else:
                query = request.kwargs.get("query", "")
                if query:
                    targets = extract_targets(query)

        # Global Denylist / Sensitive System Paths
        protected_paths = ["/.ssh/", "/etc/", "/boot/", "/.aws/", "/.config/gh/", "/.config/google-chrome/", "/.mozilla/", "/.lmms/config/"]
        target_path = request.kwargs.get("path", "")
        if not target_path and request.tool_name == "terminal.run":
            target_path = request.kwargs.get("command", "")
        if target_path:
            tp_check = target_path if target_path.endswith("/") else target_path + "/"
            for p_path in protected_paths:
                if p_path in tp_check:
                    return PermissionResult(allowed=True, reason=f"Accessing protected path {p_path} requires confirmation", risk_level="high", requires_confirmation=True)

        # Destructive tools (always require confirmation)
        if tool_def.destructive:
            return PermissionResult(allowed=True, reason="Destructive tool requires confirmation", risk_level="critical", requires_confirmation=True)

        # 3. Three-Tier Permission Enforcement (low, medium, full)
        perm_level = (request.permission_level or "medium").lower()

        # TIER 1: 'low' -> Every command / tool requires user confirmation
        if perm_level == "low":
            return PermissionResult(
                allowed=True,
                reason="Low permission tier requires explicit user approval for all operations.",
                risk_level="high",
                requires_confirmation=True
            )

        # TIER 2: 'medium' -> Autonomous inside workspace, confirmation required if leaving workspace
        if perm_level == "medium":
            eff_ws = request.workspace if request.workspace and request.workspace != "None" else os.getcwd()
            # Check for files.write outside workspace
            if request.tool_name in ("files.write", "file.write"):
                f_path = request.kwargs.get("path", "")
                if f_path and not is_within_workspace(f_path, eff_ws):
                    return PermissionResult(
                        allowed=True,
                        reason=f"Writing outside active workspace ('{eff_ws}') requires confirmation.",
                        risk_level="high",
                        requires_confirmation=True
                    )
            # Check terminal commands targeting outside paths
            elif request.tool_name == "terminal.run":
                cmd_str = request.kwargs.get("command", "")
                # If command references an explicit absolute path or path traversal outside workspace
                for word in cmd_str.split():
                    if word.startswith("/") and not is_within_workspace(word, eff_ws):
                        return PermissionResult(
                            allowed=True,
                            reason=f"Command references path '{word}' outside workspace ('{eff_ws}') and requires confirmation.",
                            risk_level="high",
                            requires_confirmation=True
                        )
                    if ".." in word:
                        resolved_cand = os.path.realpath(os.path.abspath(os.path.join(eff_ws, word)))
                        if not is_within_workspace(resolved_cand, eff_ws):
                            return PermissionResult(
                                allowed=True,
                                reason=f"Path traversal '{word}' reaches outside workspace and requires confirmation.",
                                risk_level="high",
                                requires_confirmation=True
                            )
            elif request.tool_name == "browser.open_authenticated":
                return PermissionResult(
                    allowed=True,
                    reason="Accessing authenticated browser session requires user confirmation.",
                    risk_level="high",
                    requires_confirmation=True
                )

        # TIER 3: 'full' -> Unconfined execution, only destructive operations ask (already checked above)
        if perm_level == "full":
            return PermissionResult(allowed=True, reason="Full permission tier allows unconfined execution.", risk_level="safe", requires_confirmation=False)

        # 4. Scope authorization checks (if active)
        scope = load_scope(request.workspace) or {}
        if not is_scope_active(scope):
            if tool_def.requires_target_authorization or tool_def.category == "security_offensive":
                return PermissionResult(allowed=False, reason="Scope is not active. Target-probing and offensive security tools are blocked in offline mode.", risk_level=tool_def.risk_level)
            if tool_def.requires_network and tool_def.category not in ("internal", "system", "developer") and perm_level == "low":
                return PermissionResult(allowed=False, reason="Scope is not active. External network access is restricted on low permission.", risk_level=tool_def.risk_level)
            return PermissionResult(allowed=True, reason="Tool allowed.", risk_level=tool_def.risk_level)
            
        if tool_def.category != "internal":
            if tool_def.name not in scope.get("allowed_tools", []):
                return PermissionResult(allowed=False, reason=f"Tool '{tool_def.name}' is not in scope's allowed_tools.", risk_level=tool_def.risk_level)
                
        if tool_def.requires_network:
            if not scope.get("network_actions_allowed", False):
                return PermissionResult(allowed=False, reason="Network actions are disabled in scope.", risk_level=tool_def.risk_level)
                
        if tool_def.requires_network or tool_def.requires_target_authorization:
            auth_targets = scope.get("authorized_targets", [])
            for t in targets:
                if not is_target_authorized(t, auth_targets):
                    return PermissionResult(allowed=False, reason=f"Target '{t}' is NOT in authorized_targets.", risk_level=tool_def.risk_level)
                    
        if tool_def.requires_confirmation:
            return PermissionResult(allowed=True, reason="Tool policy requires confirmation.", risk_level=tool_def.risk_level, requires_confirmation=True)

        return PermissionResult(allowed=True, reason="Allowed by policy.", risk_level=tool_def.risk_level)

permission_manager = PermissionManager()
