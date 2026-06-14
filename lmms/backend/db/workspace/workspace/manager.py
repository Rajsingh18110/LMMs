import os
import json
import uuid
import datetime
from typing import Optional
from lmms.backend.db.workspace.db import DatabaseManager

class WorkspaceManager:
    """
    Manages Workspace lifecycle, metadata, and the mapping between 
    physical project paths and LMMs workspace IDs.
    """
    def __init__(self, base_dir="~/.lmms"):
        self.base_dir = os.path.expanduser(base_dir)
        self.workspaces_dir = os.path.join(self.base_dir, "workspaces")
        self.registry_file = os.path.join(self.workspaces_dir, "registry.json")
        self._ensure_dirs()

    def _ensure_dirs(self):
        os.makedirs(self.workspaces_dir, exist_ok=True)
        if not os.path.exists(self.registry_file):
            with open(self.registry_file, "w") as f:
                json.dump({}, f)

    def _load_registry(self) -> dict:
        try:
            with open(self.registry_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_registry(self, data: dict):
        with open(self.registry_file, "w") as f:
            json.dump(data, f, indent=4)

    def open(self, path: str) -> str:
        """
        Opens a workspace at the given path. Uses reopen logic if it already exists,
        otherwise creates a new one.
        Returns the workspace UUID.
        """
        abs_path = os.path.abspath(path)
        
        # Check if already a workspace
        existing_id = self.reopen(abs_path)
        if existing_id:
            return existing_id

        # Generate new workspace
        ws_id = str(uuid.uuid4())
        
        # Write .lmms-id signature file
        id_file = os.path.join(abs_path, ".lmms-id")
        try:
            with open(id_file, "w") as f:
                f.write(ws_id)
        except Exception as e:
            print(f"[WorkspaceManager] Warning: Could not write .lmms-id to {abs_path}: {e}")

        # Update global registry
        registry = self._load_registry()
        registry[ws_id] = {
            "path": abs_path,
            "name": os.path.basename(abs_path),
            "opened_at": datetime.datetime.now().isoformat()
        }
        self._save_registry(registry)

        # Initialize Database
        self.get_db(ws_id)
        
        return ws_id

    def reopen(self, path: str) -> Optional[str]:
        """
        Attempts to reopen an existing workspace. Handles moved folders if .lmms-id is present.
        If .lmms-id is missing but path matches registry, it regenerates the signature.
        """
        abs_path = os.path.abspath(path)
        id_file = os.path.join(abs_path, ".lmms-id")
        registry = self._load_registry()

        # Case 1: .lmms-id exists
        if os.path.exists(id_file):
            try:
                with open(id_file, "r") as f:
                    ws_id = f.read().strip()
                
                # Update registry in case folder was moved
                if ws_id in registry:
                    if registry[ws_id]["path"] != abs_path:
                        registry[ws_id]["path"] = abs_path
                        self._save_registry(registry)
                else:
                    # Known ID but missing from registry (restored folder/backup)
                    registry[ws_id] = {
                        "path": abs_path,
                        "name": os.path.basename(abs_path),
                        "opened_at": datetime.datetime.now().isoformat()
                    }
                    self._save_registry(registry)
                
                return ws_id
            except Exception:
                pass

        # Case 2: .lmms-id is missing, but path is in registry
        for ws_id, data in registry.items():
            if data.get("path") == abs_path:
                # Regenerate missing .lmms-id
                try:
                    with open(id_file, "w") as f:
                        f.write(ws_id)
                except Exception:
                    pass
                return ws_id

        return None

    def get_active_workspace(self) -> Optional[str]:
        # For CLI usage, active workspace is current working directory
        abs_path = os.path.abspath(".")
        return self.reopen(abs_path) or self.open(abs_path)

    def get_db(self, ws_id: str) -> DatabaseManager:
        """Returns the database connection for a specific workspace."""
        db_path = os.path.join(self.workspaces_dir, ws_id, "database.sqlite")
        return DatabaseManager(db_path)

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    manager = WorkspaceManager()
    ws_id = manager.open(path)
    print(f"Workspace initialized/opened with UUID: {ws_id}")
    print(f"Database ready at: ~/.lmms/workspaces/{ws_id}/database.sqlite")
