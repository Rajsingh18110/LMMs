import subprocess
import sys
import json
import os
import platform
import requests
from pathlib import Path
from rich.progress import Progress, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from . import reporter

def check_python_version():
    return sys.version_info >= (3, 9)

def ensure_base_tools():
    # Only useful if we still use pip for other components
    return True

def get_registry_path():
    p = Path(os.path.expanduser("~/.lmms/config/installed_components.json"))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def get_installed_components():
    reg = get_registry_path()
    if reg.exists():
        try:
            with open(reg, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def mark_installed(component):
    installed = get_installed_components()
    installed[component] = True
    with open(get_registry_path(), "w") as f:
        json.dump(installed, f)

def download_binary(component_name):
    # Detect OS
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Map component to prefix
    if component_name == "all":
        prefix = "LMMs"
    elif component_name == "engine":
        prefix = "LMMs-Engine"
    elif component_name == "backend":
        prefix = "LMMs-Backend"
    elif component_name == "gui":
        prefix = "LMMs-GUI"
    else:
        prefix = "LMMs"

    # Construct binary name
    if system == "windows":
        binary_name = f"{prefix}-windows-latest.exe"
    elif system == "linux":
        binary_name = f"{prefix}-ubuntu-latest"
    elif system == "darwin": # macOS
        binary_name = f"{prefix}-macos-latest"
    else:
        reporter.print_error(f"Unsupported OS for binary download: {system}")
        return False

    # Define Download URL (GitHub Releases)
    repo_url = "https://github.com/MarkanM-Official/LMMs/releases/latest/download"
    download_url = f"{repo_url}/{binary_name}"
    
    # Define Install Path
    if system == "windows":
        install_dir = Path(os.path.expandvars("%LOCALAPPDATA%")) / "LMMs" / "bin"
        install_path = install_dir / f"{prefix.lower()}.exe"
    else:
        # Default Linux/Mac path
        install_dir = Path("/usr/local/bin")
        install_path = install_dir / prefix.lower()
        
        # Fallback if no sudo permissions
        if not os.access(install_dir, os.W_OK):
            install_dir = Path.home() / ".local" / "bin"
            install_path = install_dir / prefix.lower()
            
    install_dir.mkdir(parents=True, exist_ok=True)
    
    reporter.print_step(f"Downloading compiled {component_name} from GitHub Releases...")
    
    try:
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        with Progress(
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=40),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
            "•",
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn(),
            console=reporter.console
        ) as progress:
            task = progress.add_task(f"Downloading {prefix}...", total=total_size)
            with open(install_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        progress.update(task, advance=len(chunk))
        
        if system != "windows":
            # Make executable
            os.chmod(install_path, 0o755)
        reporter.print_success(f"✓ Binary installed to {install_path}")
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            reporter.print_error(f"Download Error: Binary not found on GitHub (404).")
            reporter.print_error("Please upload the compiled binary to your GitHub Releases first!")
        else:
            reporter.print_error(f"HTTP Error: {e}")
        return False
    except Exception as e:
        reporter.print_error(f"Download failed: {e}")
        return False

def install_component(component_name):
    installed = get_installed_components()
    if installed.get(component_name):
        reporter.print_success(f"✓ {component_name.capitalize()} is already installed. Skipping.")
        return True, ""

    reporter.print_step(f"Installing {component_name.capitalize()}...")
    
    if component_name in ["engine", "backend", "gui", "cli", "all"]:
        # We now download the compiled binary for ALL components instead of git cloning
        # Map cli to backend since they are bundled
        comp_to_download = "backend" if component_name == "cli" else component_name
        success = download_binary(comp_to_download)
        if success:
            mark_installed(component_name)
            return True, ""
        return False, "Binary download failed"
        
    else:
        reporter.print_error(f"Unknown component: {component_name}")
        return False, "Unknown component"
