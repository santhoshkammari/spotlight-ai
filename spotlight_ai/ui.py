import sys
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLineEdit, QVBoxLayout, QTextEdit,
    QDesktopWidget, QSizePolicy,
)
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal,
    QObject, QTimer, QPoint,
)
from PyQt5.QtGui import QPainter, QColor, QTextCursor
from spotlight_ai.slash import handle as slash_handle


WIDTH = 720
COLLAPSED_H = 64
EXPANDED_H = 420
ANIM_MS = 200


class Emitter(QObject):
    token = pyqtSignal(str)
    done = pyqtSignal()
    toggle = pyqtSignal()


class Spotlight(QWidget):
    def __init__(self, streamer):
        super().__init__()
        self.streamer = streamer
        self._expanded = False
        self._cancel = threading.Event()
        self._thread = None
        self._drag_pos = None
        self.emitter = Emitter()
        self._build_ui()
        self._center()
        self.emitter.token.connect(self._on_token, Qt.QueuedConnection)
        self.emitter.toggle.connect(self.toggle, Qt.QueuedConnection)

    def _build_ui(self):
        # Normal top-level window (appears in Alt+Tab), frameless, on top.
        self.setWindowFlags(
            Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("Spotlight")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(0)

        self.input = QLineEdit(self)
        self.input.setPlaceholderText("Ask anything...")
        self.input.setStyleSheet("""
            QLineEdit {
                background: transparent; border: none;
                color: #FFFFFF;
                font-family: "SF Pro Display","Segoe UI","Ubuntu",sans-serif;
                font-size: 22px; font-weight: 300;
                padding: 4px 0;
            }
        """)
        self.input.returnPressed.connect(self._submit)
        lay.addWidget(self.input)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setStyleSheet("""
            QTextEdit {
                background: transparent; border: none;
                border-top: 1px solid rgba(255,255,255,20);
                margin-top: 10px; padding: 12px 0 0 0;
                color: #D8D8D8;
                font-family: "SF Pro Text","Segoe UI","Ubuntu",sans-serif;
                font-size: 15px;
            }
            QScrollBar:vertical { width: 4px; background: transparent; }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,40); border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """)
        self.output.setVisible(False)
        lay.addWidget(self.output)

    def _center(self):
        s = QDesktopWidget().screenGeometry(
            QDesktopWidget().screenNumber(QDesktopWidget().cursor().pos())
        )
        self.setGeometry(
            s.x() + (s.width() - WIDTH) // 2,
            s.y() + s.height() // 4,
            WIDTH, COLLAPSED_H,
        )

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(28, 28, 30, 248))
        p.setPen(QColor(255, 255, 255, 30))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 14, 14)

    # ── toggle / show / hide ───────────────────────────────────────────────
    def toggle(self):
        if self.isVisible() and self.isActiveWindow():
            self.hide()
        else:
            self._center()  # re-center on cursor's screen each show
            self.show()
            self.raise_()
            self.activateWindow()
            self.input.setFocus()
            self.input.selectAll()

    # ── prompt flow ────────────────────────────────────────────────────────
    def _submit(self):
        q = self.input.text().strip()
        if not q:
            return
        if q.startswith("/"):
            res = slash_handle(q)
            if res.show_text:
                self._show_text(res.show_text)
            if res.new_model:
                self.input.setPlaceholderText(
                    f"model: {res.new_model.split('/')[-1]}"
                )
            if res.prompt:
                self._run(res.prompt)
            self.input.clear()
            return
        self._run(q)
        self.input.clear()

    def _run(self, query):
        self._cancel.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.3)
        self._cancel = threading.Event()
        self._show_text("…")
        self._thread = threading.Thread(
            target=self._worker, args=(query, self._cancel), daemon=True
        )
        self._thread.start()

    def _worker(self, query, cancel):
        try:
            for text in self.streamer(query, cancel_event=cancel):
                if cancel.is_set():
                    return
                self.emitter.token.emit(text)
        except Exception as e:
            self.emitter.token.emit(f"[error: {e}]")
        finally:
            self.emitter.done.emit()

    def _on_token(self, text):
        self.output.setPlainText(text)
        self.output.moveCursor(QTextCursor.End)

    def _show_text(self, t):
        self.output.setPlainText(t)
        self._expand()

    def _expand(self):
        if self._expanded:
            return
        self._expanded = True
        self.output.setVisible(True)
        self._anim(COLLAPSED_H, EXPANDED_H)

    def _collapse(self):
        if not self._expanded:
            return
        self._expanded = False
        self._anim(self.height(), COLLAPSED_H, after=self._after_collapse)

    def _after_collapse(self):
        self.output.setVisible(False)
        self.output.clear()

    def _anim(self, h0, h1, after=None):
        x, y, w = self.x(), self.y(), self.width()
        self._a = QPropertyAnimation(self, b"geometry")
        self._a.setDuration(ANIM_MS)
        self._a.setStartValue(QRect(x, y, w, h0))
        self._a.setEndValue(QRect(x, y, w, h1))
        self._a.setEasingCurve(QEasingCurve.OutCubic)
        if after:
            self._a.finished.connect(after)
        self._a.start()

    # ── events ─────────────────────────────────────────────────────────────
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self._cancel.set()
            self.hide()
        else:
            super().keyPressEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, _):
        self._drag_pos = None

    def showEvent(self, e):
        super().showEvent(e)
        self.activateWindow()
        self.raise_()
        self.input.setFocus()

    def hideEvent(self, e):
        self._cancel.set()
        # reset to collapsed for next show
        if self._expanded:
            self._expanded = False
            self.output.setVisible(False)
            self.output.clear()
            self.resize(WIDTH, COLLAPSED_H)
        self.input.clear()
        super().hideEvent(e)

    def closeEvent(self, e):
        # never destroy; just hide
        e.ignore()
        self.hide()
