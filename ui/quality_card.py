from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from ui.icon_provider import get_pixmap


class QualityCard(QWidget):
    """Quality / Format option card."""
    selected = pyqtSignal(str)

    def __init__(
        self,
        key: str,
        value: str,
        sublabel: str,
        is_popular: bool = False,
        badge_text: str = "POPULAR",
        size_text: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.key = key
        self.is_active = False
        self.is_popular = is_popular
        self.badge_text = badge_text.upper() if badge_text else ""
        self.size_text = size_text
        self.accent_color = "#ffffff"
        self.accent_text_color = "#050505"

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(80)
        self.setMinimumWidth(80)
        self.setMaximumWidth(200)

        # Base card frame offset by 6px from top to let badge float over top border without clipping
        self.card_frame = QFrame(self)
        self.card_frame.setObjectName("qualityCardFrame")
        self.card_frame.setProperty("class", "quality-card")
        self.card_frame.setProperty("active", "false")

        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setContentsMargins(4, 4, 4, 4)
        card_layout.setSpacing(2)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_val = QLabel(value)
        self.lbl_val.setObjectName("qualityCardVal")
        self.lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.lbl_val)

        self.lbl_sub = QLabel(sublabel)
        self.lbl_sub.setObjectName("qualityCardSub")
        self.lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.lbl_sub)

        self.lbl_size = QLabel(size_text)
        self.lbl_size.setObjectName("qualityCardSize")
        self.lbl_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_size.setVisible(bool(size_text))
        card_layout.addWidget(self.lbl_size)

        # Checkmark icon for active card
        self.lbl_check = QLabel(self.card_frame)
        self.lbl_check.setFixedSize(12, 12)
        self.lbl_check.setObjectName("qualityCardCheck")
        self.lbl_check.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # Floating pill badge over top-right border
        self.lbl_badge = None
        if is_popular and self.badge_text:
            self.lbl_badge = QLabel(self.badge_text, self)
            self.lbl_badge.setObjectName("qualityPopularBadge")
            self.lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        h = self.height()
        self.card_frame.setGeometry(0, 6, w, h - 6)

        if self.lbl_badge:
            self.lbl_badge.adjustSize()
            badge_w = max(self.lbl_badge.width() + 10, 32)
            badge_h = 16
            self.lbl_badge.setGeometry(w - badge_w - 6, 0, badge_w, badge_h)
            self.lbl_badge.raise_()

        self.lbl_check.move(w - 18, 6)
        self.lbl_check.raise_()

    def sizeHint(self) -> QSize:
        return QSize(100, 80)

    def set_size_text(self, size_text: str):
        self.size_text = size_text
        self.lbl_size.setText(size_text)
        self.lbl_size.setVisible(bool(size_text))

    def set_active(self, active: bool, accent_color: str = None, accent_text_color: str = None):
        if accent_color:
            self.accent_color = accent_color
        if accent_text_color:
            self.accent_text_color = accent_text_color

        self.is_active = active
        self.card_frame.setProperty("active", "true" if active else "false")
        if active and not self.lbl_badge:
            self.lbl_check.setPixmap(get_pixmap("check", self.accent_color, 11, stroke_width=2.5))
        else:
            self.lbl_check.clear()

        if self.lbl_badge:
            self.lbl_badge.setStyleSheet(f"background-color: {self.accent_color}; color: {self.accent_text_color};")

        self.card_frame.style().unpolish(self.card_frame)
        self.card_frame.style().polish(self.card_frame)
        self.card_frame.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.key)
        super().mousePressEvent(event)


class FeatureCard(QFrame):
    """Sleek horizontal feature highlight card matching Bemudex 2.0.3 design."""
    def __init__(self, icon_name: str, title: str, desc: str, accent_color: str = "#ffffff", parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.accent_color = accent_color
        self.setProperty("class", "feature-card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(76)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Rounded square icon badge aligned to top
        self.badge_frame = QFrame()
        self.badge_frame.setObjectName("featureCardIconBadge")
        self.badge_frame.setFixedSize(34, 34)
        badge_layout = QVBoxLayout(self.badge_frame)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(16, 16)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_icon()
        badge_layout.addWidget(self.lbl_icon)

        layout.addWidget(self.badge_frame, 0, Qt.AlignmentFlag.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("featureCardTitle")
        text_layout.addWidget(self.lbl_title)

        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setObjectName("featureCardDesc")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        text_layout.addWidget(self.lbl_desc)

        layout.addLayout(text_layout, 1)

    def update_accent(self, accent_color: str):
        self.accent_color = accent_color
        self._update_icon()

    def _update_icon(self):
        self.lbl_icon.setPixmap(get_pixmap(self.icon_name, self.accent_color, 16, stroke_width=2.0))
