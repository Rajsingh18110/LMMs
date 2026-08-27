"""Extension system models — state machine, records, compatibility levels."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from pathlib import Path

EXTENSIONS_ROOT = Path.home() / ".lmms" / "extensions"


class ExtState(str, Enum):
    AVAILABLE    = "available"
    INSTALLING   = "installing"
    INSTALLED    = "installed"
    ACTIVATING   = "activating"
    ACTIVE       = "active"
    DISABLED     = "disabled"
    FAILED       = "failed"
    UNINSTALLING = "uninstalling"
    UNINSTALLED  = "uninstalled"


class CompatLevel(str, Enum):
    FULL         = "FULL"          # all required APIs implemented
    PARTIAL      = "PARTIAL"       # some APIs missing
    INSTALL_ONLY = "INSTALL_ONLY"  # downloaded but cannot activate
    INCOMPATIBLE = "INCOMPATIBLE"  # e.g. requires unavailable platform


# APIs we actually implement — used to compute compat level
IMPLEMENTED_APIS = {
    "vscode.commands",
    "vscode.window.showInformationMessage",
    "vscode.window.showWarningMessage",
    "vscode.window.showErrorMessage",
    "vscode.window.showInputBox",
    "vscode.window.showQuickPick",
    "vscode.workspace.workspaceFolders",
    "vscode.workspace.getConfiguration",
    "vscode.workspace.openTextDocument",
    "vscode.workspace.fs.readFile",
    "vscode.workspace.fs.writeFile",
    "vscode.workspace.fs.stat",
    "vscode.env.appName",
    "vscode.languages.registerCompletionItemProvider",
    "vscode.languages.registerHoverProvider",
    "vscode.languages.registerDiagnosticCollection",
}


@dataclass
class ExtensionRecord:
    """Runtime record for one installed extension."""
    ext_id:       str              # e.g. "ms-python.python"
    namespace:    str              # "ms-python"
    name:         str              # "python"
    display_name: str
    version:      str
    state:        ExtState         = ExtState.AVAILABLE
    compat:       CompatLevel      = CompatLevel.INSTALL_ONLY
    path:         Optional[str]    = None   # extracted dir
    manifest:     dict             = field(default_factory=dict)
    error:        Optional[str]    = None
    log_lines:    list[str]        = field(default_factory=list)
    icon_url:     Optional[str]    = None
    downloads:    int              = 0

    # ── helpers ────────────────────────────────────────────────────────────

    def to_json(self) -> dict:
        return {
            "ext_id":       self.ext_id,
            "namespace":    self.namespace,
            "name":         self.name,
            "display_name": self.display_name,
            "version":      self.version,
            "state":        self.state.value,
            "compat":       self.compat.value,
            "path":         self.path,
            "manifest":     self.manifest,
            "error":        self.error,
            "icon_url":     self.icon_url,
            "downloads":    self.downloads,
        }

    @classmethod
    def from_json(cls, d: dict) -> "ExtensionRecord":
        r = cls(
            ext_id       = d["ext_id"],
            namespace    = d["namespace"],
            name         = d["name"],
            display_name = d.get("display_name", d["name"]),
            version      = d.get("version", ""),
            state        = ExtState(d.get("state", "installed")),
            compat       = CompatLevel(d.get("compat", "INSTALL_ONLY")),
            path         = d.get("path"),
            manifest     = d.get("manifest", {}),
            error        = d.get("error"),
            icon_url     = d.get("icon_url"),
            downloads    = int(d.get("downloads", 0)),
        )
        return r

    def log(self, msg: str):
        import datetime
        self.log_lines.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")
        # Keep last 500 lines
        if len(self.log_lines) > 500:
            self.log_lines = self.log_lines[-500:]


def compute_compat(manifest: dict) -> CompatLevel:
    """
    Determine compatibility level by examining what the extension contributes
    and what VS Code API level it needs.
    """
    import shutil
    # Without Node.js we can't activate JS extensions
    if not shutil.which("node"):
        return CompatLevel.INSTALL_ONLY

    # Engine requirement
    engines = manifest.get("engines", {})
    vscode_req = engines.get("vscode", "")
    if vscode_req and not _engine_ok(vscode_req):
        return CompatLevel.PARTIAL  # may still partially work

    # Check contribution points
    contributes = manifest.get("contributes", {})
    needs_unimplemented = set()

    if "debuggers" in contributes:
        needs_unimplemented.add("vscode.debug")
    if "taskDefinitions" in contributes:
        needs_unimplemented.add("vscode.tasks")
    if "authentication" in contributes:
        needs_unimplemented.add("vscode.authentication")

    # Check activationEvents for things we can't handle
    for ev in manifest.get("activationEvents", []):
        if ev.startswith("onDebug"):
            needs_unimplemented.add("vscode.debug")
        if ev.startswith("onAuthenticationRequest"):
            needs_unimplemented.add("vscode.authentication")

    if not needs_unimplemented:
        return CompatLevel.FULL
    # Some unimplemented but still activatable
    return CompatLevel.PARTIAL


def _engine_ok(req: str) -> bool:
    """Very simple semver check — just accept anything >=1.60."""
    import re
    m = re.search(r"(\d+)\.(\d+)", req)
    if not m:
        return True
    major, minor = int(m.group(1)), int(m.group(2))
    return major <= 1 and minor <= 100   # we simulate up to 1.100
