import os
import json
from rich.console import Console
from rich.table import Table

class DownloadsManager:
    def __init__(self):
        self.downloads_file = os.path.expanduser("~/.lmms/logs/downloads.json")

    def show_downloads(self):
        c = Console()
        if not os.path.exists(self.downloads_file):
            c.print("[yellow]No active downloads.[/yellow]")
            return

        try:
            with open(self.downloads_file, "r") as f:
                state = json.load(f)
                
            if not state:
                c.print("[yellow]No active downloads.[/yellow]")
                return
                
            table = Table(title="LMMs Active Downloads")
            table.add_column("MODEL")
            table.add_column("REPO")
            table.add_column("FILE")
            table.add_column("STATUS")
            
            for model_name, info in state.items():
                status = info.get("status", "unknown")
                if status == "complete":
                    status = "[green]Complete[/green]"
                elif status == "downloading":
                    status = "[cyan]Downloading...[/cyan]"
                elif status == "failed":
                    status = f"[red]Failed[/red]: {info.get('error', '')}"
                
                table.add_row(model_name, info.get("repo", ""), info.get("file", ""), status)
                
            c.print(table)
        except Exception as e:
            c.print(f"[red]Error reading downloads status: {e}[/red]")
