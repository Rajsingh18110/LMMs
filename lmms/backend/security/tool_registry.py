from typing import Dict, Optional, List
from lmms.backend.security.models import ToolDefinition

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self._aliases: Dict[str, str] = {
            "file_read": "files.read",
            "file.read": "files.read",
            "read_file": "files.read",
            "view_file": "files.read",
            "file_write": "files.write",
            "file.write": "files.write",
            "write_file": "files.write",
            "write_to_file": "files.write",
            "view_file_outline": "files.view_file_outline",
            "read_file_lines": "files.read_file_lines",
            "replace_in_file": "files.replace_in_file",
            "search_in_files": "files.search_in_files",
            "grep_search": "files.search_in_files",
            "list_folder": "files.list_folder",
            "list_dir": "files.list_folder",
            "files.list": "files.list_folder",
            "create_folder": "files.create_folder",
            "run_command": "terminal.run",
            "bash": "terminal.run",
            "sh": "terminal.run",
        }
        
    def register(self, definition: ToolDefinition) -> None:
        self.tools[definition.name] = definition
        
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        if not name:
            return None
            
        # 1. Direct match
        if name in self.tools:
            return self.tools[name]
            
        # 2. Check alias map
        if name in self._aliases:
            target = self._aliases[name]
            if target in self.tools:
                return self.tools[target]
                
        # 3. Normalized name check (convert _ to . or vice versa)
        norm_dot = name.replace("_", ".")
        if norm_dot in self.tools:
            return self.tools[norm_dot]
        if norm_dot in self._aliases and self._aliases[norm_dot] in self.tools:
            return self.tools[self._aliases[norm_dot]]

        norm_under = name.replace(".", "_")
        if norm_under in self.tools:
            return self.tools[norm_under]
            
        # 4. Dynamic Bridge to Orchestration Registry
        try:
            from lmms.backend.orchestration.registry import ToolRegistry as OrchRegistry
            orch = OrchRegistry()
            orch_tool = orch.get(name)
            if orch_tool:
                rl = orch_tool.metadata.risk_level
                is_net = "network" in orch_tool.metadata.tags or orch_tool.category == "search"
                dyn_def = ToolDefinition(
                    name=name,
                    category=orch_tool.category,
                    risk_level=rl,
                    requires_network=is_net
                )
                self.tools[name] = dyn_def
                return dyn_def
        except Exception:
            pass

        return None
        
    def list_tools(self) -> List[ToolDefinition]:
        return list(self.tools.values())

registry = ToolRegistry()

