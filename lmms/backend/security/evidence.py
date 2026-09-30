import os
import json
import datetime
from lmms.backend.security.models import ToolRequest, PermissionResult, ToolResult

def get_evidence_path(workspace: str) -> str:
    # Get from scope, fallback to workspace/.lmms/evidence
    from lmms.backend.security.scope import load_scope
    scope = load_scope(workspace)
    ev_dir = scope.get("evidence_directory", ".lmms/evidence") if scope else ".lmms/evidence"
    if ev_dir.startswith("~"):
        ev_dir = os.path.expanduser(ev_dir)
    elif not os.path.isabs(ev_dir):
        if workspace and workspace != "None":
            ev_dir = os.path.join(workspace, ev_dir)
        else:
            ev_dir = os.path.abspath(ev_dir)
    return ev_dir

def record_tool_evidence(request: ToolRequest, perm: PermissionResult, result: ToolResult) -> None:
    ev_dir = get_evidence_path(request.workspace)
    if not os.path.exists(ev_dir):
        try:
            os.makedirs(ev_dir, exist_ok=True)
        except Exception:
            return
            
    timeline_path = os.path.join(ev_dir, "timeline.jsonl")
    
    # Extract arguments safely without logging secrets
    # We log kwargs as strings but remove obvious secrets if they existed?
    # Simple JSON dump for now, assuming arguments are command args
    
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "tool": request.tool_name,
        "arguments": request.kwargs,
        "target": request.kwargs.get("command", "") if request.tool_name == "terminal.run" else request.kwargs.get("url", ""),
        "decision": "allowed" if perm.allowed else "denied",
        "reason": perm.reason,
        "risk_level": perm.risk_level,
        "exit_code": result.exit_code
    }
    
    try:
        with open(timeline_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
