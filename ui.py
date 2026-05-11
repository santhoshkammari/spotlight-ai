import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLineEdit, QVBoxLayout, QTextEdit, QDesktopWidget, QSizePolicy
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal, QObject
from PyQt5.QtGui import QPainter, QColor, QTextCursor
import threading
from slash import handle as slash_handle, get_current_model

class TokenEmitter(QObject):
    token_ready = pyqtSignal(str)

class SpotlightLLM(QWidget):
    def __init__(self, streamer):
        super().__init__()
        self.streamer = streamer
        self.dragging = False
        self.offset = None
        self.token_emitter = TokenEmitter()
        self._expanded = False
        self.initUI()
        self.response_complete = threading.Event()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.StrongFocus)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(0)

        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Ask anything...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0);
                border: none;
                padding: 5px;
                color: #FFFFFF;
                font-family: "Segoe UI", "SF Pro Display", sans-serif;
                font-size: 24px;
                font-weight: 350;
            }
        """)
        self.search_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_bar.returnPressed.connect(self.on_submit)
        self.layout.addWidget(self.search_bar)

        self.result_area = QTextEdit(self)
        self.result_area.setReadOnly(True)
        self.result_area.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                border: none;
                border-top: 1px solid rgba(255, 255, 255, 20);
                padding-top: 15px;
                margin-top: 5px;
                color: #E0E0E0;
                font-family: "Segoe UI", "SF Pro Text", sans-serif;
                font-size: 16px;
                line-height: 1.5;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 40);
                border-radius: 3px;
                min-height: 20px;
            }
        """)
        self.result_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_area.setVisible(False)
        self.layout.addWidget(self.result_area)

        self.token_emitter.token_ready.connect(self.update_result_area, Qt.QueuedConnection)

        self.setLayout(self.layout)

        screen = QDesktopWidget().screenNumber(QDesktopWidget().cursor().pos())
        screen_size = QDesktopWidget().screenGeometry(screen)
        self._screen_size = screen_size
        window_width = 750
        x = (screen_size.width() - window_width) // 2
        y = screen_size.height() // 4
        self.setGeometry(x, y, window_width, 60)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(24, 24, 24, 245))
        painter.setPen(QColor(255, 255, 255, 25))
        rect = self.rect()
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 16, 16)

    def on_submit(self):
        query = self.search_bar.text().strip()
        if not query:
            return

        if query.startswith("/"):
            result = slash_handle(query)
            if result.show_text:
                self._show(result.show_text)
            if result.new_model:
                self.search_bar.setPlaceholderText(f"model: {result.new_model.split('/')[-1]}")
            if result.prompt:
                self._run_prompt(result.prompt)
            elif not result.show_text:
                pass
            return

        self._run_prompt(query)

    def _run_prompt(self, query):
        self.result_area.setPlainText("thinking...")
        if not self._expanded:
            self.result_area.setVisible(True)
            self._expand()
        self.response_complete.clear()
        threading.Thread(target=self.get_response, args=(query,), daemon=True).start()

    def _show(self, text):
        self.result_area.setPlainText(text)
        if not self._expanded:
            self.result_area.setVisible(True)
            self._expand()

    def _expand(self):
        self._expanded = True
        x = self.x()
        y = self.y()
        w = self.width()
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(250)
        self.animation.setStartValue(QRect(x, y, w, 60))
        self.animation.setEndValue(QRect(x, y, w, 400))
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()

    def update_result_area(self, text):
        self.result_area.setPlainText(text)
        self.result_area.moveCursor(QTextCursor.End)

    def get_response(self, prompt):
        try:
            for token in self.streamer(prompt):
                self.token_emitter.token_ready.emit(token)
        except Exception as e:
            self.token_emitter.token_ready.emit(f"Error: {e}")
        finally:
            self.response_complete.set()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging and self.offset is not None:
            self.move(self.mapToGlobal(event.pos() - self.offset))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.offset = None

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.search_bar.setFocus()

    def closeEvent(self, event):
        super().closeEvent(event)


if __name__ == '__main__':
    from opencode import opencode_stream
    app = QApplication(sys.argv)
    ex = SpotlightLLM(streamer=opencode_stream)
    ex.show()
    sys.exit(app.exec_())
