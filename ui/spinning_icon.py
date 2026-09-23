from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QWidget
from ui.icon_provider import get_pixmap


class SpinningIcon(QWidget):
    """Smooth rotating icon widget for asynchronous loading states."""

    def __init__(self, icon_name: str = "refresh", color: str = "#ffffff", size: int = 16, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._color = color
        self._size = size
        self._angle = 0.0

        self.setFixedSize(size, size)
        self._pixmap = get_pixmap(icon_name, color, size)

        self._timer = QTimer(self)
        self._timer.setInterval(30)  # ~33 fps
        self._timer.timeout.connect(self._on_tick)

    def set_color(self, color: str):
        self._color = color
        self._pixmap = get_pixmap(self._icon_name, color, self._size)
        self.update()

    def start(self):
        self._angle = 0.0
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        if self._timer.isActive():
            self._timer.stop()

    def _on_tick(self):
        self._angle = (self._angle + 9.0) % 360.0
        self.update()

    def paintEvent(self, event):
        if self._pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.translate(self.width() / 2.0, self.height() / 2.0)
        painter.rotate(self._angle)
        painter.translate(-self.width() / 2.0, -self.height() / 2.0)
        painter.drawPixmap(0, 0, self._pixmap)
        painter.end()
