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
                return PermissionResult(allowed=False, reason=f"Inner tool '{inner_tool_name}' is not registered.", risk_level="high")
                
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

        # 2. Is scope valid and active?
        scope = load_scope(request.workspace)
        if not is_scope_active(scope):
            # If scope is not active, network actions and unauthorized targets are blocked.
            # Local filesystem tools are allowed (offline mode).
            if tool_def.requires_network or tool_def.requires_target_authorization:
                # Except localhost? The spec says "Do not assume localhost is allowed unless explicitly authorized"
                return PermissionResult(allowed=False, reason=f"Scope is not active. Network/Target tools are blocked.", risk_level=tool_def.risk_level)
            return PermissionResult(allowed=True, reason="Offline tool allowed in safe mode.", risk_level=tool_def.risk_level)
            
        # 3. Is the tool allowed by the scope?
        # Note: we only strictly filter terminal shell tools (like nmap). 
        # For internal LMMs tools, they might not be in the scope's allowed_tools list explicitly,
        # but they still need to obey network/target rules.
        if tool_def.category != "internal":
            if tool_def.name not in scope.get("allowed_tools", []):
                return PermissionResult(allowed=False, reason=f"Tool '{tool_def.name}' is not in scope's allowed_tools.", risk_level=tool_def.risk_level)
                
        # 4. Is network access permitted?
        if tool_def.requires_network:
            if not scope.get("network_actions_allowed", False):
                return PermissionResult(allowed=False, reason="Network actions are disabled in scope.", risk_level=tool_def.risk_level)
                
        # 5. Is target authorized?
        if tool_def.requires_network or tool_def.requires_target_authorization:
            auth_targets = scope.get("authorized_targets", [])
            for t in targets:
                if not is_target_authorized(t, auth_targets):
                    return PermissionResult(allowed=False, reason=f"Target '{t}' is NOT in authorized_targets.", risk_level=tool_def.risk_level)
                    
        # 6. Human confirmation
        if tool_def.requires_confirmation:
            return PermissionResult(allowed=True, reason="Tool policy requires confirmation.", risk_level=tool_def.risk_level, requires_confirmation=True)

        return PermissionResult(allowed=True, reason="Allowed by policy.", risk_level=tool_def.risk_level)

permission_manager = PermissionManager()
