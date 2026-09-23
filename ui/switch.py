from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtWidgets import QAbstractButton, QSizePolicy


class Switch(QAbstractButton):
    """Modern toggle switch with smooth sliding animation."""
    toggled_state = pyqtSignal(bool)

    def __init__(self, parent=None, checked=True, accent_color="#ffffff", accent_text_color="#050505", is_dark=True):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(36, 20)

        self.accent_color = accent_color
        self.accent_text_color = accent_text_color
        self.is_dark = is_dark

        self._position = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"position", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.toggled.connect(self._on_toggled)

    def set_theme(self, accent_color: str, accent_text_color: str, is_dark: bool = True):
        self.accent_color = accent_color
        self.accent_text_color = accent_text_color
        self.is_dark = is_dark
        self.update()

    @pyqtProperty(float)
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos
        self.update()

    def _on_toggled(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._position)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()
        self.toggled_state.emit(checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = h / 2.0

        # Colors based on checked / disabled state & theme
        if not self.isEnabled():
            if self.is_dark:
                bg_color = QColor(255, 255, 255, 14)
                border_color = QColor(255, 255, 255, 22)
                thumb_color = QColor(255, 255, 255, 55)
            else:
                bg_color = QColor(0, 0, 0, 14)
                border_color = QColor(0, 0, 0, 22)
                thumb_color = QColor(0, 0, 0, 55)
        elif self.isChecked():
            bg_color = QColor(self.accent_color)
            border_color = QColor(self.accent_color)
            thumb_color = QColor(self.accent_text_color)
        else:
            if self.is_dark:
                bg_color = QColor(255, 255, 255, 18)
                border_color = QColor(255, 255, 255, 42)
                thumb_color = QColor(160, 160, 160)
            else:
                bg_color = QColor(0, 0, 0, 16)
                border_color = QColor(0, 0, 0, 42)
                thumb_color = QColor(115, 115, 115)

        # Draw track
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(1, 1, w - 2, h - 2, radius, radius)

        # Thumb dimensions
        thumb_diameter = h - 6
        thumb_x_min = 3
        thumb_x_max = w - thumb_diameter - 3
        current_thumb_x = thumb_x_min + (thumb_x_max - thumb_x_min) * self._position

        # Draw thumb
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(thumb_color))
        painter.drawEllipse(int(current_thumb_x), 3, int(thumb_diameter), int(thumb_diameter))
        painter.end()
