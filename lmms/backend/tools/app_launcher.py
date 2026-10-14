import os
import shutil
import subprocess
import glob
import re
from typing import Dict, List, Optional

class AppLauncherTool:
    """
    Desktop & OS Application Launcher for LMMs.
    Allows the AI agent to launch, switch to, or list installed desktop apps (Chrome, VLC, Spotify, VS Code, etc.)
    without freezing the terminal session.
    """

    COMMON_ALIASES = {
        "chrome": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
        "google-chrome": ["google-chrome", "google-chrome-stable", "chromium"],
        "brave": ["brave-browser", "brave"],
        "firefox": ["firefox", "firefox-esr"],
        "edge": ["microsoft-edge-stable", "microsoft-edge-dev", "microsoft-edge"],
        "code": ["code", "codium"],
        "vscode": ["code", "codium"],
        "sublime": ["subl"],
        "gedit": ["gedit", "mousepad", "kate", "xed"],
        "vlc": ["vlc"],
        "spotify": ["spotify"],
        "calculator": ["gnome-calculator", "kcalc", "galculator", "xcalc"],
        "calc": ["gnome-calculator", "kcalc", "galculator", "xcalc"],
        "terminal": ["qterminal", "xfce4-terminal", "gnome-terminal", "konsole", "x-terminal-emulator", "xterm"],
        "files": ["thunar", "nautilus", "dolphin", "pcmanfm", "caja"],
        "filemanager": ["thunar", "nautilus", "dolphin", "pcmanfm", "caja"],
        "explorer": ["thunar", "nautilus", "dolphin", "pcmanfm"],
        "telegram": ["telegram-desktop", "telegram"],
        "discord": ["discord", "Discord"],
        "slack": ["slack"],
        "gimp": ["gimp"],
        "blender": ["blender"],
        "antigravity": ["antigravity", "antigravity-ide"],
    }

    def __init__(self):
        self._cached_apps: Optional[List[Dict[str, str]]] = None

    def _get_installed_desktop_apps(self) -> List[Dict[str, str]]:
        if self._cached_apps is not None:
            return self._cached_apps

        apps = []
        search_dirs = [
            "/usr/share/applications",
            "/usr/local/share/applications",
            os.path.expanduser("~/.local/share/applications"),
        ]

        seen_names = set()

        for sdir in search_dirs:
            if not os.path.exists(sdir):
                continue
            for fpath in glob.glob(os.path.join(sdir, "*.desktop")):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    
                    name_match = re.search(r"^Name=(.+)$", content, re.MULTILINE)
                    exec_match = re.search(r"^Exec=(.+)$", content, re.MULTILINE)
                    nodisplay = re.search(r"^NoDisplay=(true|1)$", content, re.MULTILINE | re.IGNORECASE)

                    if name_match and exec_match and not nodisplay:
                        name = name_match.group(1).strip()
                        raw_exec = exec_match.group(1).strip()
                        # Strip standard desktop parameter placeholders like %U, %F, %f
                        clean_cmd = re.sub(r"%[a-zA-Z]", "", raw_exec).strip()
                        binary_name = clean_cmd.split()[0] if clean_cmd else ""

                        if name.lower() not in seen_names and binary_name:
                            seen_names.add(name.lower())
                            apps.append({
                                "name": name,
                                "binary": binary_name,
                                "exec": clean_cmd,
                                "desktop_file": fpath
                            })
                except Exception:
                    continue

        self._cached_apps = apps
        return apps

    def list_apps(self, filter_query: str = "") -> str:
        """List available desktop apps on the system."""
        apps = self._get_installed_desktop_apps()
        if filter_query:
            q = filter_query.lower()
            apps = [a for a in apps if q in a["name"].lower() or q in a["binary"].lower()]

        if not apps:
            return f"No desktop applications found matching '{filter_query}'."

        lines = [f"Found {len(apps)} installed desktop application(s):"]
        for a in apps[:30]:  # limit to top 30
            lines.append(f"- {a['name']} (command: `{a['binary']}`)")
        if len(apps) > 30:
            lines.append(f"... and {len(apps) - 30} more.")
        return "\n".join(lines)

    def launch(self, app_name_or_target: str, args: Optional[List[str]] = None) -> str:
        """
        Launch a desktop application, URL, or local file in the background.
        Example:
            launch("google-chrome", ["https://github.com"])
            launch("calculator")
            launch("vlc", ["/path/to/video.mp4"])
            launch("https://google.com")
        """
        if not app_name_or_target:
            return "Error: No application or target specified."

        target = app_name_or_target.strip()
        cmd_args = args or []

        # 1. Handle Web URLs directly
        if target.startswith("http://") or target.startswith("https://"):
            try:
                proc = subprocess.Popen(
                    ["xdg-open", target],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return f"[SUCCESS] Opened URL '{target}' in default web browser (PID: {proc.pid})."
            except Exception as e:
                return f"Failed to open URL via xdg-open: {e}"

        # 2. Check alias map
        lowered = target.lower()
        candidates = self.COMMON_ALIASES.get(lowered, [target])

        resolved_binary = None
        for cand in candidates:
            if shutil.which(cand):
                resolved_binary = cand
                break

        # 3. If not found in aliases, check installed desktop files
        if not resolved_binary:
            apps = self._get_installed_desktop_apps()
            for a in apps:
                if lowered in a["name"].lower() or lowered in a["binary"].lower():
                    if shutil.which(a["binary"]):
                        resolved_binary = a["binary"]
                        break

        # 4. If target is a file or directory path, open with xdg-open
        if not resolved_binary and os.path.exists(target):
            try:
                proc = subprocess.Popen(
                    ["xdg-open", target],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return f"[SUCCESS] Opened path '{target}' with default desktop application (PID: {proc.pid})."
            except Exception as e:
                return f"Failed to open path: {e}"

        if not resolved_binary:
            # Try raw target as command
            if shutil.which(target):
                resolved_binary = target
            else:
                return (
                    f"Error: Could not find application '{target}' on this system. "
                    f"Use `app.list` to see installed desktop applications."
                )

        # Launch detached process
        full_command = [resolved_binary] + cmd_args
        try:
            proc = subprocess.Popen(
                full_command,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return f"[SUCCESS] Launched '{resolved_binary}' successfully (PID: {proc.pid})."
        except Exception as e:
            return f"Failed to launch '{resolved_binary}': {str(e)}"

    def close_app(self, app_name: str) -> str:
        """Close/terminate a running desktop application."""
        if not app_name:
            return "Error: No application name specified to close."
        try:
            # Safely pkill matching process
            res = subprocess.run(["pkill", "-f", app_name.strip()], capture_output=True, text=True)
            if res.returncode == 0:
                return f"[SUCCESS] Terminated application matching '{app_name}'."
            else:
                return f"No running application matched '{app_name}'."
        except Exception as e:
            return f"Failed to close application: {e}"
