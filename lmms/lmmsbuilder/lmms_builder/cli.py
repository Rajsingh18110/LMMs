import argparse
import sys
import os
import shutil
import platform
import subprocess
from pathlib import Path

from . import hardware
from . import reporter
from . import installer

LMMS_CONFIG_DIR = Path(os.path.expanduser("~/.lmms"))
LMMS_PROJECT_DIR = Path(os.path.expanduser("~/Projects/LMMs"))  # Assuming this is where it's cloned

def print_help():
    reporter.print_header()
    print("\n[bold yellow]=== LMMs Complete Command List ===[/bold yellow]")
    print("\n[bold cyan]1) Builder / Installer[/bold cyan]")
    print("  LMMs-builder -check                 : Automatically detects OS, hardware compatibility, and installed LMMs components.")
    print("  LMMs-builder install --<component>  : Downloads and installs a specific component (e.g., --engine, --gui). Automatically installs dependencies.")
    print("  LMMs-builder install --all          : Downloads and installs the entire LMMs ecosystem.")
    print("  LMMs-builder update --all           : Forces a download of the latest code/binary version from GitHub Releases.")
    
    print("\n[bold cyan]2) Repair & Rebuild[/bold cyan]")
    print("  LMMs-repair LMMs -<component>       : Repairs a corrupted component without deleting your saved data (chats, persona, models).")
    print("  LMMs-rebuild LMMs                   : Factory reset. Completely deletes the LMMs project and all your saved user data, then installs fresh.")
    print("  LMMs-rebuild LMMs -ds               : Data-safe reset. Rebuilds the code structure but keeps your saved user data intact.")
    
    print("\n[bold cyan]3) Uninstall[/bold cyan]")
    print("  LMMs-uninstall --<component>        : Deletes a specific component from your system.")
    print("  LMMs-uninstall -all --purge         : Completely removes all LMMs code and user data from your PC.")
    
    print("\n[bold cyan]4) Launch Options[/bold cyan]")
    print("  LMMs -set --gui|--cli|--engine      : Sets the default component that starts when you just type 'LMMs'.")
    print("  LMMs --gui|--cli|--engine           : Directly runs the specified component overriding the default.")
    print("  LMMs                                : Runs the default component.")
    print("  LMMs-cl                             : Shows this complete command list.\n")

def builder_main():
    if "-check" in sys.argv:
        reporter.print_step("Running LMMs System Check...")
        hw = hardware.detect_all()
        reporter.print_hardware_report(hw)
        installed = installer.get_installed_components()
        reporter.print_step("Installed Components:")
        for k, v in installed.items():
            if v:
                print(f"  - {k.capitalize()}")
        if not any(installed.values()):
            print("  - None")
        return

    if "install" in sys.argv or "update" in sys.argv:
        force_update = "update" in sys.argv
        components_to_install = []
        if "--all" in sys.argv:
            components_to_install = ["all"]
        else:
            if "--engine" in sys.argv: components_to_install.append("engine")
            if "--backend" in sys.argv: components_to_install.append("backend")
            if "--gui" in sys.argv: components_to_install.append("gui")
        
        # Rule: If GUI or Engine, force backend
        if "all" not in components_to_install and ("gui" in components_to_install or "engine" in components_to_install) and "backend" not in components_to_install:
            reporter.print_step("Auto-resolving dependency: Adding 'backend'")
            components_to_install.append("backend")
            
        for comp in components_to_install:
            installer.install_component(comp, force=force_update)
        return
        
    print_help()

def repair_main():
    if len(sys.argv) < 3 or sys.argv[1] != "LMMs":
        print("Usage: LMMs-repair LMMs -<component>")
        return
        
    comp = sys.argv[2].strip("-")
    reporter.print_step(f"Repairing {comp} (Data Safe)...")
    # Mark as uninstalled so installer re-runs
    installed = installer.get_installed_components()
    if comp in installed:
        installed[comp] = False
        with open(installer.get_registry_path(), "w") as f:
            json.dump(installed, f)
            
    installer.install_component(comp)
    reporter.print_success(f"Repair complete for {comp}.")

def rebuild_main():
    if len(sys.argv) < 2 or sys.argv[1] != "LMMs":
        print("Usage: LMMs-rebuild LMMs [-ds]")
        return
        
    data_safe = "-ds" in sys.argv
    
    # Confirm destructive action
    if not data_safe:
        ans = input("WARNING: This will permanently delete ALL user data (models, chats, persona). Continue? [y/N]: ")
        if ans.lower() != 'y':
            print("Aborted.")
            return
            
    reporter.print_step("Rebuilding LMMs...")
    
    # 1. Delete code
    if LMMS_PROJECT_DIR.exists():
        reporter.print_step("Removing old code structure...")
        shutil.rmtree(LMMS_PROJECT_DIR, ignore_errors=True)
        
    # 2. Delete data if not safe
    if not data_safe and LMMS_CONFIG_DIR.exists():
        reporter.print_step("Wiping user data...")
        shutil.rmtree(LMMS_CONFIG_DIR, ignore_errors=True)
        
    # 3. Reinstall all
    reporter.print_step("Installing fresh...")
    installer.install_component("engine")
    installer.install_component("backend")
    installer.install_component("gui")
    reporter.print_success("Rebuild complete.")

