"""Modern styled in-app confirmation dialog for Bemudex 3.0.
Replaces native OS QMessageBox with a theme-aware frameless modal.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor

from ui.themes import get_theme, DEFAULT_THEME_ID
from ui.icon_provider import get_pixmap


class ConfirmDialog(QDialog):
    """Modern modal dialog matching Bemudex 2.0.3 design."""

    def __init__(
        self,
        parent=None,
        title: str = "Confirm Action",
        message: str = "Are you sure you want to proceed?",
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        is_destructive: bool = False,
        icon_type: str = "default",
        theme_id: str = DEFAULT_THEME_ID
    ):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(440)

        t = get_theme(theme_id)
        self.theme = t
        self.is_destructive = is_destructive
        self.icon_type = icon_type

        self._init_ui(title, message, confirm_text, cancel_text)

    def _init_ui(self, title: str, message: str, confirm_text: str, cancel_text: str):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)

        # Card container with rounded corners and border
        self.card = QFrame()
        self.card.setObjectName("confirmCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 22, 24, 22)
        card_layout.setSpacing(16)

        # Top row: Icon badge + Close button
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        # Warning / Info icon in a rounded square pill
        self.icon_badge = QLabel()
        self.icon_badge.setFixedSize(42, 42)
        self.icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self.icon_type == "warning":
            icon_name = "alert-triangle"
            icon_color = "#f59e0b"
            badge_bg = "rgba(245, 158, 11, 0.14)"
            badge_border = "rgba(245, 158, 11, 0.35)"
        elif self.is_destructive or self.icon_type == "destructive":
            icon_name = "alert-triangle"
            icon_color = "#ef4444"
            badge_bg = "rgba(239, 68, 68, 0.14)"
            badge_border = "rgba(239, 68, 68, 0.35)"
        else:
            icon_name = "info"
            icon_color = self.theme.accent
            badge_bg = self.theme.accent_subtle
            badge_border = self.theme.border

        self.icon_badge.setPixmap(get_pixmap(icon_name, icon_color, 22))
        self.icon_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_bg};
                border: 1px solid {badge_border};
                border-radius: 10px;
            }}
        """)
        top_row.addWidget(self.icon_badge)
        top_row.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.theme.text_muted};
                border: none;
                font-size: 13px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                color: {self.theme.text_primary};
                background: {self.theme.accent_subtle};
            }}
        """)
        top_row.addWidget(btn_close)
        card_layout.addLayout(top_row)

        # Content: Title & Message
        content_layout = QVBoxLayout()
        content_layout.setSpacing(8)

        if title:
            lbl_title = QLabel(title)
            lbl_title.setStyleSheet(f"""
                font-size: 16px;
                font-weight: 700;
                color: {self.theme.text_primary};
            """)
            lbl_title.setWordWrap(True)
            content_layout.addWidget(lbl_title)

        lbl_msg = QLabel(message)
        lbl_msg.setStyleSheet(f"""
            font-size: 13.5px;
            line-height: 1.45;
            color: {self.theme.text_primary if not title else self.theme.text_secondary};
            font-weight: {'500' if not title else '400'};
        """)
        lbl_msg.setWordWrap(True)
        content_layout.addWidget(lbl_msg)
        card_layout.addLayout(content_layout)

        card_layout.addSpacing(6)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        btn_cancel = QPushButton(cancel_text)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFixedHeight(36)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.btn_secondary_bg};
                border: 1px solid {self.theme.border};
                color: {self.theme.btn_secondary_text};
                font-size: 12.5px;
                font-weight: 600;
                border-radius: 8px;
                padding: 0 18px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.btn_secondary_hover};
                color: {self.theme.text_primary};
                border-color: {self.theme.border_focus};
            }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_confirm = QPushButton(confirm_text)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setFixedHeight(36)
        if self.is_destructive or self.icon_type in ("warning", "destructive"):
            btn_confirm.setStyleSheet("""
                QPushButton {
                    background-color: #dc2626;
                    border: 1px solid #ef4444;
                    color: #ffffff;
                    font-size: 12.5px;
                    font-weight: 600;
                    border-radius: 8px;
                    padding: 0 20px;
                }
                QPushButton:hover {
                    background-color: #b91c1c;
                }
            """)
        else:
            btn_confirm.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme.accent};
                    border: 1px solid {self.theme.accent};
                    color: {self.theme.accent_text};
                    font-size: 12.5px;
                    font-weight: 600;
                    border-radius: 8px;
                    padding: 0 20px;
                }}
                QPushButton:hover {{
                    background-color: {self.theme.accent_hover};
                }}
            """)
        btn_confirm.clicked.connect(self.accept)
        btn_layout.addWidget(btn_confirm)

        card_layout.addLayout(btn_layout)

        # Style card
        self.card.setStyleSheet(f"""
            QFrame#confirmCard {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border_focus};
                border-radius: 14px;
            }}
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        outer_layout.addWidget(self.card)

    @classmethod
    def ask(
        cls,
        parent=None,
        title: str = "Confirm Action",
        message: str = "Are you sure you want to proceed?",
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        is_destructive: bool = False,
        theme_id: str = DEFAULT_THEME_ID
    ) -> bool:
        """Convenience method to show dialog modally and return True if accepted."""
        dlg = cls(
            parent=parent,
            title=title,
            message=message,
            confirm_text=confirm_text,
            cancel_text=cancel_text,
            is_destructive=is_destructive,
            theme_id=theme_id
        )
        if parent:
            geo = parent.geometry()
            x = geo.x() + (geo.width() - dlg.width()) // 2
            y = geo.y() + (geo.height() - dlg.sizeHint().height()) // 2
            dlg.move(max(0, x), max(0, y))
        return dlg.exec() == QDialog.DialogCode.Accepted

    @classmethod
    def ask_overwrite(cls, parent=None, filename: str = "", theme_id: str = DEFAULT_THEME_ID) -> bool:
        """Shows overwrite confirmation dialog matching Bemudex Image 3."""
        msg = f'The file "{filename}" already exists in the destination folder. Do you want to overwrite it?'
        dlg = cls(
            parent=parent,
            title="",
            message=msg,
            confirm_text="Confirm",
            cancel_text="Cancel",
            is_destructive=True,
            icon_type="warning",
            theme_id=theme_id
        )
        if parent:
            geo = parent.geometry()
            x = geo.x() + (geo.width() - dlg.width()) // 2
            y = geo.y() + (geo.height() - dlg.sizeHint().height()) // 2
            dlg.move(max(0, x), max(0, y))
        return dlg.exec() == QDialog.DialogCode.Accepted
