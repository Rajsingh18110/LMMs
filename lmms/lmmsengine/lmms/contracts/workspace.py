from typing import Protocol, Any, Dict, List

class WorkspaceContract(Protocol):
    """Protocol for workspace management."""
    
    def initialize_workspace(self, path: str) -> str:
        ...
        
    def scan_files(self, workspace_id: str) -> List[str]:
        ...
        
    def get_context(self, workspace_id: str) -> Dict[str, Any]:
        ...