def uninstall_main():
    install_dir = Path(os.path.expandvars("%LOCALAPPDATA%")) / "LMMs" / "bin" if platform.system().lower() == "windows" else Path("/usr/local/bin")
    fallback_dir = Path.home() / ".local" / "bin"
    
    if "-all" in sys.argv and "--purge" in sys.argv:
        ans = input("WARNING: This will PURGE LMMs code and ALL user data. Continue? [y/N]: ")
        if ans.lower() == 'y':
            shutil.rmtree(LMMS_PROJECT_DIR, ignore_errors=True)
            shutil.rmtree(LMMS_CONFIG_DIR, ignore_errors=True)
            
            # Remove all possible binaries
            for prefix in ["LMMs", "LMMs-Engine", "LMMs-Backend", "LMMs-GUI"]:
                bin_name = f"{prefix.lower()}.exe" if platform.system().lower() == "windows" else prefix.lower()
                (install_dir / bin_name).unlink(missing_ok=True)
                (fallback_dir / bin_name).unlink(missing_ok=True)
                
            reporter.print_success("Purge complete.")
        return
        
    for arg in sys.argv[1:]:
        if arg.startswith("--"):
            comp = arg.strip("-")
            reporter.print_step(f"Uninstalling {comp}...")
            
            installed = installer.get_installed_components()
            if comp in installed:
                installed[comp] = False
                with open(installer.get_registry_path(), "w") as f:
                    json.dump(installed, f)
                    
            # Remove specific binary
            if comp == "all": prefix = "LMMs"
            elif comp == "engine": prefix = "LMMs-Engine"
            elif comp == "backend": prefix = "LMMs-Backend"
            elif comp == "gui": prefix = "LMMs-GUI"
            else: prefix = "LMMs"
            
            bin_name = f"{prefix.lower()}.exe" if platform.system().lower() == "windows" else prefix.lower()
            (install_dir / bin_name).unlink(missing_ok=True)
            (fallback_dir / bin_name).unlink(missing_ok=True)
            
            reporter.print_success(f"{comp} uninstalled.")

def set_main():
    if len(sys.argv) < 2:
        print("Usage: LMMs-set --gui|--cli|--engine")
        return
        
    mode = sys.argv[1].strip("-")
    if mode in ["gui", "cli", "engine"]:
        config_path = LMMS_CONFIG_DIR / "config" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config = {}
        if config_path.exists():
            with open(config_path, "r") as f:
                try: config = json.load(f)
                except: pass
        config["default_mode"] = mode
        with open(config_path, "w") as f:
            json.dump(config, f)
        reporter.print_success(f"Default launcher set to: {mode}")
    else:
        print("Invalid mode.")

def lmms_main():
    mode = None
    if "--gui" in sys.argv: mode = "gui"
    elif "--cli" in sys.argv: mode = "cli"
    elif "--engine" in sys.argv: mode = "engine"
    else:
        # Load default
        config_path = LMMS_CONFIG_DIR / "config" / "config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                try: mode = json.load(f).get("default_mode", "cli")
                except: mode = "cli"
        else:
            mode = "cli"
            
    # If 'all' is installed, we should try launching the merged app first
    install_dir = Path(os.path.expandvars("%LOCALAPPDATA%")) / "LMMs" / "bin" if platform.system().lower() == "windows" else Path("/usr/local/bin")
    fallback_dir = Path.home() / ".local" / "bin"
    
    bin_name = "lmms.exe" if platform.system().lower() == "windows" else "lmms"
    unified_bin = install_dir / bin_name
    if not unified_bin.exists():
        unified_bin = fallback_dir / bin_name
        
    if unified_bin.exists():
        # Running unified standalone binary
        cmd = [str(unified_bin)]
        if mode != "cli":
            cmd.append(mode) # Passes 'gui' or 'engine' argument to unified binary
        os.execvp(str(unified_bin), cmd)
    else:
        launcher_script = LMMS_PROJECT_DIR / "lmms_launcher.py"
        if launcher_script.exists():
            os.execvp("python3", ["python3", str(launcher_script), mode])
        else:
            print("LMMs launcher not found. Please run: LMMs-builder install --all")

def cl_main():
    print_help()
