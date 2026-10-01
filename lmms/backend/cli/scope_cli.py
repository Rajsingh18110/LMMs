import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from lmms.backend.security.scope import get_scope_file, init_default_scope, load_scope, save_scope

console = Console()

def cmd_scope_init(workspace: str):
    if not workspace or workspace == "None":
        console.print("[red]No active workspace to initialize scope.[/red]")
        return
        
    scope_file = get_scope_file(workspace)
    if os.path.exists(scope_file):
        ans = Prompt.ask(f"[yellow]Scope file already exists at {scope_file}. Overwrite? (y/n)[/yellow]").lower()
        if ans != "y":
            return
            
    scope = init_default_scope()
    scope["engagement_name"] = Prompt.ask("Engagement Name", default=scope["engagement_name"])
    
    targets_str = Prompt.ask("Authorized Targets (comma separated IPs, CIDRs, or Domains)", default="")
    if targets_str:
        scope["authorized_targets"] = [t.strip() for t in targets_str.split(",") if t.strip()]
        
    tools_str = Prompt.ask("Allowed Security Tools (comma separated)", default=",".join(scope["allowed_tools"]))
    if tools_str:
        scope["allowed_tools"] = [t.strip() for t in tools_str.split(",") if t.strip()]
        
    net_allowed = Prompt.ask("Allow Network Actions? (y/n)", default="n").lower()
    scope["network_actions_allowed"] = (net_allowed == "y")
    
    if save_scope(workspace, scope):
        console.print(f"[bold green]Scope initialized and saved to {scope_file}[/bold green]")
    else:
        console.print("[bold red]Failed to save scope.[/bold red]")

def cmd_scope_status(workspace: str):
    if not workspace or workspace == "None":
        console.print("[red]No active workspace.[/red]")
        return
        
    scope = load_scope(workspace)
    if not scope:
        console.print(Panel("[yellow]No scope defined for this workspace. Defaulting to safe offline mode.[/yellow]", title="Scope Status"))
        return
        
    table = Table(title="Authorized Scope Details", border_style="cyan")
    table.add_column("Property", style="bold cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Engagement Name", scope.get("engagement_name", "N/A"))
    table.add_row("Status", scope.get("status", "N/A"))
    table.add_row("Network Actions", str(scope.get("network_actions_allowed", False)))
    
    targets = scope.get("authorized_targets", [])
    table.add_row("Authorized Targets", ", ".join(targets) if targets else "[yellow]None (Offline Only)[/yellow]")
    
    tools = scope.get("allowed_tools", [])
    table.add_row("Allowed Tools", ", ".join(tools) if tools else "None")
    
    table.add_row("Evidence Dir", scope.get("evidence_directory", "N/A"))
    
    console.print(table)

def cmd_scope_validate(workspace: str):
    if not workspace or workspace == "None":
        console.print("[red]No active workspace.[/red]")
        return
        
    scope = load_scope(workspace)
    if not scope:
        console.print("[yellow]No scope to validate. System is in safe mode.[/yellow]")
        return
        
    errors = []
    if not isinstance(scope.get("authorized_targets"), list):
        errors.append("'authorized_targets' must be a list.")
    if not isinstance(scope.get("allowed_tools"), list):
        errors.append("'allowed_tools' must be a list.")
        
    import ipaddress
    for target in scope.get("authorized_targets", []):
        if "/" in target:
            try:
                ipaddress.ip_network(target, strict=False)
            except ValueError:
                errors.append(f"Invalid CIDR format in targets: {target}")
                
    if errors:
        for err in errors:
            console.print(f"[red]Error:[/red] {err}")
        console.print("[bold red]Scope validation failed.[/bold red]")
    else:
        console.print("[bold green]Scope validation passed. Scope is well-formed.[/bold green]")

def cmd_scope_activate(workspace: str):
    scope = load_scope(workspace)
    if not scope:
        console.print("[red]No scope found. Use /scope init first.[/red]")
        return
    scope["status"] = "active"
    save_scope(workspace, scope)
    console.print("[bold green]Scope activated successfully.[/bold green]")
    
def cmd_scope_complete(workspace: str):
    scope = load_scope(workspace)
    if not scope:
        console.print("[red]No scope found.[/red]")
        return
    scope["status"] = "completed"
    save_scope(workspace, scope)
    console.print("[bold green]Scope marked as completed.[/bold green]")
    
def cmd_scope_reset(workspace: str):
    import os
    from lmms.backend.security.scope import get_scope_file
    path = get_scope_file(workspace)
    if os.path.exists(path):
        os.remove(path)
        console.print("[bold green]Scope file deleted.[/bold green]")
    else:
        console.print("[yellow]No scope file found to delete.[/yellow]")
        
def cmd_scope_export(workspace: str, dest_path: str):
    import json
    scope = load_scope(workspace)
    if not scope:
        console.print("[red]No scope found to export.[/red]")
        return
    with open(dest_path, "w") as f:
        json.dump(scope, f, indent=2)
    console.print(f"[bold green]Scope exported to {dest_path}.[/bold green]")
