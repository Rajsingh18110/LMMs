"""
LMMs Standalone GUI Application Runner
Initializes the PyQt6 QtAsync desktop IDE, ensures local/remote engine connectivity, and mounts MainWindow.
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional

COLOR_RESET = "\033[0m"
COLOR_DIM = "\033[2m"
COLOR_CYAN = "\033[36m"
COLOR_GREEN = "\033[32m"
COLOR_RED = "\033[31m"
COLOR_BOLD_WHITE = "\033[1;37m"


def check_gui_prerequisites() -> bool:
    """Verifies PyQt6 and qasync packages exist."""
    try:
        import PyQt6
        import qasync
        return True
    except ImportError:
        return False


def launch_main_window(icon_path: str):
    try:
        from lmms.gui.core.main_window import MainWindow
        from PyQt6.QtGui import QIcon

        window = MainWindow()
        if os.path.exists(icon_path):
            window.setWindowIcon(QIcon(icon_path))

        global _main_window
        _main_window = window
        window.show()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.stderr.write(f"\n{COLOR_RED}✖ MainWindow initialization failed:{COLOR_RESET} {e}\n")
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "LMMs Startup Failure", str(e))
        except Exception:
            pass
        sys.exit(1)


def run_gui(args: Optional[List[str]] = None) -> None:
    """Launch the Standalone LMMs Desktop GUI."""
    if not check_gui_prerequisites():
        sys.stderr.write(f"\n{COLOR_RED}✖ GUI dependencies missing (PyQt6 or qasync).{COLOR_RESET}\n")
        sys.stderr.write(f"  To install GUI requirements, execute:\n")
        sys.stderr.write(f"  {COLOR_CYAN}lmms install --gui{COLOR_RESET}  {COLOR_DIM}(or lmms install --all){COLOR_RESET}\n\n")
        sys.exit(1)

    # Ensure python path
    gui_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(gui_dir, "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Ensure engine server is accessible or auto-start it in the background
    auto_started_server = False
    try:
        import urllib.request
        try:
            urllib.request.urlopen("http://localhost:11435/webhook", timeout=1)
        except Exception:
            from lmms.api.service import start_server_daemon, is_server_running
            if not is_server_running():
                sys.stdout.write(f"  {COLOR_DIM}Auto-starting local LMMs workstation engine daemon...{COLOR_RESET}\n")
                start_server_daemon()
                auto_started_server = True
                os.environ["LMMS_GUI_AUTO_SERVER"] = "1"
    except Exception:
        pass

    import qasync
    import asyncio
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    from PyQt6.QtCore import QTimer

    def cleanup_workstation_engine():
        """When running in Workstation GUI mode, shut down auto-started engine on window close and purge GPU VRAM."""
        if auto_started_server or os.environ.get("LMMS_GUI_AUTO_SERVER") == "1":
            try:
                from lmms.api.service import stop_server_daemon
                stop_server_daemon()
            except Exception:
                pass

    # Force native GTK theme and disable noisy Qt platform warnings on Linux
    if sys.platform.startswith("linux"):
        if "QT_QPA_PLATFORMTHEME" not in os.environ:
            os.environ["QT_QPA_PLATFORMTHEME"] = "gtk3"

    os.environ["QT_NO_DBUS"] = "1"
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false;qt.core.qobject.*=false"
    os.environ["LC_ALL"] = "C.UTF-8"

    # Flag GUI mode in core ui
    try:
        import lmms.gui.core.ui as ui
        ui.GUI_MODE = True
    except Exception:
        pass

    # Pre-import WebEngine to initialize OpenGL context before QApplication
    try:
        from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore
    except Exception:
        pass

    app_args = sys.argv[:1] + (args or [])
    sys.argv = app_args
    app = QApplication(app_args)
    app.setApplicationName("LMMs-GUI")
    app.setApplicationDisplayName("LMMs Desktop Studio")
    app.setDesktopFileName(f"lmms-{os.getpid()}")

    icon_path = os.path.join(gui_dir, "assets", "lmms_logo_transparent.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Apply modern Dark QSS theme
    theme_path = os.path.join(gui_dir, "themes", "dark.qss")
    if os.path.exists(theme_path):
        try:
            from lmms.gui.themes.theme_manager import ThemeManager
            vscode_theme_path = os.path.join(gui_dir, "themes", "vscode", "dark_vs.json")
            theme_mgr = ThemeManager(vscode_theme_path)

            with open(theme_path, "r") as f:
                base_qss = f.read()

            overrides = theme_mgr.generate_qss_overrides()
            monaco_theme_json = theme_mgr.get_monaco_theme_json()

            os.environ["LMMS_MONACO_THEME"] = monaco_theme_json or ""
            app.setStyleSheet(base_qss + "\n" + overrides)
        except Exception as e:
            sys.stderr.write(f"[Theme] Warning: Could not fully apply theme overrides: {e}\n")

    app.aboutToQuit.connect(cleanup_workstation_engine)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Defer window creation to after event loop starts
    QTimer.singleShot(0, lambda: launch_main_window(icon_path))

    exit_code = 0
    with loop:
        try:
            exit_code = loop.run_forever()
        finally:
            cleanup_workstation_engine()
    sys.exit(exit_code)


if __name__ == "__main__":
    run_gui(sys.argv[1:])
