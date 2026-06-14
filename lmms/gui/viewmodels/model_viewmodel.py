from PyQt6.QtCore import QObject
from typing import Dict, Any

class ModelViewModel(QObject):
    """Transforms raw ModelManifest into GUI-friendly properties."""
    def __init__(self, raw_data: Dict[str, Any]):
        super().__init__()
        self.id = raw_data.get("id", "Unknown")
        self.provider = raw_data.get("provider", "Unknown")
        self.format = raw_data.get("format", "Unknown")
        self.source = raw_data.get("source", "Unknown")
        self.state = "Idle" # Will be updated by state manager
        
    def get_display_name(self) -> str:
        return self.id.split("/")[-1]
