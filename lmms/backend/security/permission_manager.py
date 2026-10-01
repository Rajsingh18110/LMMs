from lmms.backend.security.models import ToolRequest, PermissionResult
from lmms.backend.security.tool_registry import registry
from lmms.backend.security.scope import load_scope, is_scope_active
from lmms.backend.security.target_validator import is_target_authorized
from lmms.backend.security.command_parser import parse_shell_command, extract_targets, CommandParserError

class PermissionManager:
    
    def check_permission(self, request: ToolRequest) -> PermissionResult:
        tool_def = registry.get_tool(request.tool_name)
        
        # 1. Is tool registered?
        if not tool_def:
            return PermissionResult(allowed=False, reason=f"Tool '{request.tool_name}' is not registered.", risk_level="high")
            
        # Special case for terminal.run where we need to parse the inner command
        if request.tool_name == "terminal.run":
            command = request.kwargs.get("command", "")
            try:
                parsed_cmds = parse_shell_command(command)
            except CommandParserError as e:
                return PermissionResult(allowed=False, reason=str(e), risk_level="critical")
                
            if not parsed_cmds:
                return PermissionResult(allowed=False, reason="Empty command", risk_level="safe")
                
            inner_tool_name = parsed_cmds[0][0]
            inner_tool_def = registry.get_tool(inner_tool_name)
            if not inner_tool_def:
                # User requested MAXIMUM POWER: allow any unrecognized command (like cd, pwd, man) as a valid terminal tool.
                from lmms.backend.security.tool_registry import ToolDefinition
                inner_tool_def = ToolDefinition(name=inner_tool_name, category="internal", risk_level="medium")
                
            tool_def = inner_tool_def

        # Extract effective targets (especially for network tools)
        targets = []
        if request.tool_name == "terminal.run":
            targets = extract_targets(request.kwargs.get("command", ""))
        elif request.tool_name in ["browser.open_url", "browser.click_element", "browser.fill_form", "browser.scrape", "web_search", "browser.open_authenticated"]:
            # extract domain from URL
            url = request.kwargs.get("url", "")
            if url:
                targets = extract_targets(url)
            else:
                query = request.kwargs.get("query", "")
                if query:
                    # Treat search query as target if it contains domain? Overkill for web search, but let's be safe
                    targets = extract_targets(query)
                    
        # Global Denylist of Paths (like in the original code)
        protected_paths = ["/.ssh/", "/etc/", "/boot/", "/.aws/", "/.config/gh/", "/.config/google-chrome/", "/.mozilla/", "/.lmms/config/"]
        target_path = request.kwargs.get("path", "")
        if not target_path and request.tool_name == "terminal.run":
            target_path = request.kwargs.get("command", "")
        if target_path:
            tp_check = target_path if target_path.endswith("/") else target_path + "/"
            for p_path in protected_paths:
                if p_path in tp_check:
                    # Requires confirmation
                    return PermissionResult(allowed=True, reason=f"Accessing protected path {p_path} requires confirmation", risk_level="high", requires_confirmation=True)

        # Destructive tools
        if tool_def.destructive:
            return PermissionResult(allowed=True, reason="Destructive tool requires confirmation", risk_level="critical", requires_confirmation=True)

        # 2. Is scope valid and active? (Only enforced in CYBER_MODE)
        if getattr(self, "CYBER_MODE", False):
            scope = load_scope(request.workspace)
            if not is_scope_active(scope):
                # If scope is not active, network actions and unauthorized targets are blocked.
                # Local filesystem tools are allowed (offline mode).
                if tool_def.requires_network or tool_def.requires_target_authorization:
                    # Except localhost? The spec says "Do not assume localhost is allowed unless explicitly authorized"
                    return PermissionResult(allowed=False, reason="[SYSTEM_DENY] Target or Network blocked because Scope is not active. STOP executing tools. Instruct the user to run EXACTLY '/scope init' in their CLI. Do NOT use terminal.run to run this command, as it is a CLI internal command.", risk_level=tool_def.risk_level)
                return PermissionResult(allowed=True, reason="Offline tool allowed in safe mode.", risk_level=tool_def.risk_level)
                
            # 3. Is the tool allowed by the scope?
            if tool_def.category != "internal":
                if tool_def.name not in scope.get("allowed_tools", []):
                    return PermissionResult(allowed=False, reason=f"Tool '{tool_def.name}' is not in scope's allowed_tools.", risk_level=tool_def.risk_level)
                    
            # 4. Is network access permitted?
            if tool_def.requires_network:
                if not scope.get("network_actions_allowed", False):
                    return PermissionResult(allowed=False, reason="[SYSTEM_DENY] Network actions are disabled in the active scope. Instruct the user to enable network actions through '/scope init' and then run '/scope activate'.", risk_level=tool_def.risk_level)
                    
            # 5. Is target authorized?
            if tool_def.requires_network or tool_def.requires_target_authorization:
                auth_targets = scope.get("authorized_targets", [])
                for t in targets:
                    if not is_target_authorized(t, auth_targets):
                        return PermissionResult(allowed=False, reason=f"[SYSTEM_DENY] Target '{t}' is NOT in authorized_targets. STOP executing tools. Instruct the user to run EXACTLY '/scope init' to add this domain/target. Do NOT run this via terminal.run.", risk_level=tool_def.risk_level)
                    
        requires_conf = tool_def.requires_confirmation

        # Enforce UI Permission Level (low/medium/full)
        perm_level = request.permission_level.lower()
        risk = tool_def.risk_level
        
        if perm_level == "low" and risk in ["medium", "high", "critical"]:
            requires_conf = True
        elif perm_level == "medium" and risk in ["high", "critical"]:
            requires_conf = True

        # Enforce Git subcommand confirmation
        if request.tool_name == "terminal.run":
            cmd_lower = request.kwargs.get("command", "").lower()
            if inner_tool_name == "git":
                for dangerous_subcmd in ["push", "commit", "reset", "clean", "checkout"]:
                    if dangerous_subcmd in cmd_lower.split():
                        requires_conf = True
                        break

        # 6. Human confirmation
        if requires_conf:
            return PermissionResult(allowed=True, reason=f"Tool policy or permission level requires confirmation (risk: {risk}).", risk_level=risk, requires_confirmation=True)

        return PermissionResult(allowed=True, reason="Allowed by policy.", risk_level=risk)

permission_manager = PermissionManager()
