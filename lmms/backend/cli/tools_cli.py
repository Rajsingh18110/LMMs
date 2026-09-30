from rich.console import Console
from rich.table import Table
from lmms.backend.security.tool_registry import registry

console = Console()

def cmd_tools_status():
    table = Table(title="LMMs Tool Registry Status")
    table.add_column("Tool", style="cyan")
    table.add_column("Category", style="magenta")
    table.add_column("Risk", style="red")
    table.add_column("Network", style="yellow")
    table.add_column("Target Auth Req", style="blue")
    
    for tool in sorted(registry.list_tools(), key=lambda t: (t.category, t.name)):
        table.add_row(
            tool.name,
            tool.category,
            tool.risk_level,
            "Yes" if tool.requires_network else "No",
            "Yes" if tool.requires_target_authorization else "No"
        )
        
    console.print(table)
