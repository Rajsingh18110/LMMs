import re

with open("lmms/backend/cli/cli.py", "r") as f:
    content = f.read()

# Replace parser setup
old_parser = """    research_parser = subparsers.add_parser("research", help="Execute web research")
    research_parser.add_argument("query", help="Research query to execute")"""

new_parser = """    research_parser = subparsers.add_parser("research", help="Execute web research or view history")
    research_parser.add_argument("action", help="Research query, or 'history'")
    research_parser.add_argument("run_id", nargs="?", help="Run ID if action is 'history'")"""

content = content.replace(old_parser, new_parser)

# Find the block for research handler
match = re.search(r'    elif parsed\.command == "research":\n.*?(?=    else:\n        # Generic catch-all)', content, flags=re.DOTALL)
if match:
    old_handler = match.group(0)
    new_handler = """    elif parsed.command == "research":
        import asyncio
        from rich.live import Live
        from rich.panel import Panel
        from rich.text import Text
        from rich.console import Group
        
        from lmms.backend.research.engine import ResearchEngine
        from lmms.backend.research.history import ResearchHistoryStore
        from lmms.backend.research.events import (
            ResearchEvent, ResearchStarted, SearchCompleted, SearchFailed, DeduplicationCompleted,
            FetchStarted, FetchCompleted, FetchFailed, ExtractionCompleted, EvidenceAdded, ResearchCompleted, ResearchFailed
        )
        
        if parsed.action == "history":
            if not parsed.run_id:
                console.print("[red]Error: Must provide a run_id for history (e.g. lmm research history R-20260817-abc)[/red]")
                import sys
                sys.exit(1)
            store = ResearchHistoryStore()
            run = store.get_run(parsed.run_id)
            if not run:
                console.print(f"[red]Error: Run {parsed.run_id} not found or corrupted.[/red]")
                import sys
                sys.exit(1)
            
            console.print(f"\\n[bold]History for {parsed.run_id}[/bold]")
            console.print(f"Query: {run.get('query')}")
            console.print(f"Success: {run.get('success')}")
            console.print("\\n[bold cyan]Citations:[/bold cyan]")
            for cit in run.get('citations', []):
                console.print(f"[{cit.get('number')}] {cit.get('evidence', {}).get('title')} ({cit.get('evidence', {}).get('source_url')})")
            return
            
        async def run_research():
            engine = ResearchEngine()
            
            # State for Live UI
            state = {
                "run_id": "Initializing...",
                "searches": {},
                "dedup": "",
                "fetch_total": 0,
                "fetch_done": 0,
                "fetch_failed": 0,
                "extract_done": 0,
                "evidence_count": 0,
                "status": "Starting..."
            }
            
            def render_ui():
                lines = [Text(f"Run: {state['run_id']}", style="dim")]
                lines.append(Text(" "))
                
                lines.append(Text("● Searching", style="bold cyan"))
                if not state["searches"]:
                    lines.append(Text("  ..."))
                for query, count in state["searches"].items():
                    if count == -1:
                        lines.append(Text(f"  ├─ {query} ✗ Failed", style="red"))
                    else:
                        lines.append(Text(f"  ├─ {query} ✓ {count}", style="green"))
                        
                lines.append(Text(" "))
                lines.append(Text("● Deduplicating", style="bold cyan"))
                lines.append(Text(f"  {state['dedup']}" if state['dedup'] else "  ..."))
                
                lines.append(Text(" "))
                lines.append(Text("● Fetching", style="bold cyan"))
                if state["fetch_total"] > 0:
                    lines.append(Text(f"  {state['fetch_done']}/{state['fetch_total']} completed | {state['fetch_failed']} failed"))
                else:
                    lines.append(Text("  ..."))
                    
                lines.append(Text(" "))
                lines.append(Text("● Extracting", style="bold cyan"))
                lines.append(Text(f"  {state['extract_done']} pages processed"))
                
                lines.append(Text(" "))
                lines.append(Text("● Evidence", style="bold cyan"))
                lines.append(Text(f"  {state['evidence_count']} evidence blocks"))
                
                lines.append(Text(" "))
                if "Failed:" in state["status"]:
                    lines.append(Text(f"✗ {state['status']}", style="bold red"))
                elif state["status"] == "Complete":
                    lines.append(Text(f"✓ Research complete", style="bold green"))
                else:
                    lines.append(Text(f"  {state['status']}", style="italic yellow"))
                    
                return Panel(Group(*lines), title="LMMs Research", border_style="blue")
                
            async def event_handler(event: ResearchEvent):
                if isinstance(event, ResearchStarted):
                    state["run_id"] = event.run_id
                elif isinstance(event, SearchCompleted):
                    state["searches"][event.query] = event.result_count
                elif isinstance(event, SearchFailed):
                    state["searches"][event.query] = -1
                elif isinstance(event, DeduplicationCompleted):
                    state["dedup"] = f"→ {event.unique_count} unique URLs"
                    state["fetch_total"] = event.unique_count
                elif isinstance(event, FetchCompleted):
                    state["fetch_done"] += 1
                elif isinstance(event, FetchFailed):
                    state["fetch_failed"] += 1
                elif isinstance(event, ExtractionCompleted):
                    state["extract_done"] += 1
                elif isinstance(event, EvidenceAdded):
                    state["evidence_count"] += 1
                elif isinstance(event, ResearchCompleted):
                    state["status"] = "Complete"
                elif isinstance(event, ResearchFailed):
                    state["status"] = f"Failed: {event.error}"

            # Run with Live dashboard
            with Live(render_ui(), refresh_per_second=4) as live:
                
                # Wrap event handler so it triggers live UI update
                async def emit(ev):
                    await event_handler(ev)
                    live.update(render_ui())
                    
                result = await engine.execute(parsed.action, emit_cb=emit)
                
            if result.success:
                console.print("\\n[bold green]Sources:[/bold green]")
                for cit in result.citations:
                    console.print(f"[[bold yellow]{cit.number}[/bold yellow]] [italic]{cit.evidence.title}[/italic]\\n{cit.evidence.source_url}\\n")
                console.print(f"[bold cyan]Run ID: {state['run_id']}[/bold cyan]")
                
        asyncio.run(run_research())
"""
    content = content.replace(old_handler, new_handler)

with open("lmms/backend/cli/cli.py", "w") as f:
    f.write(content)

print("Rewrote CLI handler.")
