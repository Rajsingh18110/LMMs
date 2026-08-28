import os
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

class CinematicSplashScreen(QWidget):
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1280, 720) # 16:9 ratio

        # Center on screen
        try:
            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen().geometry()
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2
            )
        except Exception:
            pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.web_view = QWebEngineView(self)
        self.web_view.page().setBackgroundColor(QColor("#000000"))
        layout.addWidget(self.web_view)

        # Asset path resolution
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "intro")
        os.makedirs(assets_dir, exist_ok=True)
        
        video_path_mp4 = os.path.join(assets_dir, "intro.mp4")
        video_path_webm = os.path.join(assets_dir, "intro.webm")
        html_fallback_path = os.path.join(assets_dir, "splash.html")

        # Prioritize local video files if they exist
        if os.path.exists(video_path_mp4):
            # QWebEngineView needs a simple HTML wrapper to autoplay video seamlessly
            html_content = f"""
            <html><body style="margin:0;padding:0;background:black;overflow:hidden;">
            <video width="100%" height="100%" autoplay muted>
                <source src="file://{video_path_mp4}" type="video/mp4">
            </video>
            </body></html>
            """
            self.web_view.setHtml(html_content, QUrl.fromLocalFile(assets_dir + "/"))
            duration_ms = 6000 # default 6s
        elif os.path.exists(video_path_webm):
            html_content = f"""
            <html><body style="margin:0;padding:0;background:black;overflow:hidden;">
            <video width="100%" height="100%" autoplay muted>
                <source src="file://{video_path_webm}" type="video/webm">
            </video>
            </body></html>
            """
            self.web_view.setHtml(html_content, QUrl.fromLocalFile(assets_dir + "/"))
            duration_ms = 6000
        elif os.path.exists(html_fallback_path):
            self.web_view.setUrl(QUrl.fromLocalFile(html_fallback_path))
            duration_ms = 6000
        else:
            duration_ms = 1000 # Skip fast if no assets

        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        
        # FIX 5: Hard Timeout - regardless of what happens, close splash after 10s
        self.safety_timer = QTimer(self)
        self.safety_timer.setSingleShot(True)
        self.safety_timer.timeout.connect(self.finish_splash)
        self.safety_timer.start(10000) 

        # Normal timer for expected duration
        self.normal_timer = QTimer(self)
        self.normal_timer.setSingleShot(True)
        self.normal_timer.timeout.connect(self.start_fade_out)
        self.normal_timer.start(duration_ms)

        self.is_finishing = False

    def start_fade_out(self):
        if self.is_finishing: return
        self.fade_anim.setDuration(800) # 800ms fade out
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.fade_anim.finished.connect(self.finish_splash)
        self.fade_anim.start()

    def finish_splash(self):
        if self.is_finishing: return
        self.is_finishing = True
        self.close()
        self.finished.emit()
