import subprocess
import shutil
from lmms.backend.tools.core_tools.base import ToolResult
from lmms.backend.config.config.permissions import get_permission_level

async def execute_apt_search(params: dict) -> ToolResult:
    package_name = params.get("package_name")
    if not package_name:
        return ToolResult(tool_name="apt_search", success=False, error="Missing package_name", data=None)
        
    try:
        proc = subprocess.run(["apt-cache", "search", package_name], capture_output=True, text=True)
        lines = proc.stdout.strip().split("\n")
        results = []
        for line in lines[:10]: # Return top 10 matches
            if line:
                parts = line.split(" - ", 1)
                if len(parts) == 2:
                    results.append({"package": parts[0], "description": parts[1]})
        return ToolResult(tool_name="apt_search", success=True, data=results)
    except Exception as e:
        return ToolResult(tool_name="apt_search", success=False, error=str(e), data=None)

async def execute_apt_install(params: dict) -> ToolResult:
    package_name = params.get("package_name")
    if not package_name:
        return ToolResult(tool_name="apt_install", success=False, error="Missing package_name", data=None)
        
    perm = get_permission_level()
    if perm != "full":
        return ToolResult(tool_name="apt_install", success=False, error=f"Permission denied: Requires 'full' permission level (current is '{perm}')", data=None)
        
    # Ask for confirmation
    print(f"\n[URGENT] LMMS requests permission to run: sudo apt install -y {package_name}")
    confirm = input("Allow this action? (y/N): ")
    if confirm.lower() != 'y':
        return ToolResult(tool_name="apt_install", success=False, error="User rejected the action.", data=None)
        
    try:
        proc = subprocess.run(["sudo", "apt", "install", "-y", package_name], capture_output=True, text=True)
        if proc.returncode == 0:
            return ToolResult(tool_name="apt_install", success=True, data={"message": f"Successfully installed {package_name}"})
        return ToolResult(tool_name="apt_install", success=False, error=f"apt install failed: {proc.stderr}", data=None)
    except Exception as e:
        return ToolResult(tool_name="apt_install", success=False, error=str(e), data=None)

async def execute_launch_app(params: dict) -> ToolResult:
    app_name = params.get("app_name")
    if not app_name:
        return ToolResult(tool_name="launch_app", success=False, error="Missing app_name", data=None)
        
    app_path = shutil.which(app_name)
    if not app_path:
        return ToolResult(tool_name="launch_app", success=False, error=f"Application '{app_name}' not found in PATH", data=None)
        
    try:
        # Launching asynchronously and detaching
        subprocess.Popen([app_path], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ToolResult(tool_name="launch_app", success=True, data={"message": f"Launched {app_name} at {app_path}"})
    except Exception as e:
        return ToolResult(tool_name="launch_app", success=False, error=str(e), data=None)
