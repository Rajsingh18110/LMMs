import sys
import os

def launch_main_window(icon_path):
    try:
        from lmms.gui.core.main_window import MainWindow
        from PyQt6.QtGui import QIcon
        
        window = MainWindow()
        if os.path.exists(icon_path):
            window.setWindowIcon(QIcon(icon_path))
        
        # Keep a global reference to prevent garbage collection
        global _main_window
        _main_window = window
        window.show()
    except Exception as e:
        print(f"[FATAL] MainWindow failed to load: {e}")
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "LMMs failed to start", str(e))
        except:
            pass
        sys.exit(1)

def main():
    # Make sure python path is correct for imports
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    # Handle workspace path argument (e.g. 'lmms .')
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
        if os.path.exists(target_path) and os.path.isdir(target_path):
            abs_path = os.path.abspath(target_path)
            try:
                from lmms.backend.config.config import ConfigManager
                config_mgr = ConfigManager()
                config_mgr.set("workspace_dir", abs_path)
                config_mgr.save()
                os.chdir(abs_path)
            except Exception:
                pass
                
    import qasync
    import asyncio
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    
    # Let ui module know it's in GUI mode
    import lmms.gui.core.ui as ui
    ui.GUI_MODE = True
    
    # Force native GTK file dialog on Linux (e.g. Kali/XFCE)
    if sys.platform.startswith("linux"):
        if "QT_QPA_PLATFORMTHEME" not in os.environ:
            os.environ["QT_QPA_PLATFORMTHEME"] = "gtk3"
            
    os.environ["QT_NO_DBUS"] = "1"
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false;qt.core.qobject.*=false"
    os.environ["XCOMPOSEFILE"] = "/dev/null"

    try:
        from PyQt6.QtWebEngineWidgets import QWebEngineView
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("LMMs-GUI")
    app.setApplicationDisplayName("LMMs - GUI Mode")
    app.setDesktopFileName(f"lmms-{os.getpid()}")
    
    icon_path = os.path.join(os.path.dirname(__file__), "lmms", "gui", "assets", "lmms_logo_transparent.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        
    theme_path = os.path.join(os.path.dirname(__file__), "lmms", "gui", "themes", "dark.qss")
    try:
        with open(theme_path, "r") as f:
            app.setStyleSheet(f.read())
    except Exception:
        pass

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Auto-start the background API server if it's not running
    try:
        from lmms.backend.main import auto_start_engine
        auto_start_engine()
    except Exception as e:
        print(f"Warning: Failed to auto-start engine: {e}")
    
    # Escape hatch: env var to skip splash entirely
    if os.environ.get("LMMS_SKIP_SPLASH") == "1":
        launch_main_window(icon_path)
    else:
        try:
            from lmms.gui.widgets.splash_screen import CinematicSplashScreen
            # Global reference to prevent garbage collection while async loop starts
            global _splash
            _splash = CinematicSplashScreen()
            _splash.finished.connect(lambda: launch_main_window(icon_path))
            _splash.show()
        except Exception as e:
            print(f"[Splash Error - skipping animation]: {e}")
            launch_main_window(icon_path)
    
    with loop:
        sys.exit(loop.run_forever())

if __name__ == "__main__":
    main()
