import os
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

class ActionHistory:
    """
    An immutable ledger that records actions taken by AI agents within a workspace.
    This tracks what files were modified, commands executed, tool calls made, etc.
    """
    
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.lmms_dir = os.path.join(workspace_dir, ".lmms")
        self.history_file = os.path.join(self.lmms_dir, "action_history.jsonl")
        
        # Ensure the .lmms directory exists in the workspace
        if os.path.exists(workspace_dir):
            os.makedirs(self.lmms_dir, exist_ok=True)
            
    def _record_action(self, agent_name: str, action_type: str, details: Dict[str, Any]):
        """
        Record a generic action into the ledger.
        """
        if not os.path.exists(self.lmms_dir):
            return
            
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "unix_time": time.time(),
            "agent": agent_name,
            "type": action_type,
            "details": details
        }
        
        try:
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"Failed to write to action history: {e}")

    def record_file_modified(self, agent_name: str, file_path: str, diff_summary: str = ""):
        self._record_action(agent_name, "FILE_MODIFIED", {
            "file": file_path,
            "diff_summary": diff_summary
        })

    def record_file_created(self, agent_name: str, file_path: str):
        self._record_action(agent_name, "FILE_CREATED", {
            "file": file_path
        })
        
    def record_command_executed(self, agent_name: str, command: str, exit_code: int = 0):
        self._record_action(agent_name, "COMMAND_EXECUTED", {
            "command": command,
            "exit_code": exit_code
        })

    def record_tool_call(self, agent_name: str, tool_name: str, arguments: Dict[str, Any]):
        self._record_action(agent_name, "TOOL_CALL", {
            "tool": tool_name,
            "arguments": arguments
        })

    def record_git_commit(self, agent_name: str, commit_hash: str, message: str):
        self._record_action(agent_name, "GIT_COMMIT", {
            "commit_hash": commit_hash,
            "message": message
        })

    def get_recent_actions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve the most recent actions from the ledger.
        """
        if not os.path.exists(self.history_file):
            return []
            
        actions = []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        actions.append(json.loads(line))
        except Exception:
            return []
            
        return actions[-limit:]