def register_default_tools():
    # Filesystem shell commands
    for t in ["cat", "head", "tail", "less", "find", "grep", "sed", "awk", "file", "stat", "du", "df", "ls", "pwd"]:
        registry.register(ToolDefinition(name=t, category="filesystem", risk_level="safe"))
        
    for t in ["cp", "mv", "mkdir", "touch", "rm"]:
        rl = "high" if t == "rm" else "low"
        registry.register(ToolDefinition(name=t, category="filesystem", risk_level=rl, destructive=(t=="rm")))

    # Process/System & Shell Builtins
    for t in [
        "ps", "top", "uname", "whoami", "id", "env", "free", "uptime", "journalctl",
        "echo", "printf", "which", "whereis", "type", "true", "false", "test",
        "clear", "sleep", "wc", "sort", "uniq", "cut", "tr", "tee", "xargs",
        "tar", "gzip", "gunzip", "zip", "unzip", "bzip2", "xz", "dirname", "basename",
        "readlink", "realpath", "seq", "date", "cal", "diff", "patch", "export", "source"
    ]:
        registry.register(ToolDefinition(name=t, category="system", risk_level="safe"))
        
    for t in ["kill", "pkill", "systemctl"]:
        registry.register(ToolDefinition(name=t, category="system", risk_level="medium", destructive=True))

    # Network
    for t in ["ping", "ss", "ip", "dig", "host", "traceroute", "netstat", "arp", "route"]:
        registry.register(ToolDefinition(name=t, category="network", risk_level="low", requires_network=True))
        
    for t in ["curl", "wget", "nmap", "nc", "netcat", "tcpdump"]:
        registry.register(ToolDefinition(name=t, category="network", risk_level="medium", requires_network=True, requires_target_authorization=True))

    # Developer
    for t in [
        "git", "python", "python3", "pip", "pip3", "node", "npm", "npx", "yarn", "pnpm", "bun", "deno",
        "flutter", "dart", "java", "javac", "gradle", "mvn", "cargo", "rustc", "gcc", "g++", "make", "cmake", "go", "php", "ruby"
    ]:
        registry.register(ToolDefinition(name=t, category="developer", risk_level="low"))

    # Containers
    for t in ["docker", "docker-compose", "kubectl", "helm"]:
        registry.register(ToolDefinition(name=t, category="container", risk_level="medium"))
        
    # Security/Defensive
    for t in ["sha256sum", "sha512sum", "md5sum", "openssl", "gpg", "base64", "xxd"]:
        registry.register(ToolDefinition(name=t, category="security", risk_level="safe"))
        
    # Prohibited/Destructive
    for t in ["sqlmap", "metasploit", "msfconsole", "msfvenom", "hydra", "medusa", "ncrack", "john", "hashcat", "dd", "mkfs", "fdisk"]:
        registry.register(ToolDefinition(name=t, category="security_offensive", risk_level="critical", destructive=True, requires_confirmation=True, requires_network=True, requires_target_authorization=True))

    # Internal LMMs tools & Surgical File Tools
    registry.register(ToolDefinition(name="terminal.run", category="internal", risk_level="medium"))
    registry.register(ToolDefinition(name="run_command", category="internal", risk_level="medium"))
    
    # File tools (all aliases registered so no schema mismatch can occur)
    registry.register(ToolDefinition(name="files.read", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="file.read", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="view_file", category="internal", risk_level="safe"))
    
    registry.register(ToolDefinition(name="files.write", category="internal", risk_level="medium"))
    registry.register(ToolDefinition(name="file.write", category="internal", risk_level="medium"))
    registry.register(ToolDefinition(name="write_to_file", category="internal", risk_level="medium"))

    registry.register(ToolDefinition(name="files.view_file_outline", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="view_file_outline", category="internal", risk_level="safe"))
    
    registry.register(ToolDefinition(name="files.read_file_lines", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="read_file_lines", category="internal", risk_level="safe"))
    
    registry.register(ToolDefinition(name="files.replace_in_file", category="internal", risk_level="medium"))
    registry.register(ToolDefinition(name="replace_in_file", category="internal", risk_level="medium"))
    
    registry.register(ToolDefinition(name="files.search_in_files", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="search_in_files", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="grep_search", category="internal", risk_level="safe"))

    registry.register(ToolDefinition(name="files.list_folder", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="list_folder", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="list_dir", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="files.list", category="internal", risk_level="safe"))

    registry.register(ToolDefinition(name="files.create_folder", category="internal", risk_level="low"))
    registry.register(ToolDefinition(name="create_folder", category="internal", risk_level="low"))
    registry.register(ToolDefinition(name="files.delete", category="internal", risk_level="high", destructive=True, requires_confirmation=True))
    registry.register(ToolDefinition(name="delete", category="internal", risk_level="high", destructive=True, requires_confirmation=True))

    # Browser
    registry.register(ToolDefinition(name="browser.open_url", category="internal", risk_level="medium", requires_network=True))
    registry.register(ToolDefinition(name="browser.click_element", category="internal", risk_level="medium", requires_network=True))
    registry.register(ToolDefinition(name="browser.fill_form", category="internal", risk_level="medium", requires_network=True))
    registry.register(ToolDefinition(name="browser.type", category="internal", risk_level="medium", requires_network=True))
    registry.register(ToolDefinition(name="browser.type_text", category="internal", risk_level="medium", requires_network=True))
    registry.register(ToolDefinition(name="browser.press_key", category="internal", risk_level="low", requires_network=True))
    registry.register(ToolDefinition(name="browser.get_interactive_dom", category="internal", risk_level="safe", requires_network=True))
    registry.register(ToolDefinition(name="browser.scrape", category="internal", risk_level="safe", requires_network=True))
    registry.register(ToolDefinition(name="browser.scrape_live", category="internal", risk_level="safe", requires_network=True))
    registry.register(ToolDefinition(name="browser.crawl_url", category="internal", risk_level="safe", requires_network=True))
    registry.register(ToolDefinition(name="browser.crawl", category="internal", risk_level="safe", requires_network=True))
    registry.register(ToolDefinition(name="browser.screenshot", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="browser.scroll", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="browser.open_authenticated", category="internal", risk_level="high", requires_network=True, requires_confirmation=True))
    
    # Search, RAG & System
    registry.register(ToolDefinition(name="web_search", category="internal", risk_level="safe", requires_network=True))
    registry.register(ToolDefinition(name="vector_db.search", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="rag.search", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="rag.crawl_url", category="internal", risk_level="safe", requires_network=True))
    registry.register(ToolDefinition(name="rag.ingest", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="security.generate_report", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="app.launch", category="system", risk_level="low"))
    registry.register(ToolDefinition(name="os.launch_app", category="system", risk_level="low"))
    registry.register(ToolDefinition(name="app.list", category="system", risk_level="safe"))
    registry.register(ToolDefinition(name="app.close", category="system", risk_level="low"))
    registry.register(ToolDefinition(name="message.send", category="network", risk_level="low", requires_network=True))
    registry.register(ToolDefinition(name="telegram.send_message", category="network", risk_level="low", requires_network=True))
    registry.register(ToolDefinition(name="load_capability", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="retrieve_archive", category="internal", risk_level="safe"))

# Initialize default tools
register_default_tools()
