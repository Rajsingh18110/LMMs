import subprocess
from lmms.backend.tools.core_tools.base import ToolResult

async def list_kali_tools(params: dict) -> ToolResult:
    """Runs dpkg -l filtered for Kali tools."""
    try:
        process = subprocess.run(
            ['dpkg', '-l'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        lines = process.stdout.split('\n')
        # Simple heuristic to find tools
        kali_tools = []
        for line in lines:
            if 'kali' in line.lower() and line.startswith('ii'):
                parts = line.split()
                if len(parts) >= 3:
                    kali_tools.append(parts[1])
        return ToolResult(
            tool_name="kali_list_tools",
            success=True,
            data={"kali_packages": kali_tools[:50]} # limit to 50 for brevity
        )
    except Exception as e:
        return ToolResult(tool_name="kali_list_tools", success=False, error=str(e), data=None)

async def tool_manual(params: dict) -> ToolResult:
    """Attempts tldr, falls back to man."""
    tool_name = params.get("tool_name")
    if not tool_name:
        return ToolResult(tool_name="kali_tool_help", success=False, error="Missing tool_name", data=None)
        
    try:
        # Try tldr first
        try:
            proc = subprocess.run(['tldr', tool_name], capture_output=True, text=True, timeout=5)
            if proc.returncode == 0:
                return ToolResult(tool_name="kali_tool_help", success=True, data={"tldr": proc.stdout.strip()})
        except FileNotFoundError:
            pass # tldr not installed
            
        # Fallback to man
        proc = subprocess.run(['man', tool_name], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            lines = proc.stdout.split('\n')[:50]
            return ToolResult(tool_name="kali_tool_help", success=True, data={"man": '\n'.join(lines).strip()})
            
        return ToolResult(tool_name="kali_tool_help", success=False, error=f"Manual not found for {tool_name}", data=None)
    except Exception as e:
        return ToolResult(tool_name="kali_tool_help", success=False, error=str(e), data=None)

async def kali_doc_search(params: dict) -> ToolResult:
    """Searches /usr/share/doc/"""
    query = params.get("query")
    if not query:
        return ToolResult(tool_name="kali_doc_search", success=False, error="Missing query", data=None)
        
    try:
        # Very simplistic search: find directories in /usr/share/doc/ matching query
        proc = subprocess.run(['find', '/usr/share/doc/', '-maxdepth', '1', '-iname', f"*{query}*"], capture_output=True, text=True)
        paths = proc.stdout.strip().split('\n')
        paths = [p for p in paths if p]
        
        return ToolResult(tool_name="kali_doc_search", success=True, data={"doc_paths": paths[:10]})
    except Exception as e:
        return ToolResult(tool_name="kali_doc_search", success=False, error=str(e), data=None)
