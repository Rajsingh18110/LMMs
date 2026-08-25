import sys, markdown
from PyQt6.QtWidgets import QApplication, QTextBrowser, QVBoxLayout, QWidget, QFrame
app = QApplication(sys.argv)
tb = QTextBrowser()
html = markdown.markdown("hello", extensions=["tables", "fenced_code"])
tb.setHtml(html)
print(f"HTML is: {html}")
print(f"Doc height: {tb.document().size().height()}")
