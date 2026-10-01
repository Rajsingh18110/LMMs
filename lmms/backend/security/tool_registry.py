from typing import Dict, Optional, List
from lmms.backend.security.models import ToolDefinition

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        
    def register(self, definition: ToolDefinition) -> None:
        self.tools[definition.name] = definition
        
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self.tools.get(name)
        
    def list_tools(self) -> List[ToolDefinition]:
        return list(self.tools.values())

registry = ToolRegistry()

def register_default_tools():
    # Filesystem
    for t in ["cat", "head", "tail", "less", "find", "grep", "sed", "awk", "file", "stat", "du", "df", "ls", "pwd", "echo", "printf", "tee", "cut", "sort", "uniq", "wc", "xargs", "jq", "tar", "unzip", "zip", "gzip"]:
        registry.register(ToolDefinition(name=t, category="filesystem", risk_level="safe"))
        
    for t in ["cp", "mv", "mkdir", "touch", "rm"]:
        # rm requires caution, but maybe not confirmation for basic usage, unless risk_level=high
        rl = "high" if t == "rm" else "low"
        registry.register(ToolDefinition(name=t, category="filesystem", risk_level=rl, destructive=(t=="rm")))

    # Process/System
    for t in ["ps", "top", "uname", "whoami", "id", "env", "free", "uptime", "journalctl"]:
        registry.register(ToolDefinition(name=t, category="system", risk_level="safe"))
        
    for t in ["kill", "pkill", "systemctl"]:
        registry.register(ToolDefinition(name=t, category="system", risk_level="medium", destructive=True))

    # Network
    for t in ["ping", "ss", "ip", "dig", "host", "traceroute", "netstat", "arp", "route"]:
        registry.register(ToolDefinition(name=t, category="network", risk_level="low", requires_network=True))
        
    for t in ["curl", "wget", "nmap", "nc", "netcat", "tcpdump"]:
        registry.register(ToolDefinition(name=t, category="network", risk_level="medium", requires_network=True, requires_target_authorization=True))

    # Developer
    for t in ["git", "python", "python3", "pip", "node", "npm", "npx", "cargo", "rustc", "gcc", "make", "cmake", "g++", "go", "php", "ruby"]:
        registry.register(ToolDefinition(name=t, category="developer", risk_level="low"))

    # Containers
    for t in ["docker", "docker-compose", "kubectl", "helm"]:
        registry.register(ToolDefinition(name=t, category="container", risk_level="medium"))
        
    # Security/Defensive
    for t in ["sha256sum", "sha512sum", "md5sum", "openssl", "gpg", "base64", "xxd"]:
        registry.register(ToolDefinition(name=t, category="security", risk_level="safe"))
        
    # Prohibited/Destructive (Always blocked or require explicit confirmation if permitted)
    for t in ["sqlmap", "metasploit", "msfconsole", "msfvenom", "hydra", "medusa", "ncrack", "john", "hashcat", "dd", "mkfs", "fdisk"]:
        registry.register(ToolDefinition(name=t, category="security_offensive", risk_level="critical", destructive=True, requires_confirmation=True, requires_network=True, requires_target_authorization=True))

    # Internal LMMs tools (for backwards compatibility)
    registry.register(ToolDefinition(name="terminal.run", category="internal", risk_level="medium"))
    registry.register(ToolDefinition(name="files.write", category="internal", risk_level="medium"))
    registry.register(ToolDefinition(name="files.read", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="files.diagnose", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="browser.open_url", category="internal", risk_level="medium", requires_network=True))
    registry.register(ToolDefinition(name="browser.click_element", category="internal", risk_level="high", requires_network=True, requires_confirmation=True))
    registry.register(ToolDefinition(name="browser.fill_form", category="internal", risk_level="high", requires_network=True, requires_confirmation=True))
    registry.register(ToolDefinition(name="browser.scrape", category="internal", risk_level="safe", requires_network=True))
    registry.register(ToolDefinition(name="browser.scroll", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="browser.open_authenticated", category="internal", risk_level="high", requires_network=True, requires_confirmation=True))
    registry.register(ToolDefinition(name="web_search", category="internal", risk_level="safe", requires_network=True))
    registry.register(ToolDefinition(name="vector_db.search", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="security.generate_report", category="internal", risk_level="safe"))
    registry.register(ToolDefinition(name="memory.update_scratchpad", category="internal", risk_level="safe"))

# Initialize default tools
register_default_tools()
