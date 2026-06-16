import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Make sure we can import lmms
sys.path.insert(0, os.path.abspath('/home/kali/Projects/LMMs'))

from lmms.gui.core.main_window import MainWindow

app = QApplication(sys.argv)
window = MainWindow()
window.resize(1400, 900)
window.show()

def capture():
    pixmap = window.grab()
    pixmap.save("/home/kali/Projects/LMMs/screenshot.png")
    app.quit()

# Give it a second to render
QTimer.singleShot(2000, capture)
app.exec()
