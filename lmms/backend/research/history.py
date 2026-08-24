import os
import json
import dataclasses
from typing import Optional, Dict, Any
from lmms.backend.research.result import ResearchResult

class ResearchHistoryStore:
    def __init__(self, base_dir: str = None):
        if not base_dir:
            base_dir = os.path.expanduser("~/.lmms/research")
        self.base_dir = base_dir
        
    def _ensure_dir(self):
        os.makedirs(self.base_dir, exist_ok=True)
        
    def _get_path(self, run_id: str) -> str:
        # Sanitize to prevent path traversal
        clean_id = "".join(c for c in run_id if c.isalnum() or c in "-_")
        return os.path.join(self.base_dir, f"{clean_id}.json")

    def save_run(self, run_id: str, result: ResearchResult):
        self._ensure_dir()
        
        # Convert to dict
        data = dataclasses.asdict(result)
        
        # Enforce reasonable size limits on raw evidence content to save disk space
        # We cap stored evidence at ~5000 chars per block to prevent multi-megabyte JSONs
        for ev in data.get("evidence", []):
            if len(ev.get("content", "")) > 5000:
                ev["content"] = ev["content"][:5000] + "\n...[truncated for storage]..."
                
        # Also clean citations
        for cit in data.get("citations", []):
            if "evidence" in cit and len(cit["evidence"].get("content", "")) > 5000:
                cit["evidence"]["content"] = cit["evidence"]["content"][:5000] + "\n...[truncated for storage]..."
                
        # Inject run_id
        data["run_id"] = run_id
        
        path = self._get_path(run_id)
        temp_path = f"{path}.tmp"
        
        try:
            # Atomic write
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_path, path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            print(f"[ResearchHistory] Failed to save run {run_id}: {e}")

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        path = self._get_path(run_id)
        if not os.path.exists(path):
            return None
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ResearchHistory] Corrupted or unreadable run {run_id}: {e}")
            return None
