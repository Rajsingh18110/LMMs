import sys
import os

def main():
    # Make sure python path is correct for imports
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    import qasync
    import asyncio
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    
    # Let ui module know it's in GUI mode
    import lmms.gui.core.ui as ui
    ui.GUI_MODE = True
    
    from lmms.gui.core.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("LMMs-GUI")
    app.setApplicationDisplayName("LMMs - GUI Mode")
    app.setDesktopFileName("lmms")
    
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
    
    window = MainWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    window.show()
    
    with loop:
        sys.exit(loop.run_forever())

if __name__ == "__main__":
    main()
