# Copyright 2026 LMMs Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Rich Terminal CLI Panel for AI Workflow Orchestration (/panel)."""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from .models import Workflow, WorkflowRun, NodeStatus
from .store import WorkflowStore
from .engine import WorkflowEngine


console = Console()


def render_dashboard(store: WorkflowStore, workspace: str) -> None:
    """Renders the top-level CLI workflow control panel."""
    console.print(
        Panel.fit(
            "[bold cyan]⚡ LMMs AI Workflow Engine[/bold cyan] [dim](Apache-2.0 Local-First Automation)[/dim]\n"
            f"[dim]Workspace:[/dim] [yellow]{workspace}[/yellow]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    # Check for pending approvals
    pending_run = store.get_pending_run_for_gate()
    if pending_run and pending_run.pending_approval:
        console.print(
            Panel(
                f"[bold yellow]⚠️ PENDING HUMAN APPROVAL[/bold yellow]\n"
                f"Run ID: [cyan]{pending_run.run_id}[/cyan] | Waiting at Gate: [bold red]{pending_run.pending_approval}[/bold red]\n"
                f"Run [bold green]/panel approve {pending_run.run_id}[/bold green] to resume or [bold red]/panel deny {pending_run.run_id}[/bold red] to abort.",
                border_style="yellow",
                box=box.HEAVY,
            )
        )

    # Workflows Table
    wfs = store.list_workflows(include_builtins=True)
    wf_table = Table(title="Available AI Workflows", box=box.SIMPLE_HEAVY)
    wf_table.add_column("Workflow ID", style="cyan", no_wrap=True)
    wf_table.add_column("Name", style="bold white")
    wf_table.add_column("Nodes", justify="center", style="green")
    wf_table.add_column("Source", style="dim")
    wf_table.add_column("Description", style="white")

    for w in wfs:
        wf_table.add_row(
            w["id"],
            w["name"],
            w["nodes_count"],
            w["source"],
            w["description"][:50] + ("..." if len(w["description"]) > 50 else ""),
        )

    console.print(wf_table)

    # Recent Runs Table
    runs = store.list_runs(limit=5)
    run_table = Table(title="Recent Workflow Executions", box=box.SIMPLE_HEAVY)
    run_table.add_column("Run ID", style="cyan", no_wrap=True)
    run_table.add_column("Workflow", style="bold white")
    run_table.add_column("Status", justify="center")
    run_table.add_column("Started", style="dim")
    run_table.add_column("Gate Pending", style="yellow")

    status_badges = {
        NodeStatus.SUCCESS.value: "[green]✔ SUCCESS[/green]",
        NodeStatus.FAILED.value: "[red]✖ FAILED[/red]",
        NodeStatus.RUNNING.value: "[blue]● RUNNING[/blue]",
        NodeStatus.WAITING_APPROVAL.value: "[yellow]⏸ WAITING GATE[/yellow]",
    }

    for r in runs:
        badge = status_badges.get(r["status"], f"[dim]{r['status']}[/dim]")
        run_table.add_row(
            r["run_id"],
            r["workflow_id"],
            badge,
            r["start_time"][:19].replace("T", " ") if r["start_time"] else "N/A",
            r["pending_approval"] if r["pending_approval"] != "none" else "-",
        )

    console.print(run_table)

    # Commands footer
    console.print(
        "[dim]Commands:[/dim] "
        "[cyan]/panel run <id>[/cyan]  •  "
        "[cyan]/panel view <run_id>[/cyan]  •  "
        "[cyan]/panel approve <run_id>[/cyan]  •  "
        "[cyan]/panel export <id>[/cyan]  •  "
        "[cyan]/panel list[/cyan]"
    )


def _run_coroutine_sync(coro):
    """Executes an async coroutine synchronously, handling active or absent event loops safely."""
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(lambda: asyncio.run(coro)).result()
    except RuntimeError:
        return asyncio.run(coro)


def run_workflow_sync(workflow_id: str, workspace: str, raw_params: Optional[str] = None) -> None:
    """Executes a workflow synchronously with live terminal progress reporting."""
    store = WorkflowStore()
    wf = store.get_workflow(workflow_id)
    if not wf:
        console.print(f"[bold red]Error:[/bold red] Workflow '{workflow_id}' not found.")
        return

    context = {"workspace": workspace}
    if raw_params:
        try:
            context.update(json.loads(raw_params))
        except Exception as e:
            console.print(f"[yellow]Warning: Could not parse params JSON ({e}), using default context.[/yellow]")

    console.print(
        Panel(
            f"[bold green]▶ Launching Workflow:[/bold green] [bold white]{wf.name}[/bold white] ({wf.id})\n"
            f"[dim]Total Nodes:[/dim] {len(wf.nodes)}  |  [dim]Edges:[/dim] {len(wf.edges)}",
            box=box.ROUNDED,
            border_style="green",
        )
    )

    engine = WorkflowEngine(workspace_root=workspace)

    async def _exec():
        import uuid
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        run = WorkflowRun(run_id=run_id, workflow_id=wf.id, context=context)

        with console.status(f"[bold cyan]Executing DAG {wf.id}...[/bold cyan]") as spinner:
            final_run = await engine.execute(wf, initial_context=context, run_state=run)
            store.save_run(final_run)
            return final_run

    final_run = _run_coroutine_sync(_exec())

    # Report outputs
    console.print(f"\n[bold]Execution Finished with Status:[/bold] {final_run.status}")
    for nid, res in final_run.results.items():
        icon = "✔" if res.status == NodeStatus.SUCCESS else ("⏸" if res.status == NodeStatus.WAITING_APPROVAL else "✖")
        color = "green" if res.status == NodeStatus.SUCCESS else ("yellow" if res.status == NodeStatus.WAITING_APPROVAL else "red")
        console.print(f"  [{color}]{icon}[/{color}] Node [bold]{nid}[/bold] ({res.duration_ms:.1f}ms): {res.status.value}")
        if res.error:
            console.print(f"      [red]Error: {res.error}[/red]")
        elif res.output:
            short_out = str(res.output).strip()
            if len(short_out) > 150:
                short_out = short_out[:147] + "..."
            console.print(f"      [dim]Output: {short_out}[/dim]")

    if final_run.pending_approval:
        console.print(
            Panel(
                f"[bold yellow]⏸ Workflow paused at Gate Node: '{final_run.pending_approval}'[/bold yellow]\n"
                f"To approve and resume execution, run:\n"
                f"[bold cyan]/panel approve {final_run.run_id} {final_run.pending_approval}[/bold cyan]",
                box=box.ROUNDED,
                border_style="yellow",
            )
        )


def resume_gate_sync(run_id: str, node_id: Optional[str], approved: bool, workspace: str) -> None:
    """Resumes an execution run paused at a human approval gate."""
    store = WorkflowStore()
    run = store.get_run(run_id)
    if not run:
        console.print(f"[bold red]Error:[/bold red] Run '{run_id}' not found.")
        return

    gate_node = node_id or run.pending_approval
    if not gate_node:
        console.print(f"[bold red]Error:[/bold red] Run '{run_id}' is not currently waiting for gate approval.")
        return

    wf = store.get_workflow(run.workflow_id)
    if not wf:
        console.print(f"[bold red]Error:[/bold red] Original workflow '{run.workflow_id}' not found.")
        return

    engine = WorkflowEngine(workspace_root=workspace)

    action_label = "Approved" if approved else "Denied"
    console.print(f"Gate node [bold cyan]{gate_node}[/bold cyan] set to [bold]{action_label}[/bold]. Resuming DAG...")

    async def _resume():
        resumed = await engine.approve_gate(wf, run, gate_node, approved=approved)
        store.save_run(resumed)
        return resumed

    final_run = _run_coroutine_sync(_resume())

    console.print(f"[bold green]Run {run_id} updated:[/bold green] Status = {final_run.status}")


def view_run_details(run_id: str) -> None:
    """Displays detailed execution results of a run."""
    store = WorkflowStore()
    run = store.get_run(run_id)
    if not run:
        console.print(f"[bold red]Error:[/bold red] Run '{run_id}' not found.")
        return

    console.print(
        Panel(
            f"[bold cyan]Workflow Run Detail:[/bold cyan] {run.run_id}\n"
            f"[dim]Workflow ID:[/dim] {run.workflow_id}  |  [dim]Status:[/dim] {run.status}\n"
            f"[dim]Started:[/dim] {run.start_time}  |  [dim]Ended:[/dim] {run.end_time or 'In Progress'}",
            box=box.ROUNDED,
        )
    )

    t = Table(box=box.SIMPLE_HEAVY)
    t.add_column("Node ID", style="cyan")
    t.add_column("Status", justify="center")
    t.add_column("Duration (ms)", justify="right")
    t.add_column("Output / Error", style="white")

    for nid, res in run.results.items():
        color = "green" if res.status == NodeStatus.SUCCESS else "red"
        content = res.error if res.error else str(res.output or "")
        t.add_row(
            nid,
            f"[{color}]{res.status.value}[/{color}]",
            f"{res.duration_ms:.1f}",
            content[:200] + ("..." if len(content) > 200 else ""),
        )

    console.print(t)


def handle_panel_cli(args: List[str], workspace_root: str) -> None:
    """Main dispatch for the `/panel` command in the CLI."""
    store = WorkflowStore()

    if not args or args[0] in ("dashboard", "status", "view_all"):
        render_dashboard(store, workspace_root)
        return

    cmd = args[0].lower()

    if cmd == "list":
        wfs = store.list_workflows()
        t = Table(title="Registered AI Workflows", box=box.ROUNDED)
        t.add_column("ID", style="cyan")
        t.add_column("Name", style="bold")
        t.add_column("Nodes", style="green")
        t.add_column("Description")
        for w in wfs:
            t.add_row(w["id"], w["name"], w["nodes_count"], w["description"])
        console.print(t)

    elif cmd == "runs":
        runs = store.list_runs(limit=20)
        t = Table(title="Workflow Execution History", box=box.ROUNDED)
        t.add_column("Run ID", style="cyan")
        t.add_column("Workflow", style="bold")
        t.add_column("Status")
        t.add_column("Time", style="dim")
        for r in runs:
            t.add_row(r["run_id"], r["workflow_id"], r["status"], r["start_time"][:19])
        console.print(t)

    elif cmd == "run":
        if len(args) < 2:
            console.print("[yellow]Usage: /panel run <workflow_id> [--params '{\"key\":\"value\"}'][/yellow]")
            return
        wid = args[1]
        params = args[2] if len(args) > 2 else None
        run_workflow_sync(wid, workspace_root, raw_params=params)

    elif cmd == "view":
        if len(args) < 2:
            console.print("[yellow]Usage: /panel view <run_id>[/yellow]")
            return
        view_run_details(args[1])

    elif cmd == "approve":
        if len(args) < 2:
            console.print("[yellow]Usage: /panel approve <run_id> [node_id][/yellow]")
            return
        run_id = args[1]
        node_id = args[2] if len(args) > 2 else None
        resume_gate_sync(run_id, node_id, approved=True, workspace=workspace_root)

    elif cmd == "deny":
        if len(args) < 2:
            console.print("[yellow]Usage: /panel deny <run_id> [node_id][/yellow]")
            return
        run_id = args[1]
        node_id = args[2] if len(args) > 2 else None
        resume_gate_sync(run_id, node_id, approved=False, workspace=workspace_root)

    elif cmd == "export":
        if len(args) < 2:
            console.print("[yellow]Usage: /panel export <workflow_id> [output_file.json][/yellow]")
            return
        wid = args[1]
        wf = store.get_workflow(wid)
        if not wf:
            console.print(f"[bold red]Workflow '{wid}' not found.[/bold red]")
            return
        out_path = Path(args[2]) if len(args) > 2 else Path(f"{wid}.json")
        out_path.write_text(wf.to_json(), encoding="utf-8")
        console.print(f"[green]✔ Workflow '{wid}' exported to {out_path.resolve()}[/green]")

    elif cmd == "import":
        if len(args) < 2:
            console.print("[yellow]Usage: /panel import <file.json>[/yellow]")
            return
        in_path = Path(args[1])
        if not in_path.exists():
            console.print(f"[bold red]File '{in_path}' not found.[/bold red]")
            return
        try:
            wf = Workflow.from_json(in_path.read_text(encoding="utf-8"))
            saved = store.save_workflow(wf)
            console.print(f"[green]✔ Workflow '{wf.name}' ({wf.id}) successfully imported to {saved}[/green]")
        except Exception as e:
            console.print(f"[bold red]Failed to import workflow: {e}[/bold red]")

    else:
        console.print(f"[yellow]Unknown /panel subcommand: '{cmd}'[/yellow]")
        console.print("Available: [cyan]list, run, runs, view, approve, deny, export, import[/cyan]")
