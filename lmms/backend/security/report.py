import os
import json
from datetime import datetime
from lmms.backend.security.scope import load_scope
from lmms.backend.security.defensive import get_evidence_dir

def generate_report(workspace: str, findings_summary: str) -> str:
    """
    Aggregates timeline and inventory into a single markdown report.
    Returns the path to the generated report.
    """
    if not workspace or workspace == "None":
        raise ValueError("No active workspace.")
        
    ev_dir = get_evidence_dir(workspace)
    timeline_path = os.path.join(ev_dir, "timeline.jsonl")
    inv_path = os.path.join(ev_dir, "asset_inventory.json")
    report_path = os.path.join(ev_dir, "SECURITY_REPORT.md")
    
    scope = load_scope(workspace) or {}
    
    timeline = []
    if os.path.exists(timeline_path):
        with open(timeline_path, "r") as f:
            for line in f:
                try:
                    timeline.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    pass
                    
    inventory = []
    if os.path.exists(inv_path):
        try:
            with open(inv_path, "r") as f:
                inventory = json.load(f)
        except json.JSONDecodeError:
            pass
            
    # Build Markdown Content
    md = []
    md.append(f"# Security Review & Audit Report")
    md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**Workspace:** `{workspace}`")
    md.append(f"**Engagement Name:** {scope.get('engagement_name', 'Default Offline Lab')}\n")
    
    md.append("## 1. Executive Summary")
    if findings_summary:
        md.append(findings_summary + "\n")
    else:
        md.append("No executive summary provided.\n")
        
    md.append("## 2. Scope & Target Information")
    targets = scope.get("authorized_targets", [])
    md.append(f"- **Authorized Targets:** {', '.join(targets) if targets else 'None (Offline Mode)'}")
    md.append(f"- **Network Actions Allowed:** {scope.get('network_actions_allowed', False)}")
    tools = scope.get("allowed_tools", [])
    md.append(f"- **Allowed Tools:** {', '.join(tools) if tools else 'None'}\n")
    
    md.append("## 3. Discovered Asset Inventory")
    if inventory:
        md.append("| Target IP | Port | Protocol | Service | State |")
        md.append("|---|---|---|---|---|")
        for asset in inventory:
            ip = asset.get("ip", "")
            port = asset.get("port", "")
            proto = asset.get("protocol", "")
            svc = asset.get("service", "")
            state = asset.get("state", "")
            md.append(f"| {ip} | {port} | {proto} | {svc} | {state} |")
    else:
        md.append("No structured assets recorded in inventory.")
    md.append("\n")
        
    md.append("## 4. Evidence Timeline")
    if timeline:
        md.append("| Timestamp | Command | Target | Result Summary |")
        md.append("|---|---|---|---|")
        for entry in timeline:
            ts = entry.get("timestamp", "")
            # Format timestamp nicely if possible
            if "T" in ts:
                ts = ts.split(".")[0].replace("T", " ")
            cmd = entry.get("command", "")
            target = entry.get("target", "")
            res = entry.get("result", "").replace("\n", " ") # Keep table clean
            if len(res) > 50:
                res = res[:47] + "..."
            md.append(f"| {ts} | `{cmd}` | {target} | {res} |")
    else:
        md.append("No actions recorded in timeline.")
    md.append("\n")
    
    md.append("## 5. Security Recommendations & Fixes")
    md.append("*(Refer to the executive summary for detailed remediation steps taken during the session.)*\n")
    
    with open(report_path, "w") as f:
        f.write("\n".join(md))
        
    return report_path
