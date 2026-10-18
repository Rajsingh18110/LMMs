import json
import os
from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table

DEFAULT_PACKAGES = {
    "runtimes": {
        "llama-cpp": {"status": "installed", "description": "Llama.cpp Python native bindings with CUDA acceleration"},
        "pytorch": {"status": "installed", "description": "Universal PyTorch execution backend"},
        "vllm": {"status": "available", "description": "High-throughput vLLM serving engine"}
    },
    "providers": {
        "huggingface": {"status": "installed", "description": "Hugging Face Hub model provider & GGUF repository"},
        "lmstudio": {"status": "available", "description": "LM Studio local API integration provider"},
        "ollama": {"status": "available", "description": "Ollama local model bridge provider"}
    },
    "tools": {
        "terminal": {"status": "installed", "description": "Local shell execution sandbox tool"},
        "browser": {"status": "installed", "description": "Headless browser web inspection tool"},
        "files": {"status": "installed", "description": "Local filesystem access and file editor tool"},
        "web_search": {"status": "installed", "description": "Live web search & knowledge extraction tool"},
        "wikipedia": {"status": "available", "description": "Wikipedia knowledge retrieval tool"},
        "github": {"status": "available", "description": "GitHub API repository analysis tool"}
    }
}


class PackageManager:
    """Manages modular packages for runtimes, providers, and tools."""

    def __init__(self):
        self.packages_file = os.path.expanduser("~/.lmms/packages.json")
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.packages_file):
            try:
                with open(self.packages_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        os.makedirs(os.path.dirname(self.packages_file), exist_ok=True)
        self._save(DEFAULT_PACKAGES)
        return DEFAULT_PACKAGES

    def _save(self, data: Dict[str, Any]) -> None:
        with open(self.packages_file, "w") as f:
            json.dump(data, f, indent=2)

    def list_packages(self) -> None:
        c = Console()
        table = Table(title="LMMs Modular Package Manager")
        table.add_column("Type", style="cyan")
        table.add_column("Package Name", style="bold white")
        table.add_column("Status", style="green")
        table.add_column("Description", style="dim")

        for category, pkgs in self.data.items():
            cat_name = category.rstrip("s").capitalize()
            for name, details in pkgs.items():
                status = details.get("status", "available")
                status_styled = "[bold green]installed[/bold green]" if status == "installed" else "[yellow]available[/yellow]"
                table.add_row(cat_name, name, status_styled, details.get("description", ""))

        c.print(table)

    def install(self, pkg_type: str, name: str) -> None:
        c = Console()
        category = f"{pkg_type.lower()}s"
        if category not in self.data:
            c.print(f"[bold red]✖ Invalid package type '{pkg_type}'.[/bold red] Choices: runtime, provider, tool")
            return

        name = name.lower()
        if name in self.data[category] and self.data[category][name].get("status") == "installed":
            c.print(f"[yellow]Package '{name}' is already installed.[/yellow]")
            return

        c.print(f"[cyan]Installing {pkg_type} package '{name}'...[/cyan]")
        if name not in self.data[category]:
            self.data[category][name] = {
                "status": "installed",
                "description": f"Custom {pkg_type} package: {name}"
            }
        else:
            self.data[category][name]["status"] = "installed"

        self._save(self.data)
        c.print(f"[bold green]✔ Successfully installed and registered {pkg_type} '{name}'.[/bold green]")

    def remove(self, name_or_type: str, name: Optional[str] = None) -> None:
        c = Console()
        if name:
            category = f"{name_or_type.lower()}s"
            pkg_name = name.lower()
            if category in self.data and pkg_name in self.data[category]:
                self.data[category][pkg_name]["status"] = "available"
                self._save(self.data)
                c.print(f"[bold green]✔ Package '{pkg_name}' ({name_or_type}) removed.[/bold green]")
                return
            c.print(f"[red]Package '{pkg_name}' of type '{name_or_type}' not found.[/red]")
        else:
            pkg_name = name_or_type.lower()
            found = False
            for category in self.data:
                if pkg_name in self.data[category]:
                    self.data[category][pkg_name]["status"] = "available"
                    found = True
            if found:
                self._save(self.data)
                c.print(f"[bold green]✔ Package '{pkg_name}' removed.[/bold green]")
            else:
                c.print(f"[red]Package '{pkg_name}' not found.[/red]")
