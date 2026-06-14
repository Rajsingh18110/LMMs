import re
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PyQt6.QtGui import QColor, QPainter, QFont, QSyntaxHighlighter, QTextCharFormat, QTextFormat
from PyQt6.QtCore import Qt, QRect, QSize

class PythonSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlightingRules = []
        
        # Keyword format
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor("#ff7b72")) # VS Code dark keyword color
        keywordFormat.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "\\band\\b", "\\bas\\b", "\\bassert\\b", "\\bbreak\\b",
            "\\bclass\\b", "\\bcontinue\\b", "\\bdef\\b", "\\bdel\\b",
            "\\belif\\b", "\\belse\\b", "\\bexcept\\b", "\\bFalse\\b",
            "\\bfinally\\b", "\\bfor\\b", "\\bfrom\\b", "\\bglobal\\b",
            "\\bif\\b", "\\bimport\\b", "\\bin\\b", "\\bis\\b",
            "\\blambda\\b", "\\bNone\\b", "\\bnonlocal\\b", "\\bnot\\b",
            "\\bor\\b", "\\bpass\\b", "\\braise\\b", "\\breturn\\b",
            "\\bTrue\\b", "\\btry\\b", "\\bwhile\\b", "\\bwith\\b", "\\byield\\b"
        ]
        for pattern in keywords:
            self.highlightingRules.append((re.compile(pattern), keywordFormat))
            
        # Class/Function name format
        classFormat = QTextCharFormat()
        classFormat.setForeground(QColor("#d2a8ff"))
        self.highlightingRules.append((re.compile("\\bclass\\s+([A-Za-z_]+)"), classFormat))
        
        funcFormat = QTextCharFormat()
        funcFormat.setForeground(QColor("#d2a8ff"))
        self.highlightingRules.append((re.compile("\\bdef\\s+([A-Za-z_]+)"), funcFormat))

        # String format
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor("#a5d6ff"))
        self.highlightingRules.append((re.compile("\".*?\""), stringFormat))
        self.highlightingRules.append((re.compile("'.*?'"), stringFormat))
        
        # Comment format
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor("#8b949e"))
        self.highlightingRules.append((re.compile("#[^\n]*"), commentFormat))

        # Builtins and Magic
        builtinFormat = QTextCharFormat()
        builtinFormat.setForeground(QColor("#79c0ff"))
        self.highlightingRules.append((re.compile("\\bself\\b"), builtinFormat))

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, format)

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineNumberArea = LineNumberArea(self)
        
        # Set font
        font = QFont("monospace", 10)
        self.setFont(font)
        
        # Connections
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        
        # Initialization
        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()
        
        # Set colors
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0d1117;
                color: #c9d1d9;
                border: none;
                selection-background-color: #264f78;
            }
        """)

        # Add syntax highlighter placeholder
        self.highlighter = None

    def load_file(self, file_path, content):
        self.setPlainText(content)
        # Only highlight python files smaller than 150KB to avoid UI freezing
        if file_path.endswith('.py') and len(content) < 150000:
            self.highlighter = PythonSyntaxHighlighter(self.document())

    def lineNumberAreaWidth(self):
        digits = 1
        m = max(1, self.blockCount())
        while m >= 10:
            m /= 10
            digits += 1
        
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
            
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor("#161b22")
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#0d1117")) # matches editor background

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor("#484f58"))
                painter.drawText(0, top, self.lineNumberArea.width() - 5, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1
