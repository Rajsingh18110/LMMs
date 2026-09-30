"""Small, non-mutating diagnostics used by the interactive CLI."""

import os
import platform
import shutil

import requests
from rich.table import Table


def engine_health(engine_url: str, request_get=requests.get) -> tuple[bool, str]:
    try:
        response = request_get(f"{engine_url}/webhook", timeout=2)
        if response.status_code == 200:
            return True, "reachable"
        return False, f"HTTP {response.status_code}"
    except Exception as exc:
        return False, str(exc)


def collect_status(workspace: str, engine_url: str, request_get=requests.get) -> dict:
    engine_online, engine_detail = engine_health(engine_url, request_get)
    workspace_active = bool(workspace and workspace != "None")
    return {
        "engine": "online" if engine_online else "offline",
        "engine_detail": engine_detail,
        "workspace": workspace if workspace_active else "No active workspace",
        "workspace_exists": workspace_active and os.path.isdir(workspace),
        "git_repository": workspace_active and os.path.isdir(os.path.join(workspace, ".git")),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }


def collect_doctor_report(workspace: str, engine_url: str, request_get=requests.get) -> dict:
    status = collect_status(workspace, engine_url, request_get)
    tools = {name: bool(shutil.which(name)) for name in ("git", "python3", "nvidia-smi")}
    status["tools"] = tools
    status["healthy"] = status["engine"] == "online" and tools["git"] and tools["python3"]
    return status


def render_status(console, status: dict) -> None:
    table = Table(title="LMMs Status", header_style="bold cyan")
    table.add_column("Component")
    table.add_column("State")
    table.add_row("Engine", status["engine"].upper())
    table.add_row("Engine detail", status["engine_detail"])
    table.add_row("Workspace", status["workspace"])
    table.add_row("Git workspace", "yes" if status["git_repository"] else "no")
    table.add_row("Python", status["python"])
    console.print(table)


def render_doctor(console, report: dict) -> None:
    render_status(console, report)
    table = Table(title="LMMs Doctor", header_style="bold cyan")
    table.add_column("Check")
    table.add_column("Result")
    for tool, available in report["tools"].items():
        table.add_row(tool, "available" if available else "not found")
    table.add_row("Overall", "healthy" if report["healthy"] else "needs attention")
    console.print(table)
