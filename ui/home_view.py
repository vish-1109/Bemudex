import os
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QUrl, QTimer
from PyQt6.QtGui import QPixmap, QGuiApplication, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QFileDialog, QScrollArea
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from services.config_manager import load_last_folder, save_last_folder, load_audio_format, load_theme
from workers.metadata_worker import MetadataWorker
from ui.icon_provider import get_icon, get_pixmap
from ui.quality_card import QualityCard, FeatureCard
from ui.audio_options import AudioOptionsWidget
from ui.switch import Switch
from ui.spinning_icon import SpinningIcon
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


class HomeView(QWidget):
    """Primary Downloader screen matching Bemudex 2.0.3 design."""
    download_requested = pyqtSignal(dict)
    cancel_requested = pyqtSignal()
    folder_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("centerWidget")

        # State
        self.active_folder = load_last_folder() or os.path.join(os.path.expanduser("~"), "Downloads")
        self.active_mode = "video"       # "video" or "audio"
        self.active_quality = "best"     # "best", "4k", "1440", "1080", "720", "480"
        self.active_audio_format = load_audio_format() or "mp3"
        self.current_metadata = None
        self.meta_worker = None
        self._last_fetched_url = ""
        self.theme = get_theme(load_theme())

        # Debounced URL auto-fetch timer
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._auto_fetch_trigger)

        # Network manager for asynchronous cover thumbnail downloading
        self.network_mgr = QNetworkAccessManager(self)
        self.network_mgr.finished.connect(self._on_thumbnail_downloaded)

        # Dynamic cycling placeholder examples across supported sites
        self.PLACEHOLDER_URLS = [
            "https://www.youtube.com/watch?v=...",
            "https://soundcloud.com/artist/track...",
            "https://www.tiktok.com/@user/video/...",
            "https://vimeo.com/123456789...",
            "https://x.com/user/status/...",
        ]
        self._placeholder_idx = 0
        self._placeholder_timer = QTimer(self)
        self._placeholder_timer.setInterval(3200)
        self._placeholder_timer.timeout.connect(self._cycle_placeholder)
        self._placeholder_timer.start()

        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area with explicit objectName to prevent default white background
        self.scroll = QScrollArea()
        self.scroll.setObjectName("centerScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setMinimumWidth(300)

        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName("centerScrollWidget")
        layout = QVBoxLayout(self.scroll_widget)
        layout.setContentsMargins(52, 40, 52, 40)
        layout.setSpacing(22)

        # 1. Header: Greeting
        header_layout = QVBoxLayout()
        header_layout.setSpacing(6)
        hour = datetime.now().hour
        greeting = "Good Morning" if hour < 12 else ("Good Afternoon" if hour < 17 else "Good Evening")
        self.lbl_greeting = QLabel(greeting)
        self.lbl_greeting.setObjectName("greetingTitle")
        header_layout.addWidget(self.lbl_greeting)

        lbl_sub = QLabel("Drop a media link to begin your download • 1,750+ sites supported")
        lbl_sub.setObjectName("greetingSubtitle")
        header_layout.addWidget(lbl_sub)
        layout.addLayout(header_layout)

        # 2. Hero URL Input Bar
        url_container = QVBoxLayout()
        url_container.setSpacing(6)

        url_frame = QFrame()
        url_frame.setObjectName("urlBarFrame")
        url_layout = QHBoxLayout(url_frame)
        url_layout.setContentsMargins(12, 6, 12, 6)
        url_layout.setSpacing(10)

        self.lbl_link_icon = QLabel()
        url_layout.addWidget(self.lbl_link_icon)

        self.input_url = QLineEdit()
        self.input_url.setObjectName("urlInput")
        self.input_url.setPlaceholderText(self.PLACEHOLDER_URLS[0])
        self.input_url.textChanged.connect(self._on_url_text_changed)
        self.input_url.returnPressed.connect(self._on_fetch_clicked)
        url_layout.addWidget(self.input_url, 1)

        self.btn_clear_url = QPushButton()
        self.btn_clear_url.setObjectName("btnClearUrl")
        self.btn_clear_url.setFixedSize(22, 22)
        self.btn_clear_url.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_url.clicked.connect(self._on_clear_url)
        self.btn_clear_url.hide()
        url_layout.addWidget(self.btn_clear_url)

        self.btn_url_action = QPushButton("  Paste")
        self.btn_url_action.setObjectName("btnPaste")
        self.btn_url_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_url_action.clicked.connect(self._on_url_action_clicked)
        url_layout.addWidget(self.btn_url_action)

        url_container.addWidget(url_frame)

        # URL Input Hint Row
        hint_row = QHBoxLayout()
        hint_row.setSpacing(5)
        hint_row.setContentsMargins(4, 0, 0, 0)

        lbl_press = QLabel("Press")
        lbl_press.setObjectName("urlHintText")
        hint_row.addWidget(lbl_press)

        lbl_kbd = QLabel("Enter")
        lbl_kbd.setObjectName("urlHintKbd")
        hint_row.addWidget(lbl_kbd)

        lbl_or = QLabel("or click Fetch to analyze the link")
        lbl_or.setObjectName("urlHintText")
        hint_row.addWidget(lbl_or)
        hint_row.addStretch()

        url_container.addLayout(hint_row)
        layout.addLayout(url_container)

        # 3. Skeleton Loading Card (Hidden until fetching)
        self.card_skeleton = self._create_skeleton_card()
        self.card_skeleton.hide()
        layout.addWidget(self.card_skeleton)

        # 3b. Playlist Loading Banner (Shown when analyzing playlists)
        self.card_playlist_loading = self._create_playlist_loading_card()
        self.card_playlist_loading.hide()
        layout.addWidget(self.card_playlist_loading)

        # 4. Metadata Preview Card (Hidden until metadata arrives)
        self.card_metadata = self._create_metadata_card()
        self.card_metadata.hide()
        layout.addWidget(self.card_metadata)

        # 5. Format & Quality Workspace
        self.workspace_frame = self._create_workspace_section()
        layout.addWidget(self.workspace_frame)

        # 6. Primary Action Bar (Download Now + Cancel)
        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)

        self.btn_download = QPushButton("  Download Now")
        self.btn_download.setObjectName("btnDownload")
        self.btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download.setEnabled(False)
        self.btn_download.clicked.connect(self._on_download_clicked)
        action_layout.addWidget(self.btn_download, 1)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        action_layout.addWidget(self.btn_cancel, 0)

        layout.addLayout(action_layout)

        # 7. Status Feedback Notice
        self.lbl_status = QLabel("Ready to analyze media link.")
        self.lbl_status.setObjectName("statusNotice")
        layout.addWidget(self.lbl_status)

        # 8. Feature Showcase Row (Shown when idle, hidden when metadata is loaded)
        self.feature_cards_widget = self._create_feature_cards_section()
        layout.addWidget(self.feature_cards_widget)

        layout.addStretch()
        self.scroll.setWidget(self.scroll_widget)
        root_layout.addWidget(self.scroll)

        self._refresh_icons()

    def _create_skeleton_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card-frame")

        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        # Skeleton Thumbnail
        thumb_skel = QFrame()
        thumb_skel.setObjectName("skeletonThumb")
        thumb_skel.setFixedSize(220, 124)
        layout.addWidget(thumb_skel)

        # Skeleton Text bars
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        bar_title = QFrame()
        bar_title.setProperty("class", "skeleton-bar")
        bar_title.setFixedHeight(18)
        bar_title.setFixedWidth(320)
        info_layout.addWidget(bar_title)

        bar_channel = QFrame()
        bar_channel.setProperty("class", "skeleton-bar")
        bar_channel.setFixedHeight(14)
        bar_channel.setFixedWidth(200)
        info_layout.addWidget(bar_channel)

        bar_stats = QFrame()
        bar_stats.setProperty("class", "skeleton-bar")
        bar_stats.setFixedHeight(13)
        bar_stats.setFixedWidth(130)
        info_layout.addWidget(bar_stats)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(6)
        for w in (46, 52, 40):
            badge_bar = QFrame()
            badge_bar.setProperty("class", "skeleton-bar")
            badge_bar.setFixedSize(w, 20)
            badges_row.addWidget(badge_bar)
        badges_row.addStretch()
        info_layout.addLayout(badges_row)

        layout.addLayout(info_layout, 1)
        return card

    def _is_playlist_url(self, url: str) -> bool:
        if not url:
            return False
        u = url.lower()
        return 'list=' in u or 'playlist' in u or '/sets/' in u or 'album' in u

    def _create_playlist_loading_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("playlistLoadingCard")
        card.setMinimumHeight(115)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(6)

        layout.addStretch()

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        header_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.playlist_spinner = SpinningIcon("refresh", color="#ffffff", size=15)
        header_row.addWidget(self.playlist_spinner)

        self.lbl_playlist_title = QLabel("Analyzing playlist metadata...")
        self.lbl_playlist_title.setObjectName("playlistLoadingTitle")
        header_row.addWidget(self.lbl_playlist_title)
        layout.addLayout(header_row)

        self.lbl_playlist_sub = QLabel("Large playlists may take some time to process.")
        self.lbl_playlist_sub.setObjectName("playlistLoadingSub")
        self.lbl_playlist_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_playlist_sub)

        self.lbl_playlist_wait = QLabel("Please wait.")
        self.lbl_playlist_wait.setObjectName("playlistLoadingWait")
        self.lbl_playlist_wait.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_playlist_wait)

        layout.addStretch()

        return card

    def show_playlist_loading(self, count: int | None = None):
        if count is not None and count > 0:
            self.lbl_playlist_title.setText(f"Playlist detected: {count} tracks")
            self.lbl_playlist_sub.setText("Analyzing playlist metadata...\nLarge playlists may take up to a minute depending on playlist size and YouTube response times.")
        else:
            self.lbl_playlist_title.setText("Analyzing playlist metadata...")
            self.lbl_playlist_sub.setText("Large playlists may take some time to process.")
        self.lbl_playlist_wait.setText("Please wait.")
        self.playlist_spinner.start()
        self.card_playlist_loading.show()

    def hide_playlist_loading(self):
        if hasattr(self, 'playlist_spinner'):
            self.playlist_spinner.stop()
        if hasattr(self, 'card_playlist_loading'):
            self.card_playlist_loading.hide()

    def _create_metadata_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card-frame")

        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(18)

        # Thumbnail with duration badge overlay
        self.thumb_container = QFrame()
        self.thumb_container.setObjectName("metaThumbContainer")
        self.thumb_container.setFixedSize(220, 124)

        self.lbl_thumb = QLabel(self.thumb_container)
        self.lbl_thumb.setObjectName("metaThumb")
        self.lbl_thumb.setGeometry(0, 0, 220, 124)
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)

        thumb_overlay_layout = QHBoxLayout(self.lbl_thumb)
        thumb_overlay_layout.setContentsMargins(0, 0, 8, 8)
        thumb_overlay_layout.addStretch()

        self.lbl_duration_badge = QLabel("0:00")
        self.lbl_duration_badge.setObjectName("durationBadge")
        self.lbl_duration_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_overlay_layout.addWidget(self.lbl_duration_badge, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self.thumb_container)

        # Details Column (vertically centered)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_meta_title = QLabel("Video Title")
        self.lbl_meta_title.setObjectName("metaTitle")
        self.lbl_meta_title.setWordWrap(True)
        info_layout.addWidget(self.lbl_meta_title)

        self.lbl_meta_channel = QLabel("Channel")
        self.lbl_meta_channel.setObjectName("metaChannel")
        info_layout.addWidget(self.lbl_meta_channel)

        self.lbl_meta_stats = QLabel("Views • Upload date")
        self.lbl_meta_stats.setObjectName("metaStats")
        info_layout.addWidget(self.lbl_meta_stats)

        # Badges row
        self.badge_layout = QHBoxLayout()
        self.badge_layout.setSpacing(6)

        self.badge_res = QLabel("1080p")
        self.badge_res.setProperty("class", "badge-pill")
        self.badge_layout.addWidget(self.badge_res)

        self.badge_av1 = QLabel("AV1")
        self.badge_av1.setProperty("class", "badge-pill-accent")
        self.badge_av1.hide()
        self.badge_layout.addWidget(self.badge_av1)

        self.badge_vp9 = QLabel("VP9")
        self.badge_vp9.setProperty("class", "badge-pill")
        self.badge_vp9.hide()
        self.badge_layout.addWidget(self.badge_vp9)

        self.badge_fps = QLabel("60fps")
        self.badge_fps.setProperty("class", "badge-pill")
        self.badge_fps.hide()
        self.badge_layout.addWidget(self.badge_fps)

        self.badge_hdr = QLabel("HDR")
        self.badge_hdr.setProperty("class", "badge-pill-accent")
        self.badge_hdr.hide()
        self.badge_layout.addWidget(self.badge_hdr)

        # MP4 badge with monitor-play icon
        self.badge_format = QFrame()
        self.badge_format.setProperty("class", "badge-pill")
        f_mp4_lay = QHBoxLayout(self.badge_format)
        f_mp4_lay.setContentsMargins(6, 2, 7, 2)
        f_mp4_lay.setSpacing(4)
        self.lbl_format_icon = QLabel()
        self.lbl_format_icon.setPixmap(get_pixmap("monitor-play", "#aaaaaa", 12))
        self.lbl_format_text = QLabel("MP4")
        self.lbl_format_text.setStyleSheet("font-size: 11px; font-weight: 600; color: #aaaaaa;")
        f_mp4_lay.addWidget(self.lbl_format_icon)
        f_mp4_lay.addWidget(self.lbl_format_text)
        self.badge_layout.addWidget(self.badge_format)

        # MP3 badge with headphones icon
        self.badge_audio = QFrame()
        self.badge_audio.setProperty("class", "badge-pill")
        f_mp3_lay = QHBoxLayout(self.badge_audio)
        f_mp3_lay.setContentsMargins(6, 2, 7, 2)
        f_mp3_lay.setSpacing(4)
        self.lbl_audio_icon = QLabel()
        self.lbl_audio_icon.setPixmap(get_pixmap("headphones", "#aaaaaa", 12))
        self.lbl_audio_text = QLabel("MP3")
        self.lbl_audio_text.setStyleSheet("font-size: 11px; font-weight: 600; color: #aaaaaa;")
        f_mp3_lay.addWidget(self.lbl_audio_icon)
        f_mp3_lay.addWidget(self.lbl_audio_text)
        self.badge_layout.addWidget(self.badge_audio)

        self.badge_layout.addStretch()
        info_layout.addLayout(self.badge_layout)

        layout.addLayout(info_layout, 1)
        return card

    def _create_workspace_section(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Format Tabs Container: [ 🎥 Video | 🎵 Audio ]
        tabs_container_row = QHBoxLayout()
        tabs_container_row.setContentsMargins(0, 0, 0, 2)
        
        self.tabs_frame = QFrame()
        self.tabs_frame.setObjectName("formatTabsContainer")
        tabs_frame_layout = QHBoxLayout(self.tabs_frame)
        tabs_frame_layout.setContentsMargins(4, 4, 4, 4)
        tabs_frame_layout.setSpacing(4)

        self.btn_tab_video = QPushButton("  Video")
        self.btn_tab_video.setProperty("class", "format-tab active")
        self.btn_tab_video.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_video.setFixedHeight(34)
        self.btn_tab_video.setMinimumWidth(100)
        self.btn_tab_video.clicked.connect(lambda: self._set_mode("video"))
        tabs_frame_layout.addWidget(self.btn_tab_video)

        self.btn_tab_audio = QPushButton("  Audio")
        self.btn_tab_audio.setProperty("class", "format-tab")
        self.btn_tab_audio.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_audio.setFixedHeight(34)
        self.btn_tab_audio.setMinimumWidth(100)
        self.btn_tab_audio.clicked.connect(lambda: self._set_mode("audio"))
        tabs_frame_layout.addWidget(self.btn_tab_audio)

        tabs_container_row.addWidget(self.tabs_frame)
        tabs_container_row.addStretch()
        layout.addLayout(tabs_container_row)

        # Video Quality Section
        self.video_options_widget = QWidget()
        self.quality_section = QVBoxLayout(self.video_options_widget)
        self.quality_section.setContentsMargins(0, 0, 0, 0)
        self.quality_section.setSpacing(18)
        self.quality_section.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Quality group
        quality_group = QVBoxLayout()
        quality_group.setSpacing(8)

        self.lbl_quality_header = QLabel("QUALITY")
        self.lbl_quality_header.setProperty("class", "workspace-section-label")
        quality_group.addWidget(self.lbl_quality_header)

        self.quality_cards_layout = QHBoxLayout()
        self.quality_cards_layout.setSpacing(10)
        self.quality_cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.quality_cards = {}

        # Default Video Options
        video_opts = [
            ("best", "Best", "Available", False, ""),
            ("4k", "4K", "UHD", False, ""),
            ("1440", "1440p", "QHD", False, ""),
            ("1080", "1080p", "FHD", True, "POPULAR"),
            ("720", "720p", "HD", False, ""),
            ("480", "480p", "SD", False, ""),
        ]

        for key, val, sub, is_pop, badge in video_opts:
            card = QualityCard(key, val, sub, is_popular=is_pop, badge_text=badge)
            card.selected.connect(self._set_quality)
            self.quality_cards_layout.addWidget(card, 0)
            self.quality_cards[key] = card
        self.quality_cards_layout.addStretch(1)

        quality_group.addLayout(self.quality_cards_layout)
        self.quality_section.addLayout(quality_group)

        # Video Options (Subtitles) Section
        self.video_options_group = QVBoxLayout()
        self.video_options_group.setSpacing(8)

        lbl_video_options = QLabel("OPTIONS")
        lbl_video_options.setProperty("class", "workspace-section-label")
        self.video_options_group.addWidget(lbl_video_options)

        video_toggles_frame = QFrame()
        video_toggles_frame.setObjectName("videoTogglesContainer")
        video_toggles_layout = QVBoxLayout(video_toggles_frame)
        video_toggles_layout.setContentsMargins(14, 10, 14, 10)
        video_toggles_layout.setSpacing(10)

        row_subs = QHBoxLayout()
        row_subs.setSpacing(10)

        self.lbl_subs_icon = QLabel()
        self.lbl_subs_icon.setPixmap(get_pixmap("subtitles", self.theme.accent, 16))
        row_subs.addWidget(self.lbl_subs_icon)

        subs_text_layout = QVBoxLayout()
        subs_text_layout.setSpacing(2)

        lbl_subs_title = QLabel("Embed Subtitles (CC)")
        lbl_subs_title.setObjectName("videoToggleLabel")
        subs_text_layout.addWidget(lbl_subs_title)

        lbl_subs_desc = QLabel("Embed English & original closed captions directly into MP4")
        lbl_subs_desc.setObjectName("videoToggleSublabel")
        subs_text_layout.addWidget(lbl_subs_desc)

        row_subs.addLayout(subs_text_layout, 1)

        self.switch_subtitles = Switch(
            checked=False,
            accent_color=self.theme.accent,
            accent_text_color=self.theme.accent_text,
            is_dark=self.theme.is_dark
        )
        row_subs.addWidget(self.switch_subtitles)
        video_toggles_layout.addLayout(row_subs)

        self.video_options_group.addWidget(video_toggles_frame)
        self.quality_section.addLayout(self.video_options_group)
        
        # Save Destination Folder Section for Video Mode
        self.video_folder_section = QVBoxLayout()
        self.video_folder_section.setSpacing(14)

        lbl_save_header = QLabel("SAVE TO")
        lbl_save_header.setProperty("class", "workspace-section-label")
        self.video_folder_section.addWidget(lbl_save_header)

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

        self.video_folder_section.addWidget(folder_frame)
        self.quality_section.addLayout(self.video_folder_section)
        
        layout.addWidget(self.video_options_widget)
        
        # Audio Options Widget
        self.audio_options_widget = AudioOptionsWidget(initial_folder=self.active_folder)
        self.audio_options_widget.audio_format_changed.connect(self._on_audio_format_changed)
        self.audio_options_widget.folder_changed.connect(self._on_audio_folder_changed)
        self.audio_options_widget.hide()
        layout.addWidget(self.audio_options_widget)

        # Set initial active quality card (Best)
        self._set_quality(self.active_quality)

        return container

    def _create_feature_cards_section(self) -> QWidget:
        container = QWidget()
        layout = QGridLayout(container)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        for i in range(3):
            layout.setColumnStretch(i, 1)

        features = [
            ("globe", "1,750+ Sites", "Supports YouTube, SoundCloud, TikTok, Vimeo, and more."),
            ("zap", "Smart Detection", "Auto-detect video info and formats."),
            ("eye-off", "Smart Info Hiding", "Hides complex codecs (AVC1, VP09, Opus) with sleek badges & file sizes."),
            ("playlists", "Playlist Support", "Download entire playlists at once."),
            ("download", "High Performance", "Multi-threaded parallel downloads."),
            ("shield", "Privacy First", "No data collection. Everything local."),
        ]

        self.feature_cards_list = []
        for i, (icon, title, desc) in enumerate(features):
            card = FeatureCard(icon, title, desc, self.theme.accent)
            self.feature_cards_list.append(card)
            row = i // 3
            col = i % 3
            layout.addWidget(card, row, col)

        return container

    def _set_mode(self, mode: str):
        self.active_mode = mode
        if mode == "video":
            self.btn_tab_video.setProperty("class", "format-tab active")
            self.btn_tab_audio.setProperty("class", "format-tab")
            self.video_options_widget.show()
            self.audio_options_widget.hide()
            
            if self.current_metadata and self.current_metadata.get('resolutions'):
                sizes = self.current_metadata.get('resolution_sizes', {})
                available_res = [h for h in self.current_metadata.get('resolutions', []) if h >= 480]
                if available_res:
                    opts = [("best", "Best", "Available", False, "", sizes.get('best', ''))]
                    for h in available_res:
                        lbl = "4K" if h >= 2160 else f"{h}p"
                        sub = "UHD" if h >= 2160 else ("QHD" if h == 1440 else ("FHD" if h == 1080 else ("HD" if h == 720 else "SD")))
                        is_pop = (h == 1080)
                        opts.append((str(h), lbl, sub, is_pop, "Popular" if is_pop else "", sizes.get(str(h), '')))
                    self._rebuild_quality_cards(opts, self.active_quality or "best")
                    self.btn_tab_video.style().polish(self.btn_tab_video)
                    self.btn_tab_audio.style().polish(self.btn_tab_audio)
                    self._refresh_tab_icons()
                    return
            self._rebuild_quality_cards([
                ("best", "Best", "Available", False, "", ""),
                ("4k", "4K", "UHD", False, "", ""),
                ("1440", "1440p", "QHD", False, "", ""),
                ("1080", "1080p", "FHD", True, "Popular", ""),
                ("720", "720p", "HD", False, "", ""),
                ("480", "480p", "SD", False, "", ""),
            ], self.active_quality or "best")
        else:
            self.btn_tab_video.setProperty("class", "format-tab")
            self.btn_tab_audio.setProperty("class", "format-tab active")
            self.video_options_widget.hide()
            self.audio_options_widget.show()
            if self.current_metadata:
                title = self.current_metadata.get("title", "")
                artist = self.current_metadata.get("channel", "")
                has_chapters = bool(self.current_metadata.get("has_chapters"))
                pix = getattr(self, '_current_thumbnail_pixmap', None)
                self.audio_options_widget.set_metadata(title, artist, pixmap=pix, has_chapters=has_chapters)

        self.btn_tab_video.style().polish(self.btn_tab_video)
        self.btn_tab_audio.style().polish(self.btn_tab_audio)
        self._refresh_tab_icons()

    def _rebuild_quality_cards(self, options: list, default_key: str):
        for card in self.quality_cards.values():
            self.quality_cards_layout.removeWidget(card)
            card.hide()
            card.setParent(None)
            card.deleteLater()
        self.quality_cards.clear()

        while self.quality_cards_layout.count() > 0:
            item = self.quality_cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        for opt in options:
            if len(opt) == 6:
                key, val, sub, is_pop, badge, size_text = opt
            else:
                key, val, sub, is_pop, badge = opt
                size_text = ""
            card = QualityCard(key, val, sub, is_popular=is_pop, badge_text=badge, size_text=size_text)
            card.selected.connect(self._set_quality)
            self.quality_cards_layout.addWidget(card, 0)
            self.quality_cards[key] = card
            card.show()
        self.quality_cards_layout.addStretch(1)

        self._set_quality(default_key)

    def _set_quality(self, val: str):
        self.active_quality = val
        for k, card in self.quality_cards.items():
            card.set_active(k == val, self.theme.accent, self.theme.accent_text)

    def _on_audio_format_changed(self, fmt: str):
        self.active_audio_format = fmt

    def _on_url_text_changed(self, text: str):
        raw = text.strip()
        has_text = bool(raw)
        self.btn_download.setEnabled(has_text)
        self.btn_clear_url.setVisible(has_text)
        if has_text:
            self.btn_url_action.setText("  Fetch")
            self.btn_url_action.setIcon(get_icon("search", self.theme.accent_text, 14))
            # Debounced auto-fetch
            is_candidate = (
                raw.startswith("http://") or raw.startswith("https://") or
                "youtube.com/" in raw or "youtu.be/" in raw
            )
            if is_candidate and raw != self._last_fetched_url:
                self._debounce_timer.start(350)
            else:
                self._debounce_timer.stop()
        else:
            self.btn_url_action.setText("  Paste")
            self.btn_url_action.setIcon(get_icon("paste", self.theme.accent_text, 14))
            self._debounce_timer.stop()
            if self.current_metadata is not None or self.card_metadata.isVisible():
                self._reset_url_state()

    def _auto_fetch_trigger(self):
        raw = self.input_url.text().strip()
        if raw and raw != self._last_fetched_url:
            self._on_fetch_clicked()

    def _cycle_placeholder(self):
        """Cycles the placeholder example across supported platforms when input is empty."""
        if not self.input_url.text().strip():
            self._placeholder_idx = (self._placeholder_idx + 1) % len(self.PLACEHOLDER_URLS)
            self.input_url.setPlaceholderText(self.PLACEHOLDER_URLS[self._placeholder_idx])

    def _on_url_action_clicked(self):
        text = self.input_url.text().strip()
        if text:
            self._on_fetch_clicked()
        else:
            self._on_paste_clicked()

    def _reset_url_state(self):
        self.card_skeleton.hide()
        self.hide_playlist_loading()
        self.card_metadata.hide()
        self.feature_cards_widget.show()
        self.current_metadata = None
        self._last_fetched_url = ""
        self.lbl_status.setText("Ready to analyze media link.")
        self.audio_options_widget.clear_metadata()
        if self.active_mode == "video":
            self._rebuild_quality_cards([
                ("best", "Best", "Available", False, "", ""),
                ("4k", "4K", "UHD", False, "", ""),
                ("1440", "1440p", "QHD", False, "", ""),
                ("1080", "1080p", "FHD", True, "POPULAR", ""),
                ("720", "720p", "HD", False, "", ""),
                ("480", "480p", "SD", False, "", ""),
            ], "best")

    def _on_clear_url(self):
        self._debounce_timer.stop()
        self.input_url.clear()
        self.btn_download.setEnabled(False)
        self._reset_url_state()

    def _on_paste_clicked(self):
        clipboard = QGuiApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.input_url.setText(text)
            self._on_fetch_clicked()

    def _on_audio_folder_changed(self, folder: str):
        self.active_folder = folder
        self.lbl_folder_path.setText(folder)
        self.folder_changed.emit(folder)

    def set_active_folder(self, folder: str):
        if folder and os.path.exists(folder):
            self.active_folder = folder
            self.lbl_folder_path.setText(folder)
            if hasattr(self, 'audio_options_widget'):
                self.audio_options_widget.set_folder(folder)

    def set_default_audio_format(self, fmt: str):
        if fmt in ["mp3", "m4a", "flac", "wav", "aac"]:
            self.active_audio_format = fmt
            if hasattr(self, 'audio_options_widget'):
                self.audio_options_widget._set_format(fmt)

    def _on_browse_clicked(self):
        chosen = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.active_folder)
        if chosen:
            self.active_folder = chosen
            self.lbl_folder_path.setText(chosen)
            save_last_folder(chosen)
            self.folder_changed.emit(chosen)

    def _on_fetch_clicked(self):
        self._debounce_timer.stop()
        url = self.input_url.text().strip()
        if not url:
            self.lbl_status.setText("⚠️ Please enter a valid URL.")
            return

        self._current_thumbnail_pixmap = None
        self.audio_options_widget.clear_metadata()

        self.btn_url_action.setEnabled(False)
        self.btn_url_action.setText("  Fetching...")
        self.btn_url_action.setIcon(get_icon("refresh", self.theme.accent_text, 14))
        self.lbl_status.setText("Analyzing video link via yt-dlp...")

        # Show skeleton loading state matching Image 3
        self.feature_cards_widget.hide()
        self.card_metadata.hide()
        self.card_skeleton.show()

        if self._is_playlist_url(url):
            self.show_playlist_loading(count=None)
            self.lbl_status.setText("Analyzing playlist link via yt-dlp...")
        else:
            self.hide_playlist_loading()
            self.lbl_status.setText("Analyzing video link via yt-dlp...")

        self.meta_worker = MetadataWorker(url)
        self.meta_worker.metadata_ready.connect(self._on_metadata_loaded)
        self.meta_worker.metadata_error.connect(self._on_metadata_failed)
        self.meta_worker.playlist_detected.connect(self._on_playlist_detected)
        self.meta_worker.start()

    @pyqtSlot(int)
    def _on_playlist_detected(self, count: int):
        self.show_playlist_loading(count=count)

    @pyqtSlot(dict)
    def _on_metadata_loaded(self, data: dict):
        self.current_metadata = data
        self._last_fetched_url = data.get('url', '')
        self.btn_url_action.setEnabled(True)
        self.btn_url_action.setText("  Fetch")
        self.btn_url_action.setIcon(get_icon("search", self.theme.accent_text, 14))
        self.lbl_status.setText(f"✓ Metadata loaded: {data.get('title', 'Media')}")

        # Populate card labels
        self.lbl_meta_title.setText(data.get('title', 'Unknown Title'))
        self.lbl_meta_channel.setText(data.get('channel', 'Unknown Channel'))

        # Also populate audio tagger fields
        self.audio_options_widget.set_metadata(
            data.get('title', ''),
            data.get('channel', ''),
            pixmap=getattr(self, '_current_thumbnail_pixmap', None),
            has_chapters=bool(data.get('has_chapters'))
        )

        stats_parts = []
        if data.get('view_str'):
            stats_parts.append(data['view_str'])
        if data.get('upload_date'):
            stats_parts.append(data['upload_date'])
        self.lbl_meta_stats.setText(" • ".join(stats_parts) if stats_parts else "")

        # Duration overlay badge
        duration_str = data.get('duration_str', '')
        if duration_str:
            self.lbl_duration_badge.setText(duration_str)
            self.lbl_duration_badge.show()
        else:
            self.lbl_duration_badge.hide()

        # Dynamic badges
        res_list = data.get('resolutions', [])
        if res_list:
            top_h = res_list[0]
            self.badge_res.setText("4K" if top_h >= 2160 else f"{top_h}p")
            self.badge_res.show()
        else:
            self.badge_res.hide()

        self.badge_av1.setVisible(bool(data.get('has_av1')))
        self.badge_vp9.setVisible(bool(data.get('has_vp9')))

        fps = data.get('fps', 0)
        if fps and fps >= 60:
            self.badge_fps.setText(f"{fps}fps")
            self.badge_fps.show()
        else:
            self.badge_fps.hide()

        self.badge_hdr.setVisible(bool(data.get('has_hdr')))
        self.badge_format.setVisible(bool(res_list))
        self.badge_audio.show()

        # Dynamic quality cards with estimated sizes
        sizes = data.get('resolution_sizes', {})
        available_res = [h for h in res_list if h >= 480]

        if available_res:
            opts = [("best", "Best", "Available", False, "", sizes.get('best', ''))]
            max_h = max(available_res)
            for h in available_res:
                lbl = "4K" if h >= 2160 else f"{h}p"
                sub = "UHD" if h >= 2160 else ("QHD" if h == 1440 else ("FHD" if h == 1080 else ("HD" if h == 720 else "SD")))
                is_pop = (h == max_h)
                opts.append((str(h), lbl, sub, is_pop, "POPULAR" if is_pop else "", sizes.get(str(h), '')))
            if self.active_mode == "video":
                self._rebuild_quality_cards(opts, "best")

        self.card_skeleton.hide()
        self.hide_playlist_loading()
        self.feature_cards_widget.hide()
        self.card_metadata.show()

        # Load cover thumbnail asynchronously
        thumb_url = data.get('thumbnail')
        if thumb_url:
            self.network_mgr.get(QNetworkRequest(QUrl(thumb_url)))

    @pyqtSlot(str)
    def _on_metadata_failed(self, err_msg: str):
        self.btn_url_action.setEnabled(True)
        self.btn_url_action.setText("  Fetch")
        self.btn_url_action.setIcon(get_icon("search", self.theme.accent_text, 14))
        self.lbl_status.setText(f"❌ Failed to fetch metadata: {err_msg}")
        self.card_skeleton.hide()
        self.hide_playlist_loading()
        self.card_metadata.hide()
        self.feature_cards_widget.show()

    @pyqtSlot(QNetworkReply)
    def _on_thumbnail_downloaded(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            pix = QPixmap()
            pix.loadFromData(reply.readAll())
            self._current_thumbnail_pixmap = pix
            rounded_pix = create_rounded_pixmap(pix, 220, 124, 8)
            self.lbl_thumb.setPixmap(rounded_pix)
            self.audio_options_widget.set_metadata(
                self.current_metadata.get("title", "") if self.current_metadata else "",
                self.current_metadata.get("channel", "") if self.current_metadata else "",
                pix,
                has_chapters=bool(self.current_metadata.get("has_chapters")) if self.current_metadata else False
            )
        reply.deleteLater()

    def _on_download_clicked(self):
        url = self.input_url.text().strip()
        if not url:
            self.lbl_status.setText("⚠️ Enter a valid URL first.")
            return

        quality = self.audio_options_widget.active_bitrate if self.active_mode == "audio" else ("best" if self.active_quality == "best" else self.active_quality)
        audio_fmt = self.active_audio_format if self.active_mode == "audio" else "mp3"
        
        meta = self.current_metadata if (self.current_metadata and self.current_metadata.get('url') == url) else {}
        
        audio_title = self.audio_options_widget.input_title.text().strip() if self.active_mode == "audio" else meta.get('title', 'Media Download')
        audio_artist = self.audio_options_widget.input_artist.text().strip() if self.active_mode == "audio" else meta.get('channel', '')

        payload = {
            'url': url,
            'folder': self.active_folder,
            'type': self.active_mode,
            'quality': quality,
            'audio_format': audio_fmt,
            'audio_bitrate': self.audio_options_widget.active_bitrate if self.active_mode == "audio" else "320",
            'embed_artwork': self.audio_options_widget.switch_artwork.isChecked() if self.active_mode == "audio" else True,
            'write_id3': self.audio_options_widget.switch_id3.isChecked() if self.active_mode == "audio" else True,
            'embed_chapters': self.audio_options_widget.switch_chapters.isChecked() if self.active_mode == "audio" else True,
            'embed_subtitles': self.switch_subtitles.isChecked() if self.active_mode == "video" else False,
            'title': audio_title,
            'artist': audio_artist,
            'thumbnail': meta.get('thumbnail', ''),
            'channel': meta.get('channel', ''),
            'duration_str': meta.get('duration_str', '')
        }
        self.download_requested.emit(payload)

    def set_downloading(self, is_downloading: bool):
        self.btn_cancel.setEnabled(is_downloading)
        if is_downloading:
            self.btn_download.setText("  Add to Queue")
            self.btn_download.setEnabled(True)
        else:
            self.btn_download.setText("  Download Now")
            self.btn_download.setEnabled(bool(self.input_url.text().strip()))

    def set_status(self, msg: str):
        self.lbl_status.setText(msg)

    def _refresh_tab_icons(self):
        self.btn_tab_video.setIcon(get_icon("video", self.theme.accent if self.active_mode == "video" else self.theme.text_muted, 17))
        self.btn_tab_audio.setIcon(get_icon("audio", self.theme.accent if self.active_mode == "audio" else self.theme.text_muted, 17))

    def _refresh_icons(self):
        self.lbl_link_icon.setPixmap(get_pixmap("link", self.theme.text_muted, 16))
        self.btn_clear_url.setIcon(get_icon("close", self.theme.text_muted, 12))

        has_text = bool(self.input_url.text().strip())
        action_icon = "search" if has_text else "paste"
        self.btn_url_action.setIcon(get_icon(action_icon, self.theme.accent_text, 14))

        self._refresh_tab_icons()

        self.lbl_folder_icon.setPixmap(get_pixmap("folder", self.theme.text_muted, 16))
        self.btn_download.setIcon(get_icon("download", self.theme.accent_text, 16))

        for card in self.quality_cards.values():
            card.set_active(card.is_active, self.theme.accent, self.theme.accent_text)

        if hasattr(self, 'feature_cards_list'):
            for fcard in self.feature_cards_list:
                fcard.update_accent(self.theme.accent)
                
        if hasattr(self, 'playlist_spinner'):
            self.playlist_spinner.set_color(self.theme.accent)

        self.audio_options_widget.set_theme_colors(self.theme.accent, self.theme.accent_text, self.theme.is_dark)
        if hasattr(self, 'lbl_subs_icon') and hasattr(self, 'switch_subtitles'):
            self.lbl_subs_icon.setPixmap(get_pixmap("subtitles", self.theme.accent, 16))
            self.switch_subtitles.set_theme(self.theme.accent, self.theme.accent_text, self.theme.is_dark)

    def apply_theme(self, theme_id: str):
        self.theme = get_theme(theme_id)
        self._refresh_icons()
