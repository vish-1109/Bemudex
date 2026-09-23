import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFrame, QPushButton, QFileDialog
)

from ui.icon_provider import get_pixmap
from ui.quality_card import QualityCard
from ui.switch import Switch
from services.config_manager import save_last_folder, load_theme
from ui.themes import get_theme


def create_rounded_pixmap(pix: QPixmap, target_w: int, target_h: int, radius: int = 8) -> QPixmap:
    if pix.isNull():
        return pix
    scaled = pix.scaled(
        target_w, target_h,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation
    )
    x = max(0, (scaled.width() - target_w) // 2)
    y = max(0, (scaled.height() - target_h) // 2)
    cropped = scaled.copy(x, y, target_w, target_h)

    out = QPixmap(target_w, target_h)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    path = QPainterPath()
    path.addRoundedRect(0, 0, target_w, target_h, radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, cropped)
    painter.end()
    return out


class AudioOptionsWidget(QWidget):
    """Audio Workspace split layout."""
    audio_format_changed = pyqtSignal(str)
    bitrate_changed = pyqtSignal(str)
    folder_changed = pyqtSignal(str)

    def __init__(self, initial_folder="", parent=None):
        super().__init__(parent)
        self.active_format = "mp3"
        self.active_bitrate = "320"
        self.active_folder = initial_folder or os.path.join(os.path.expanduser("~"), "Downloads")
        self.format_cards = {}
        self.bitrate_cards = {}
        current_theme = get_theme(load_theme())
        self.accent_color = current_theme.accent
        self.accent_text_color = current_theme.accent_text
        self.is_dark = current_theme.is_dark

        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(28)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── LEFT COLUMN (190px fixed width) ──
        left_col = QVBoxLayout()
        left_col.setSpacing(14)

        # 1. Cover Art Container
        self.cover_container = QFrame()
        self.cover_container.setObjectName("audioCoverContainer")
        self.cover_container.setFixedSize(190, 190)

        cover_layout = QVBoxLayout(self.cover_container)
        cover_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_art = QLabel()
        self.lbl_art.setFixedSize(190, 190)
        self.lbl_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_art.setObjectName("audioCoverArt")
        self._set_placeholder_art()
        cover_layout.addWidget(self.lbl_art)

        # TAGGER badge inside container
        self.lbl_tagger = QLabel("TAGGER", self.cover_container)
        self.lbl_tagger.setObjectName("audioCoverBadge")
        self.lbl_tagger.setGeometry(190 - 58, 190 - 24, 50, 16)
        self.lbl_tagger.setAlignment(Qt.AlignmentFlag.AlignCenter)

        left_col.addWidget(self.cover_container)

        # 2. Track Title & Artist Metadata Inputs (14px gap to input -> 15px visual gap)
        tag_inputs = QVBoxLayout()
        tag_inputs.setSpacing(14)

        title_group = QVBoxLayout()
        title_group.setSpacing(14)
        lbl_title = QLabel("TRACK TITLE")
        lbl_title.setObjectName("audioTagLabel")
        title_group.addWidget(lbl_title)

        self.input_title = QLineEdit()
        self.input_title.setObjectName("audioTagInput")
        self.input_title.setFixedHeight(36)
        self.input_title.setPlaceholderText("Song title...")
        title_group.addWidget(self.input_title)
        tag_inputs.addLayout(title_group)

        artist_group = QVBoxLayout()
        artist_group.setSpacing(14)
        lbl_artist = QLabel("ARTIST / CHANNEL")
        lbl_artist.setObjectName("audioTagLabel")
        artist_group.addWidget(lbl_artist)

        self.input_artist = QLineEdit()
        self.input_artist.setObjectName("audioTagInput")
        self.input_artist.setFixedHeight(36)
        self.input_artist.setPlaceholderText("Artist name...")
        artist_group.addWidget(self.input_artist)
        tag_inputs.addLayout(artist_group)

        left_col.addLayout(tag_inputs)

        left_col.addStretch()
        main_layout.addLayout(left_col, 0)

        # ── RIGHT COLUMN (Flexible width) ──
        right_col = QVBoxLayout()
        right_col.setSpacing(18)

        # 1. Audio Format
        format_group = QVBoxLayout()
        format_group.setSpacing(8)

        lbl_format = QLabel("Audio Format")
        lbl_format.setProperty("class", "workspace-section-label")
        format_group.addWidget(lbl_format)

        self.format_layout = QHBoxLayout()
        self.format_layout.setSpacing(10)
        self.format_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        formats = [
            ("mp3", "MP3", "MPEG Layer 3", True, "HQ"),
            ("flac", "FLAC", "Lossless Audio", False, ""),
            ("m4a", "AAC", "Apple Audio\n(M4A)", False, ""),
            ("wav", "WAV", "Uncompressed\nPCM", False, ""),
        ]
        for key, val, sub, is_pop, badge in formats:
            card = QualityCard(key, val, sub, is_popular=is_pop, badge_text=badge)
            card.selected.connect(self._set_format)
            self.format_layout.addWidget(card, 0)
            self.format_cards[key] = card
        self.format_layout.addStretch(1)
        format_group.addLayout(self.format_layout)
        right_col.addLayout(format_group)

        # 2. Target Bitrate (for MP3 and AAC)
        self.bitrate_container = QWidget()
        bitrate_box = QVBoxLayout(self.bitrate_container)
        bitrate_box.setContentsMargins(0, 0, 0, 0)
        bitrate_box.setSpacing(8)

        lbl_bitrate = QLabel("Target Bitrate")
        lbl_bitrate.setProperty("class", "workspace-section-label")
        bitrate_box.addWidget(lbl_bitrate)

        self.bitrate_layout = QHBoxLayout()
        self.bitrate_layout.setSpacing(10)
        self.bitrate_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        bitrates = [
            ("320", "320 kbps", "Insane Quality", True, "BEST"),
            ("256", "256 kbps", "Very High", False, ""),
            ("192", "192 kbps", "High Quality", False, ""),
            ("128", "128 kbps", "Standard", False, ""),
        ]
        for key, val, sub, is_pop, badge in bitrates:
            card = QualityCard(key, val, sub, is_popular=is_pop, badge_text=badge)
            card.selected.connect(self._set_bitrate)
            self.bitrate_layout.addWidget(card, 0)
            self.bitrate_cards[key] = card
        self.bitrate_layout.addStretch(1)
        bitrate_box.addLayout(self.bitrate_layout)
        right_col.addWidget(self.bitrate_container)

        # 3. Embedding Options Container
        embed_group = QVBoxLayout()
        embed_group.setSpacing(14)

        lbl_embed = QLabel("Embedding Options")
        lbl_embed.setProperty("class", "workspace-section-label")
        embed_group.addWidget(lbl_embed)

        embed_frame = QFrame()
        embed_frame.setObjectName("audioTogglesContainer")
        embed_layout = QVBoxLayout(embed_frame)
        embed_layout.setContentsMargins(14, 8, 14, 8)
        embed_layout.setSpacing(10)

        # Row 1: Embed Artwork
        row_art = QHBoxLayout()
        lbl_row_art = QLabel("Embed Artwork Thumbnail")
        lbl_row_art.setObjectName("audioToggleLabel")
        row_art.addWidget(lbl_row_art, 1)
        self.switch_artwork = Switch(
            checked=True,
            accent_color=self.accent_color,
            accent_text_color=self.accent_text_color,
            is_dark=self.is_dark
        )
        row_art.addWidget(self.switch_artwork)
        embed_layout.addLayout(row_art)

        div1 = QFrame()
        div1.setObjectName("audioToggleDivider")
        div1.setFixedHeight(1)
        embed_layout.addWidget(div1)

        # Row 2: Write ID3 Tags
        row_id3 = QHBoxLayout()
        lbl_row_id3 = QLabel("Write ID3 Metadata Tags")
        lbl_row_id3.setObjectName("audioToggleLabel")
        row_id3.addWidget(lbl_row_id3, 1)
        self.switch_id3 = Switch(
            checked=True,
            accent_color=self.accent_color,
            accent_text_color=self.accent_text_color,
            is_dark=self.is_dark
        )
        row_id3.addWidget(self.switch_id3)
        embed_layout.addLayout(row_id3)

        div2 = QFrame()
        div2.setObjectName("audioToggleDivider")
        div2.setFixedHeight(1)
        embed_layout.addWidget(div2)

        # Row 3: Audio Chapters
        row_chap = QHBoxLayout()
        self.lbl_chapters = QLabel("Embed Audio Chapters (Not detected)")
        self.lbl_chapters.setObjectName("audioToggleLabelDisabled")
        row_chap.addWidget(self.lbl_chapters, 1)
        self.switch_chapters = Switch(
            checked=False,
            accent_color=self.accent_color,
            accent_text_color=self.accent_text_color,
            is_dark=self.is_dark
        )
        self.switch_chapters.setEnabled(False)
        row_chap.addWidget(self.switch_chapters)
        embed_layout.addLayout(row_chap)

        embed_group.addWidget(embed_frame)
        right_col.addLayout(embed_group)

        # 4. Save Location (Inside Audio workspace right column)
        folder_section = QVBoxLayout()
        folder_section.setSpacing(14)

        lbl_save = QLabel("Save to")
        lbl_save.setProperty("class", "workspace-section-label")
        folder_section.addWidget(lbl_save)

        folder_frame = QFrame()
        folder_frame.setObjectName("folderFrame")
        folder_layout = QHBoxLayout(folder_frame)
        folder_layout.setContentsMargins(14, 8, 14, 8)
        folder_layout.setSpacing(10)

        self.lbl_folder_icon = QLabel()
        folder_layout.addWidget(self.lbl_folder_icon)

        self.lbl_folder_path = QLabel(self.active_folder)
        self.lbl_folder_path.setObjectName("folderPathLabel")
        folder_layout.addWidget(self.lbl_folder_path, 1)

        btn_browse = QPushButton("Browse")
        btn_browse.setObjectName("btnBrowse")
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.clicked.connect(self._on_browse_clicked)
        folder_layout.addWidget(btn_browse)

        folder_section.addWidget(folder_frame)
        right_col.addLayout(folder_section)

        main_layout.addLayout(right_col, 1)

        # Initial active selections
        self._set_format("mp3")
        self._set_bitrate("320")
        self._update_icons()

    def _set_placeholder_art(self):
        self.lbl_art.setPixmap(get_pixmap("audio", "#555555", 36))

    def _set_format(self, fmt: str):
        self.active_format = fmt
        self.audio_format_changed.emit(fmt)

        # Show bitrate options only for lossy MP3 and AAC (M4A)
        show_bitrate = fmt in ["mp3", "m4a"]
        self.bitrate_container.setVisible(show_bitrate)

        for k, c in self.format_cards.items():
            c.set_active(k == fmt, self.accent_color, self.accent_text_color)

    def _set_bitrate(self, br: str):
        self.active_bitrate = br
        self.bitrate_changed.emit(br)
        for k, c in self.bitrate_cards.items():
            c.set_active(k == br, self.accent_color, self.accent_text_color)

    def set_folder(self, folder: str):
        if folder and os.path.exists(folder):
            self.active_folder = folder
            self.lbl_folder_path.setText(folder)

    def _on_browse_clicked(self):
        chosen = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.active_folder)
        if chosen:
            self.set_folder(chosen)
            save_last_folder(chosen)
            self.folder_changed.emit(chosen)

    def set_metadata(self, title: str, artist: str, pixmap: QPixmap = None, has_chapters: bool = False):
        if title is not None:
            self.input_title.setText(title)
            self.input_title.setCursorPosition(0)
        if artist is not None:
            self.input_artist.setText(artist)
            self.input_artist.setCursorPosition(0)

        if has_chapters:
            self.lbl_chapters.setText("Embed Audio Chapters ✓")
            self.lbl_chapters.setObjectName("audioToggleLabel")
            self.switch_chapters.setEnabled(True)
            self.switch_chapters.setChecked(True)
        else:
            self.lbl_chapters.setText("Embed Audio Chapters (Not detected)")
            self.lbl_chapters.setObjectName("audioToggleLabelDisabled")
            self.switch_chapters.setEnabled(False)
            self.switch_chapters.setChecked(False)

        if pixmap and not pixmap.isNull():
            self._current_pixmap = pixmap
            self.lbl_art.setPixmap(create_rounded_pixmap(pixmap, 190, 190, 8))
        elif pixmap is None and hasattr(self, '_current_pixmap') and self._current_pixmap and not self._current_pixmap.isNull():
            self.lbl_art.setPixmap(create_rounded_pixmap(self._current_pixmap, 190, 190, 8))
        else:
            self._set_placeholder_art()

    def clear_metadata(self):
        self._current_pixmap = None
        self.input_title.clear()
        self.input_artist.clear()
        self._set_placeholder_art()
        self.lbl_chapters.setText("Embed Audio Chapters (Not detected)")
        self.lbl_chapters.setObjectName("audioToggleLabelDisabled")
        self.switch_chapters.setEnabled(False)
        self.switch_chapters.setChecked(False)

    def set_theme_colors(self, accent: str, text: str, is_dark: bool = True):
        self.accent_color = accent
        self.accent_text_color = text
        self.is_dark = is_dark
        for k, c in self.format_cards.items():
            c.set_active(k == self.active_format, accent, text)
        for k, c in self.bitrate_cards.items():
            c.set_active(k == self.active_bitrate, accent, text)
        if hasattr(self, 'switch_artwork'):
            self.switch_artwork.set_theme(accent, text, is_dark)
        if hasattr(self, 'switch_id3'):
            self.switch_id3.set_theme(accent, text, is_dark)
        if hasattr(self, 'switch_chapters'):
            self.switch_chapters.set_theme(accent, text, is_dark)
        self._update_icons()

    def _update_icons(self):
        self.lbl_folder_icon.setPixmap(get_pixmap("folder", "#666666", 16))
