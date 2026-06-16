import re
import subprocess
import sys
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PyQt6.QtGui import QColor, QPainter, QFont, QSyntaxHighlighter, QTextCharFormat, QTextFormat
from PyQt6.QtCore import Qt, QRect, QSize, QTimer, QThread, pyqtSignal

try:
    import pygments
    from pygments.lexers import get_lexer_for_filename
    from pygments.lexers.special import TextLexer
    import pygments.token as Token
except ImportError:
    pygments = None

class PygmentsHighlighter(QSyntaxHighlighter):
    def __init__(self, document, file_path):
        super().__init__(document)
        if pygments is None:
            self.lexer = None
            return
            
        try:
            self.lexer = get_lexer_for_filename(file_path)
        except Exception:
            self.lexer = TextLexer()
            
        self.formats = {}
        def _add_format(token_type, color_hex, bold=False):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color_hex))
            if bold: fmt.setFontWeight(QFont.Weight.Bold)
            self.formats[token_type] = fmt

        # One Dark Pro inspired theme
        _add_format(Token.Keyword, "#c678dd", bold=True)
        _add_format(Token.Keyword.Constant, "#d19a66")
        _add_format(Token.Keyword.Declaration, "#c678dd")
        _add_format(Token.Keyword.Namespace, "#c678dd")
        _add_format(Token.Keyword.Type, "#e5c07b")
        _add_format(Token.Name.Builtin, "#56b6c2")
        _add_format(Token.Name.Function, "#61afef")
        _add_format(Token.Name.Class, "#e5c07b")
        _add_format(Token.Name.Namespace, "#e5c07b")
        _add_format(Token.Name.Exception, "#e06c75")
        _add_format(Token.Name.Decorator, "#61afef")
        _add_format(Token.String, "#98c379")
        _add_format(Token.String.Doc, "#5c6370")
        _add_format(Token.Number, "#d19a66")
        _add_format(Token.Comment, "#5c6370")
        _add_format(Token.Operator, "#56b6c2")
        _add_format(Token.Operator.Word, "#c678dd")
        _add_format(Token.Punctuation, "#abb2bf")
        _add_format(Token.Text, "#abb2bf")

    def highlightBlock(self, text):
        if not text or self.lexer is None: return
        try:
            tokens = pygments.lex(text, self.lexer)
            current_pos = 0
            for token, value in tokens:
                length = len(value)
                fmt = None
                t = token
                while t is not None:
                    if t in self.formats:
                        fmt = self.formats[t]
                        break
                    t = t.parent
                
                if fmt:
                    self.setFormat(current_pos, length, fmt)
                current_pos += length
        except Exception:
            pass

class LinterThread(QThread):
    result_ready = pyqtSignal(list)
    
    def __init__(self, text, file_path):
        super().__init__()
        self.text = text
        self.file_path = file_path
        
    def run(self):
        if not self.file_path.endswith('.py'):
            self.result_ready.emit([])
            return
            
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "flake8", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=self.text)
            
            errors = []
            for line in stdout.splitlines():
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    try:
                        line_num = int(parts[1])
                        col_num = int(parts[2])
                        msg = parts[3].strip()
                        errors.append({'line': line_num, 'col': col_num, 'msg': msg})
                    except ValueError:
                        pass
            self.result_ready.emit(errors)
        except Exception as e:
            self.result_ready.emit([])

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
        
        self.highlighter = None
        self.linter_errors = []
        
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


        
        # Add Timer for linting
        self.lint_timer = QTimer(self)
        self.lint_timer.setSingleShot(True)
        self.lint_timer.setInterval(1000)
        self.lint_timer.timeout.connect(self.run_linter)
        self.textChanged.connect(self.on_text_changed)

    def load_file(self, file_path, content, disable_highlighting=False):
        self.file_path = file_path
        self.setPlainText(content)
        if not disable_highlighting:
            self.highlighter = PygmentsHighlighter(self.document(), file_path)
        self.run_linter()

    def on_text_changed(self):
        self.lint_timer.start()
        
    def run_linter(self):
        if hasattr(self, 'file_path') and self.file_path.endswith('.py'):
            self.linter_thread = LinterThread(self.toPlainText(), self.file_path)
            self.linter_thread.result_ready.connect(self.on_linter_results)
            self.linter_thread.start()
            
    def on_linter_results(self, errors):
        self.linter_errors = errors
        self.highlightCurrentLine()

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
        
        # 1. Add current line highlight
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor("#161b22")
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
            
        # 2. Add Linter zigzag red lines
        for err in self.linter_errors:
            line_num = err['line'] - 1
            col_num = err['col'] - 1
            
            sel = QTextEdit.ExtraSelection()
            sel.format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
            sel.format.setUnderlineColor(QColor("#f14c4c")) # Red zigzag line
            
            block = self.document().findBlockByNumber(line_num)
            if block.isValid():
                cursor = self.textCursor()
                cursor.setPosition(block.position() + col_num)
                cursor.select(cursor.SelectionType.WordUnderCursor)
                if not cursor.hasSelection():
                    cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.KeepAnchor)
                sel.cursor = cursor
                extraSelections.append(sel)

        self.setExtraSelections(extraSelections)

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#0d1117"))

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
