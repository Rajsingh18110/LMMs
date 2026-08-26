# Made by markanm
from PyQt6.QtCore import QObject, pyqtSignal
from urllib.parse import unquote
import os

class DiagnosticManager(QObject):
    _instance = None
    
    # Signal emitted when diagnostics for a file change
    diagnostics_updated = pyqtSignal(str) # Emits the file path
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = DiagnosticManager()
        return cls._instance
        
    def __init__(self):
        super().__init__()
        # Map of absolute file path -> list of diagnostics
        self._diagnostics = {}
        
    def update_diagnostics(self, uri, diagnostics):
        """Called by LSPManager when publishDiagnostics is received."""
        # Convert URI to absolute path
        if uri.startswith("file://"):
            file_path = unquote(uri[7:])
        else:
            file_path = unquote(uri)
            
        file_path = os.path.abspath(file_path)
        
        self._diagnostics[file_path] = diagnostics
        self.diagnostics_updated.emit(file_path)
        
    def get_diagnostics(self, file_path=None):
        """Get diagnostics for a specific file, or all if file_path is None."""
        if file_path:
            return self._diagnostics.get(os.path.abspath(file_path), [])
        return self._diagnostics
        
    def has_errors(self, path):
        """Check if a file or any file in a directory has errors (severity 1)."""
        abs_path = os.path.abspath(path)
        
        for file_path, diags in self._diagnostics.items():
            if file_path == abs_path or file_path.startswith(abs_path + os.sep):
                # Check if any diagnostic is an error (severity 1 usually)
                for d in diags:
                    if d.get("severity") == 1:
                        return True
        return False
