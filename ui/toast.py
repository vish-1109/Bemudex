"""Floating in-app toast notification system for Bemudex 3.0 Native Qt.
Renders pill-shaped status alerts (success, error, info) matching Bemudex 2.0.3 design.
"""

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QObject
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen

from ui.icon_provider import get_pixmap, get_icon
from services.config_manager import load_theme
from ui.themes import get_theme


class ToastNotification(QFrame):
    """Floating pill notification badge matching Bemudex 2.0.3 design."""
    dismissed = pyqtSignal(object)

    def __init__(self, message: str, toast_type: str = "success", duration_ms: int = 3500, parent=None, theme_id=None):
        super().__init__(parent)
        self.toast_type = toast_type.lower()
        self.duration_ms = duration_ms
        self.is_closing = False

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedHeight(38)
        self.setMinimumWidth(0)
        self.setMaximumWidth(600)

        # Detect theme for light/dark color adaptation
        current_theme = get_theme(theme_id or load_theme())
        is_dark = current_theme.is_dark

        # Setup colors per type and theme mode
        if self.toast_type == "success":
            self.icon_name = "check-circle"
            if is_dark:
                self.q_bg_color = QColor(14, 34, 24, 245)
                self.q_border_color = QColor(16, 185, 129, 180)
                self.text_color = "#f0fdf4"
                self.icon_color = "#10b981"
                self.btn_color = "#10b981"
                self.btn_hover_bg = "rgba(255, 255, 255, 0.12)"
            else:
                self.q_bg_color = QColor(240, 253, 244, 252)
                self.q_border_color = QColor(16, 185, 129, 230)
                self.text_color = "#064e3b"
                self.icon_color = "#059669"
                self.btn_color = "#059669"
                self.btn_hover_bg = "rgba(0, 0, 0, 0.08)"
        elif self.toast_type == "error":
            self.icon_name = "alert-triangle"
            if is_dark:
                self.q_bg_color = QColor(40, 16, 16, 245)
                self.q_border_color = QColor(239, 68, 68, 180)
                self.text_color = "#fef2f2"
                self.icon_color = "#ef4444"
                self.btn_color = "#ef4444"
                self.btn_hover_bg = "rgba(255, 255, 255, 0.12)"
            else:
                self.q_bg_color = QColor(254, 242, 242, 252)
                self.q_border_color = QColor(239, 68, 68, 230)
                self.text_color = "#7f1d1d"
                self.icon_color = "#dc2626"
                self.btn_color = "#dc2626"
                self.btn_hover_bg = "rgba(0, 0, 0, 0.08)"
        else:
            self.icon_name = "info"
            if is_dark:
                self.q_bg_color = QColor(24, 20, 44, 245)
                self.q_border_color = QColor(139, 92, 246, 180)
                self.text_color = "#f5f3ff"
                self.icon_color = "#a78bfa"
                self.btn_color = "#a78bfa"
                self.btn_hover_bg = "rgba(255, 255, 255, 0.12)"
            else:
                self.q_bg_color = QColor(245, 243, 255, 252)
                self.q_border_color = QColor(139, 92, 246, 230)
                self.text_color = "#312e81"
                self.icon_color = "#7c3aed"
                self.btn_color = "#7c3aed"
                self.btn_hover_bg = "rgba(0, 0, 0, 0.08)"

        self.setStyleSheet(f"""
            QLabel#toastMessage {{
                color: {self.text_color};
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#btnToastClose {{
                background: transparent;
                border: none;
                padding: 0px;
                border-radius: 9px;
            }}
            QPushButton#btnToastClose:hover {{
                background-color: {self.btn_hover_bg};
            }}
        """)
        self.setObjectName("toastPill")

        # Layout: [ Icon ] [ Message ] [ Close Button ]
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 12, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(18, 18)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setPixmap(get_pixmap(self.icon_name, self.icon_color, 16, stroke_width=2.2))
        layout.addWidget(self.lbl_icon)

        self.lbl_message = QLabel(message)
        self.lbl_message.setObjectName("toastMessage")
        self.lbl_message.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.lbl_message, 1)

        self.btn_close = QPushButton()
        self.btn_close.setObjectName("btnToastClose")
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setIcon(get_icon("close", self.btn_color, 12, stroke_width=2.2))
        self.btn_close.clicked.connect(self.dismiss)
        layout.addWidget(self.btn_close)

        # Auto-dismiss timer
        if self.duration_ms > 0:
            self.timer = QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.dismiss)
            self.timer.start(self.duration_ms)

        # Opacity animation for fade in
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(220)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = rect.height() / 2.0

        painter.setPen(QPen(self.q_border_color, 1.2))
        painter.setBrush(QBrush(self.q_bg_color))
        painter.drawRoundedRect(rect, radius, radius)
        painter.end()

    def dismiss(self):
        if self.is_closing:
            return
        self.is_closing = True
        self.fade_anim.stop()
        self.fade_anim.setDuration(180)
        self.fade_anim.setStartValue(self.opacity_effect.opacity())
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_anim.finished.connect(self._on_fade_out_finished)
        self.fade_anim.start()

    def _on_fade_out_finished(self):
        self.dismissed.emit(self)
        self.hide()
        self.deleteLater()


class ToastManager(QObject):
    """Floating overlay manager for MainWindow to position toasts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.active_toasts = []

        if parent:
            parent.installEventFilter(self)

    def show_toast(self, message: str, toast_type: str = "success", duration_ms: int = 3500, theme_id: str = None):
        # Remove any excess active toasts
        while len(self.active_toasts) >= 3:
            oldest = self.active_toasts.pop(0)
            oldest.dismiss()

        toast = ToastNotification(message, toast_type=toast_type, duration_ms=duration_ms, parent=self.parent_widget, theme_id=theme_id)
        toast.dismissed.connect(self._on_toast_dismissed)
        self.active_toasts.append(toast)
        toast.show()
        self.reposition_toasts()

    def _on_toast_dismissed(self, toast):
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
        self.reposition_toasts()

    def reposition_toasts(self):
        if not self.parent_widget:
            return
        parent_w = self.parent_widget.width()
        parent_h = self.parent_widget.height()

        # Stack active toasts upward from bottom-center
        bottom_offset = 28
        spacing = 8

        for toast in reversed(self.active_toasts):
            toast.adjustSize()
            toast_w = toast.width()
            toast_h = toast.height()
            x = (parent_w - toast_w) // 2
            y = parent_h - bottom_offset - toast_h
            toast.move(x, y)
            toast.raise_()
            bottom_offset += toast_h + spacing

    def eventFilter(self, obj, event):
        if obj == self.parent_widget and event.type() == event.Type.Resize:
            self.reposition_toasts()
        return super().eventFilter(obj, event)
