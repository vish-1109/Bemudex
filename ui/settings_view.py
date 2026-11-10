import os
import sys
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QScrollArea, QFrame, QFileDialog
)

from core.version import VERSION, BUILD, RELEASE_CHANNEL
from core.constants import YT_DLP_ENGINE_DIR
from services.config_manager import (
    load_video_folder, save_video_folder, get_default_video_folder,
    load_audio_folder, save_audio_folder, get_default_audio_folder,
    load_audio_format, save_audio_format,
    load_ffmpeg_path, save_ffmpeg_path,
    load_theme, save_theme,
    load_auto_close_panel, save_auto_close_panel,
    load_ui_scale, save_ui_scale,
    load_check_updates_on_launch, save_check_updates_on_launch,
    load_cookies_source, save_cookies_source,
    load_cookies_file, save_cookies_file,
    load_crop_artwork, save_crop_artwork,
    load_sponsorblock_enabled, save_sponsorblock_enabled,
    load_compatibility_mode, save_compatibility_mode,
    load_subtitle_languages, save_subtitle_languages,
    load_auto_subtitles, save_auto_subtitles,
    load_engine_channel, save_engine_channel,
    load_desktop_notifications, save_desktop_notifications
)
from core.logger import logger
from services.dependency_manager import DependencyManager
from ui.confirm_dialog import ConfirmDialog
from ui.linux_desktop import open_url_in_browser
from ui.themes import get_available_themes, get_theme
from ui.switch import Switch
from workers.engine_worker import EngineCheckWorker, EngineUpdateWorker, EngineRollbackWorker


class SettingsView(QWidget):
    """Native Settings screen for Bemudex 3.0."""
    video_folder_changed = pyqtSignal(str)
    audio_folder_changed = pyqtSignal(str)
    folder_changed = pyqtSignal(str)
    audio_format_changed = pyqtSignal(str)
    theme_changed = pyqtSignal(str)
    ui_scale_changed = pyqtSignal(int)
    toast_requested = pyqtSignal(str, str)
    engine_status_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("centerWidget")
        self.dep_manager = DependencyManager()

        self.check_worker = None
        self.update_worker = None
        self.rollback_worker = None

        self._init_ui()
        self.refresh_all()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(52, 44, 52, 44)
        root_layout.setSpacing(24)

        # 1. Header: Title & Subtitle
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        lbl_title = QLabel("Settings")
        lbl_title.setObjectName("greetingTitle")
        header_layout.addWidget(lbl_title)

        lbl_sub = QLabel("Application preferences, engine status, and system details.")
        lbl_sub.setObjectName("greetingSubtitle")
        header_layout.addWidget(lbl_sub)

        root_layout.addLayout(header_layout)

        # 2. Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setObjectName("settingsScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setMinimumWidth(300)

        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        self.content_layout = QVBoxLayout(scroll_content)
        self.content_layout.setContentsMargins(0, 10, 8, 36)
        self.content_layout.setSpacing(26)

        # Card 1: Appearance & Theme
        self._build_appearance_card()

        # Card 2: Download Preferences
        self._build_preferences_card()

        # Card 3: Download & Playback Enhancements
        self._build_enhancements_card()

        # Card 4: Authentication & Cookies
        self._build_cookies_card()

        # Card 4: yt-dlp Engine
        self._build_engine_card()

        # Card 4: Troubleshooting
        self._build_troubleshooting_card()

        # Card 5: About Section
        self._build_about_card()

        self.content_layout.addStretch()
        self.scroll.setWidget(scroll_content)
        root_layout.addWidget(self.scroll, 1)

    # ── Section 1: Appearance & Theme ──
    def _build_appearance_card(self):
        card = QFrame()
        card.setObjectName("settingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)

        lbl_section = QLabel("APPEARANCE")
        lbl_section.setObjectName("settingsSectionTitle")
        layout.addWidget(lbl_section)

        row_theme = QHBoxLayout()
        row_theme.setSpacing(16)

        theme_text_col = QVBoxLayout()
        theme_text_col.setSpacing(4)

        lbl_theme_title = QLabel("Theme")
        lbl_theme_title.setObjectName("settingsItemTitle")
        theme_text_col.addWidget(lbl_theme_title)

        lbl_theme_desc = QLabel("Choose your preferred appearance and color palette.")
        lbl_theme_desc.setObjectName("settingsItemDesc")
        lbl_theme_desc.setWordWrap(True)
        theme_text_col.addWidget(lbl_theme_desc)
        row_theme.addLayout(theme_text_col, 1)

        self.combo_theme = QComboBox()
        self.combo_theme.setObjectName("settingsComboBox")
        self.combo_theme.setFixedWidth(180)
        self.combo_theme.setFixedHeight(38)
        for theme_id, display_name in get_available_themes():
            self.combo_theme.addItem(display_name, theme_id)

        current_theme = load_theme()
        idx = self.combo_theme.findData(current_theme)
        if idx >= 0:
            self.combo_theme.setCurrentIndex(idx)

        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)
        row_theme.addWidget(self.combo_theme)
        layout.addLayout(row_theme)

        layout.addSpacing(6)
        layout.addWidget(self._create_divider())
        layout.addSpacing(6)

        # 2. UI Scaling
        row_scale = QHBoxLayout()
        row_scale.setSpacing(16)
        scale_text_col = QVBoxLayout()
        scale_text_col.setSpacing(4)

        lbl_scale_title = QLabel("UI Scaling")
        lbl_scale_title.setObjectName("settingsItemTitle")
        scale_text_col.addWidget(lbl_scale_title)

        lbl_scale_desc = QLabel("Adjust the size of the user interface text and elements.")
        lbl_scale_desc.setObjectName("settingsItemDesc")
        lbl_scale_desc.setWordWrap(True)
        scale_text_col.addWidget(lbl_scale_desc)
        row_scale.addLayout(scale_text_col, 1)

        self.combo_scale = QComboBox()
        self.combo_scale.setObjectName("settingsComboBox")
        self.combo_scale.setFixedWidth(180)
        self.combo_scale.setFixedHeight(38)
        scale_opts = [
            ("100% (Default)", 100),
            ("110%", 110),
            ("125%", 125),
            ("150%", 150),
            ("175%", 175),
        ]
        for lbl, val in scale_opts:
            self.combo_scale.addItem(lbl, val)

        current_scale = load_ui_scale()
        s_idx = self.combo_scale.findData(current_scale)
        if s_idx >= 0:
            self.combo_scale.setCurrentIndex(s_idx)

        self.combo_scale.currentIndexChanged.connect(self._on_ui_scale_changed)
        row_scale.addWidget(self.combo_scale)
        layout.addLayout(row_scale)

        self.content_layout.addWidget(card)

    # ── Section 2: Download Preferences ──
    def _build_preferences_card(self):
        card = QFrame()
        card.setObjectName("settingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Header
        lbl_section = QLabel("DOWNLOAD PREFERENCES")
        lbl_section.setObjectName("settingsSectionTitle")
        layout.addWidget(lbl_section)

        # 1. Video Download Location
        row_vid_dir = QVBoxLayout()
        row_vid_dir.setSpacing(6)
        lbl_vid_title = QLabel("Video Download Location")
        lbl_vid_title.setObjectName("settingsItemTitle")
        row_vid_dir.addWidget(lbl_vid_title)

        lbl_vid_desc = QLabel("Downloaded video files will be saved here automatically (default: ~/Downloads/Bemudex/Videos).")
        lbl_vid_desc.setObjectName("settingsItemDesc")
        lbl_vid_desc.setWordWrap(True)
        row_vid_dir.addWidget(lbl_vid_desc)

        row_vid_dir.addSpacing(4)

        self.input_video_folder = QLineEdit()
        self.input_video_folder.setObjectName("settingsPathInput")
        self.input_video_folder.setFixedHeight(38)
        self.input_video_folder.setReadOnly(True)
        row_vid_dir.addWidget(self.input_video_folder)
        self.input_folder = self.input_video_folder  # alias for backward compatibility

        row_vid_dir.addSpacing(6)

        vid_btn_row = QHBoxLayout()
        vid_btn_row.setSpacing(10)
        btn_browse_vid = QPushButton("Browse Video Folder...")
        btn_browse_vid.setObjectName("btnSettingsAction")
        btn_browse_vid.setFixedHeight(36)
        btn_browse_vid.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse_vid.clicked.connect(self._on_browse_video_folder_clicked)
        vid_btn_row.addWidget(btn_browse_vid)

        btn_default_vid = QPushButton("Reset to Default")
        btn_default_vid.setObjectName("btnSettingsAction")
        btn_default_vid.setFixedHeight(36)
        btn_default_vid.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_default_vid.clicked.connect(self._on_reset_video_folder_clicked)
        vid_btn_row.addWidget(btn_default_vid)
        vid_btn_row.addStretch()
        row_vid_dir.addLayout(vid_btn_row)
        layout.addLayout(row_vid_dir)

        layout.addSpacing(6)
        layout.addWidget(self._create_divider())
        layout.addSpacing(6)

        # 2. Audio Download Location
        row_aud_dir = QVBoxLayout()
        row_aud_dir.setSpacing(6)
        lbl_aud_title = QLabel("Audio Download Location")
        lbl_aud_title.setObjectName("settingsItemTitle")
        row_aud_dir.addWidget(lbl_aud_title)

        lbl_aud_desc = QLabel("Downloaded music and audio tracks will be saved here automatically (default: ~/Downloads/Bemudex/Audio).")
        lbl_aud_desc.setObjectName("settingsItemDesc")
        lbl_aud_desc.setWordWrap(True)
        row_aud_dir.addWidget(lbl_aud_desc)

        row_aud_dir.addSpacing(4)

        self.input_audio_folder = QLineEdit()
        self.input_audio_folder.setObjectName("settingsPathInput")
        self.input_audio_folder.setFixedHeight(38)
        self.input_audio_folder.setReadOnly(True)
        row_aud_dir.addWidget(self.input_audio_folder)

        row_aud_dir.addSpacing(6)

        aud_btn_row = QHBoxLayout()
        aud_btn_row.setSpacing(10)
        btn_browse_aud = QPushButton("Browse Audio Folder...")
        btn_browse_aud.setObjectName("btnSettingsAction")
        btn_browse_aud.setFixedHeight(36)
        btn_browse_aud.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse_aud.clicked.connect(self._on_browse_audio_folder_clicked)
        aud_btn_row.addWidget(btn_browse_aud)

        btn_default_aud = QPushButton("Reset to Default")
        btn_default_aud.setObjectName("btnSettingsAction")
        btn_default_aud.setFixedHeight(36)
        btn_default_aud.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_default_aud.clicked.connect(self._on_reset_audio_folder_clicked)
        aud_btn_row.addWidget(btn_default_aud)
        aud_btn_row.addStretch()
        row_aud_dir.addLayout(aud_btn_row)
        layout.addLayout(row_aud_dir)

        layout.addSpacing(6)
        layout.addWidget(self._create_divider())
        layout.addSpacing(6)

        # 2. Default Audio Format
        row_audio = QHBoxLayout()
        row_audio.setSpacing(16)
        audio_text_col = QVBoxLayout()
        audio_text_col.setSpacing(4)

        lbl_audio_title = QLabel("Default Audio Format")
        lbl_audio_title.setObjectName("settingsItemTitle")
        audio_text_col.addWidget(lbl_audio_title)

        lbl_audio_desc = QLabel("Preferred audio codec when downloading music and audio tracks.")
        lbl_audio_desc.setObjectName("settingsItemDesc")
        lbl_audio_desc.setWordWrap(True)
        audio_text_col.addWidget(lbl_audio_desc)
        row_audio.addLayout(audio_text_col, 1)

        self.combo_audio = QComboBox()
        self.combo_audio.setObjectName("settingsComboBox")
        self.combo_audio.setFixedWidth(170)
        self.combo_audio.setFixedHeight(38)
        self.combo_audio.addItems(["MP3 (Standard)", "M4A (AAC)", "FLAC (Lossless)", "WAV", "AAC"])
        self.combo_audio.currentIndexChanged.connect(self._on_audio_format_changed)
        row_audio.addWidget(self.combo_audio)
        layout.addLayout(row_audio)

        layout.addSpacing(6)
        layout.addWidget(self._create_divider())
        layout.addSpacing(6)

        # 3. Auto-Close Downloads Panel on Completion
        row_close = QHBoxLayout()
        row_close.setSpacing(16)
        close_text_col = QVBoxLayout()
        close_text_col.setSpacing(4)

        lbl_close_title = QLabel("Auto-Close Downloads Panel")
        lbl_close_title.setObjectName("settingsItemTitle")
        close_text_col.addWidget(lbl_close_title)

        lbl_close_desc = QLabel("Automatically close the downloads panel when all queued downloads finish.")
        lbl_close_desc.setObjectName("settingsItemDesc")
        lbl_close_desc.setWordWrap(True)
        close_text_col.addWidget(lbl_close_desc)
        row_close.addLayout(close_text_col, 1)

        t = get_theme(load_theme())
        self.switch_auto_close = Switch(
            checked=load_auto_close_panel(),
            accent_color=t.accent,
            accent_text_color=t.accent_text,
            is_dark=t.is_dark
        )
        self.switch_auto_close.toggled_state.connect(self._on_auto_close_toggled)
        row_close.addWidget(self.switch_auto_close)
        layout.addLayout(row_close)

        layout.addSpacing(6)
        layout.addWidget(self._create_divider())
        layout.addSpacing(6)

        # 3. Desktop Notifications
        row_notify = QHBoxLayout()
        row_notify.setSpacing(16)
        notify_text_col = QVBoxLayout()
        notify_text_col.setSpacing(4)

        lbl_notify_title = QLabel("Desktop Notifications")
        lbl_notify_title.setObjectName("settingsItemTitle")
        notify_text_col.addWidget(lbl_notify_title)

        lbl_notify_desc = QLabel("Show a native system notification when a download completes in the background.")
        lbl_notify_desc.setObjectName("settingsItemDesc")
        lbl_notify_desc.setWordWrap(True)
        notify_text_col.addWidget(lbl_notify_desc)
        row_notify.addLayout(notify_text_col, 1)

        self.switch_desktop_notify = Switch(
            checked=load_desktop_notifications(),
            accent_color=t.accent,
            accent_text_color=t.accent_text,
            is_dark=t.is_dark
        )
        self.switch_desktop_notify.toggled_state.connect(self._on_desktop_notify_toggled)
        row_notify.addWidget(self.switch_desktop_notify)
        layout.addLayout(row_notify)

        layout.addSpacing(6)
        layout.addWidget(self._create_divider())
        layout.addSpacing(6)

        # 3. FFmpeg Encoder Binary
        row_ffmpeg = QVBoxLayout()
        row_ffmpeg.setSpacing(6)
        lbl_ff_title = QLabel("FFmpeg Binary Location")
        lbl_ff_title.setObjectName("settingsItemTitle")
        row_ffmpeg.addWidget(lbl_ff_title)

        self.lbl_ff_status = QLabel("Detecting FFmpeg installation...")
        self.lbl_ff_status.setObjectName("settingsItemDesc")
        self.lbl_ff_status.setWordWrap(True)
        row_ffmpeg.addWidget(self.lbl_ff_status)

        row_ffmpeg.addSpacing(4)

        self.input_ffmpeg = QLineEdit()
        self.input_ffmpeg.setObjectName("settingsPathInput")
        self.input_ffmpeg.setFixedHeight(38)
        self.input_ffmpeg.setPlaceholderText("Automatic system detection (default)")
        self.input_ffmpeg.setReadOnly(True)
        row_ffmpeg.addWidget(self.input_ffmpeg)

        row_ffmpeg.addSpacing(6)

        ff_btn_row = QHBoxLayout()
        ff_btn_row.setSpacing(10)
        btn_browse_ff = QPushButton("Browse...")
        btn_browse_ff.setObjectName("btnSettingsAction")
        btn_browse_ff.setFixedHeight(36)
        btn_browse_ff.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse_ff.clicked.connect(self._on_browse_ffmpeg_clicked)
        ff_btn_row.addWidget(btn_browse_ff)

        self.btn_auto_ff = QPushButton("Auto-Detect")
        self.btn_auto_ff.setObjectName("btnSettingsAction")
        self.btn_auto_ff.setFixedHeight(36)
        self.btn_auto_ff.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_auto_ff.clicked.connect(self._on_auto_ffmpeg_clicked)
        ff_btn_row.addWidget(self.btn_auto_ff)
        ff_btn_row.addStretch()
        row_ffmpeg.addLayout(ff_btn_row)
        layout.addLayout(row_ffmpeg)

        self.content_layout.addWidget(card)

    # ── Section 3: Download & Playback Enhancements ──
    def _build_enhancements_card(self):
        card = QFrame()
        card.setObjectName("settingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Header
        lbl_section = QLabel("DOWNLOAD & PLAYBACK ENHANCEMENTS")
        lbl_section.setObjectName("settingsSectionTitle")
        layout.addWidget(lbl_section)

        t = get_theme(load_theme())

        # 1. Device Compatibility Mode (H.264 / AAC)
        row_compat = QHBoxLayout()
        row_compat.setSpacing(16)
        compat_text_col = QVBoxLayout()
        compat_text_col.setSpacing(4)

        lbl_compat_title = QLabel("Device Compatibility Mode (H.264 / MP4)")
        lbl_compat_title.setObjectName("settingsItemTitle")
        compat_text_col.addWidget(lbl_compat_title)

        lbl_compat_desc = QLabel(
            "Prioritizes standard H.264 video and AAC audio for maximum compatibility with older smart TVs, "
            "car screens, and video editors (DaVinci Resolve, Premiere) instead of AV1/VP9."
        )
        lbl_compat_desc.setObjectName("settingsItemDesc")
        lbl_compat_desc.setWordWrap(True)
        compat_text_col.addWidget(lbl_compat_desc)
        row_compat.addLayout(compat_text_col, 1)

        self.switch_compat_mode = Switch(
            checked=load_compatibility_mode(),
            accent_color=t.accent,
            accent_text_color=t.accent_text,
            is_dark=t.is_dark
        )
        self.switch_compat_mode.toggled_state.connect(self._on_compat_mode_toggled)
        row_compat.addWidget(self.switch_compat_mode)
        layout.addLayout(row_compat)

        layout.addSpacing(6)
        layout.addWidget(self._create_divider())
        layout.addSpacing(6)

        # 2. SponsorBlock Integration
        row_sb = QHBoxLayout()
        row_sb.setSpacing(16)
        sb_text_col = QVBoxLayout()
        sb_text_col.setSpacing(4)

        lbl_sb_title = QLabel("SponsorBlock (Skip Sponsors & Intros)")
        lbl_sb_title.setObjectName("settingsItemTitle")
        sb_text_col.addWidget(lbl_sb_title)

        lbl_sb_desc = QLabel(
            "Automatically detects and splices out sponsor segments, self-promotions, interaction reminders, "
            "and filler intros from downloaded YouTube videos using crowdsourced SponsorBlock data."
        )
        lbl_sb_desc.setObjectName("settingsItemDesc")
        lbl_sb_desc.setWordWrap(True)
        sb_text_col.addWidget(lbl_sb_desc)
        row_sb.addLayout(sb_text_col, 1)

        self.switch_sponsorblock = Switch(
            checked=load_sponsorblock_enabled(),
            accent_color=t.accent,
            accent_text_color=t.accent_text,
            is_dark=t.is_dark
        )
        self.switch_sponsorblock.toggled_state.connect(self._on_sponsorblock_toggled)
        row_sb.addWidget(self.switch_sponsorblock)
        layout.addLayout(row_sb)

        layout.addSpacing(6)
        layout.addWidget(self._create_divider())
        layout.addSpacing(6)

        # 3. Crop Audio Artwork to Square 1:1
        row_crop = QHBoxLayout()
        row_crop.setSpacing(16)
        crop_text_col = QVBoxLayout()
        crop_text_col.setSpacing(4)

        lbl_crop_title = QLabel("Crop Audio Artwork to Square (1:1)")
        lbl_crop_title.setObjectName("settingsItemTitle")
        crop_text_col.addWidget(lbl_crop_title)

        lbl_crop_desc = QLabel(
            "Center-crops 16:9 widescreen thumbnails into a 1:1 square before embedding into audio files, "
            "preventing black bars and stretched cover art in music players."
        )
        lbl_crop_desc.setObjectName("settingsItemDesc")
        lbl_crop_desc.setWordWrap(True)
        crop_text_col.addWidget(lbl_crop_desc)
        row_crop.addLayout(crop_text_col, 1)

        self.switch_crop_artwork = Switch(
            checked=load_crop_artwork(),
            accent_color=t.accent,
            accent_text_color=t.accent_text,
            is_dark=t.is_dark
        )
        self.switch_crop_artwork.toggled_state.connect(self._on_crop_artwork_toggled)
        row_crop.addWidget(self.switch_crop_artwork)
        layout.addLayout(row_crop)

        layout.addSpacing(6)
        layout.addWidget(self._create_divider())
        layout.addSpacing(6)

        # 4. Preferred Subtitle Languages
        row_sub_langs = QVBoxLayout()
        row_sub_langs.setSpacing(6)

        lbl_langs_title = QLabel("Preferred Subtitle Languages")
        lbl_langs_title.setObjectName("settingsItemTitle")
        row_sub_langs.addWidget(lbl_langs_title)

        lbl_langs_desc = QLabel(
            "Comma-separated language codes to download and embed when subtitles are requested (e.g. en, en-US, es, ja, fr, de, hi)."
        )
        lbl_langs_desc.setObjectName("settingsItemDesc")
        lbl_langs_desc.setWordWrap(True)
        row_sub_langs.addWidget(lbl_langs_desc)

        row_sub_langs.addSpacing(4)

        self.input_sub_langs = QLineEdit()
        self.input_sub_langs.setObjectName("settingsPathInput")
        self.input_sub_langs.setFixedHeight(38)
        self.input_sub_langs.setPlaceholderText("en, en-US, en-GB")
        self.input_sub_langs.setText(load_subtitle_languages())
        self.input_sub_langs.editingFinished.connect(self._on_sub_langs_changed)
        row_sub_langs.addWidget(self.input_sub_langs)
        layout.addLayout(row_sub_langs)

        layout.addSpacing(6)
        layout.addWidget(self._create_divider())
        layout.addSpacing(6)

        # 5. Include Auto-Generated Subtitles
        row_auto_subs = QHBoxLayout()
        row_auto_subs.setSpacing(16)
        auto_subs_text_col = QVBoxLayout()
        auto_subs_text_col.setSpacing(4)

        lbl_auto_subs_title = QLabel("Include Auto-Generated Subtitles")
        lbl_auto_subs_title.setObjectName("settingsItemTitle")
        auto_subs_text_col.addWidget(lbl_auto_subs_title)

        lbl_auto_subs_desc = QLabel(
            "Allow downloading YouTube's automatic speech-to-text captions if no human-created subtitle tracks are found."
        )
        lbl_auto_subs_desc.setObjectName("settingsItemDesc")
        lbl_auto_subs_desc.setWordWrap(True)
        auto_subs_text_col.addWidget(lbl_auto_subs_desc)
        row_auto_subs.addLayout(auto_subs_text_col, 1)

        self.switch_auto_subs = Switch(
            checked=load_auto_subtitles(),
            accent_color=t.accent,
            accent_text_color=t.accent_text,
            is_dark=t.is_dark
        )
        self.switch_auto_subs.toggled_state.connect(self._on_auto_subs_toggled)
        row_auto_subs.addWidget(self.switch_auto_subs)
        layout.addLayout(row_auto_subs)

        self.content_layout.addWidget(card)

    # ── Section 4: Authentication & Cookies ──
    def _build_cookies_card(self):
        card = QFrame()
        card.setObjectName("settingsCard")
        self.card_cookies = card
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Header
        lbl_section = QLabel("AUTHENTICATION & COOKIES")
        lbl_section.setObjectName("settingsSectionTitle")
        layout.addWidget(lbl_section)

        # 1. Cookie Source
        row_cookies = QHBoxLayout()
        row_cookies.setSpacing(16)
        cookies_text_col = QVBoxLayout()
        cookies_text_col.setSpacing(4)

        lbl_cookie_title = QLabel("Browser Cookies Source")
        lbl_cookie_title.setObjectName("settingsItemTitle")
        cookies_text_col.addWidget(lbl_cookie_title)

        lbl_cookie_desc = QLabel(
            "Pass session cookies from your web browser or an exported cookies.txt file to bypass "
            "YouTube's 'Sign in to confirm you're not a bot' wall and access private, age-restricted, "
            "or member-only media."
        )
        lbl_cookie_desc.setObjectName("settingsItemDesc")
        lbl_cookie_desc.setWordWrap(True)
        cookies_text_col.addWidget(lbl_cookie_desc)
        row_cookies.addLayout(cookies_text_col, 1)

        self.combo_cookies = QComboBox()
        self.combo_cookies.setObjectName("settingsComboBox")
        self.combo_cookies.setFixedWidth(220)
        self.combo_cookies.setFixedHeight(38)
        cookie_options = [
            ("None (Anonymous)", "none"),
            ("Firefox", "firefox"),
            ("Google Chrome", "chrome"),
            ("Brave Browser", "brave"),
            ("Chromium", "chromium"),
            ("Custom cookies.txt File", "file"),
        ]
        for label, val in cookie_options:
            self.combo_cookies.addItem(label, val)

        self.combo_cookies.currentIndexChanged.connect(self._on_cookies_source_changed)
        row_cookies.addWidget(self.combo_cookies)
        layout.addLayout(row_cookies)

        # 2. File Picker Row (visible only when 'file' is selected)
        self.row_cookie_file = QVBoxLayout()
        self.row_cookie_file.setSpacing(6)

        lbl_file_title = QLabel("Custom Cookies File Path")
        lbl_file_title.setObjectName("settingsItemTitle")
        self.row_cookie_file.addWidget(lbl_file_title)

        self.input_cookies_file = QLineEdit()
        self.input_cookies_file.setObjectName("settingsPathInput")
        self.input_cookies_file.setFixedHeight(38)
        self.input_cookies_file.setReadOnly(True)
        self.input_cookies_file.setPlaceholderText("Select an exported cookies.txt file...")
        self.row_cookie_file.addWidget(self.input_cookies_file)

        file_btn_row = QHBoxLayout()
        file_btn_row.setSpacing(10)
        btn_browse_cookie_file = QPushButton("Browse cookies.txt...")
        btn_browse_cookie_file.setObjectName("btnSettingsAction")
        btn_browse_cookie_file.setFixedHeight(36)
        btn_browse_cookie_file.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse_cookie_file.clicked.connect(self._on_browse_cookies_file_clicked)
        file_btn_row.addWidget(btn_browse_cookie_file)

        btn_clear_cookie_file = QPushButton("Clear")
        btn_clear_cookie_file.setObjectName("btnSettingsAction")
        btn_clear_cookie_file.setFixedHeight(36)
        btn_clear_cookie_file.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear_cookie_file.clicked.connect(self._on_clear_cookies_file_clicked)
        file_btn_row.addWidget(btn_clear_cookie_file)
        file_btn_row.addStretch()
        self.row_cookie_file.addLayout(file_btn_row)

        self.cookie_file_container = QWidget()
        self.cookie_file_container.setLayout(self.row_cookie_file)
        self.cookie_file_container.setVisible(False)
        layout.addWidget(self.cookie_file_container)

        # Helpful hint
        lbl_cookie_hint = QLabel(
            "💡 Tip: On Linux, Firefox or an exported cookies.txt file works directly without requiring OS keyring access."
        )
        lbl_cookie_hint.setObjectName("settingsItemDesc")
        lbl_cookie_hint.setWordWrap(True)
        layout.addWidget(lbl_cookie_hint)

        self.content_layout.addWidget(card)
    def _build_engine_card(self):
        card = QFrame()
        card.setObjectName("settingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Header
        lbl_section = QLabel("DEPENDENCIES & SYSTEM HEALTH")
        lbl_section.setObjectName("settingsSectionTitle")
        layout.addWidget(lbl_section)

        # ── System Health Summary Banner (Image 1) ──
        self.health_frame = QFrame()
        self.health_frame.setObjectName("healthSummaryFrame")
        health_layout = QVBoxLayout(self.health_frame)
        health_layout.setContentsMargins(18, 14, 18, 14)
        health_layout.setSpacing(10)

        lbl_health_title = QLabel("SYSTEM HEALTH SUMMARY")
        lbl_health_title.setObjectName("healthSummaryHeader")
        health_layout.addWidget(lbl_health_title)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(18)
        badges_row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.lbl_health_bemudex = QLabel()
        self.lbl_health_bemudex.setObjectName("healthBadgeLabel")
        badges_row.addWidget(self.lbl_health_bemudex)

        self.lbl_health_ytdlp = QLabel()
        self.lbl_health_ytdlp.setObjectName("healthBadgeLabel")
        badges_row.addWidget(self.lbl_health_ytdlp)

        self.lbl_health_ffmpeg = QLabel()
        self.lbl_health_ffmpeg.setObjectName("healthBadgeLabel")
        badges_row.addWidget(self.lbl_health_ffmpeg)

        self.lbl_health_folder = QLabel()
        self.lbl_health_folder.setObjectName("healthBadgeLabel")
        badges_row.addWidget(self.lbl_health_folder)

        badges_row.addStretch()
        health_layout.addLayout(badges_row)

        self.lbl_health_status = QLabel("✓ Ready to Download")
        self.lbl_health_status.setObjectName("healthStatusMsg")
        health_layout.addWidget(self.lbl_health_status)

        layout.addWidget(self.health_frame)
        layout.addSpacing(6)
        layout.addWidget(self._create_divider())
        layout.addSpacing(6)

        # ── Release Channel Selector (Nightly vs Stable) ──
        row_channel = QHBoxLayout()
        row_channel.setSpacing(16)
        channel_text_col = QVBoxLayout()
        channel_text_col.setSpacing(4)

        lbl_channel_title = QLabel("yt-dlp Release Channel")
        lbl_channel_title.setObjectName("settingsItemTitle")
        channel_text_col.addWidget(lbl_channel_title)

        lbl_channel_desc = QLabel(
            "Select which release branch of yt-dlp to track. Nightly provides daily updates with the latest extractors and YouTube cipher fixes."
        )
        lbl_channel_desc.setObjectName("settingsItemDesc")
        lbl_channel_desc.setWordWrap(True)
        channel_text_col.addWidget(lbl_channel_desc)
        row_channel.addLayout(channel_text_col, 1)

        self.combo_engine_channel = QComboBox()
        self.combo_engine_channel.setObjectName("settingsComboBox")
        self.combo_engine_channel.setFixedWidth(230)
        self.combo_engine_channel.setFixedHeight(38)
        self.combo_engine_channel.addItem("Nightly (Recommended)", "nightly")
        self.combo_engine_channel.addItem("Stable (Official Releases)", "stable")
        self.combo_engine_channel.currentIndexChanged.connect(self._on_engine_channel_changed)
        row_channel.addWidget(self.combo_engine_channel)
        layout.addLayout(row_channel)

        layout.addSpacing(6)
        layout.addWidget(self._create_divider())
        layout.addSpacing(6)

        # Engine Version and Source info
        info_row = QHBoxLayout()
        info_row.setSpacing(32)

        col1 = QVBoxLayout()
        col1.setSpacing(4)
        lbl_ver_header = QLabel("Installed Version")
        lbl_ver_header.setObjectName("settingsItemDesc")
        col1.addWidget(lbl_ver_header)

        self.lbl_engine_ver = QLabel("Loading...")
        self.lbl_engine_ver.setObjectName("settingsItemTitle")
        col1.addWidget(self.lbl_engine_ver)
        info_row.addLayout(col1)

        col2 = QVBoxLayout()
        col2.setSpacing(4)
        lbl_src_header = QLabel("Engine Source")
        lbl_src_header.setObjectName("settingsItemDesc")
        col2.addWidget(lbl_src_header)

        self.lbl_engine_src = QLabel("Bundled / System")
        self.lbl_engine_src.setObjectName("settingsItemTitle")
        col2.addWidget(self.lbl_engine_src)
        info_row.addLayout(col2, 1)
        layout.addLayout(info_row)

        # Status text notification
        self.lbl_engine_status = QLabel("✓ Engine is ready.")
        self.lbl_engine_status.setObjectName("settingsNotice")
        layout.addWidget(self.lbl_engine_status)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_check_engine = QPushButton("Check for Updates")
        self.btn_check_engine.setObjectName("btnSettingsAction")
        self.btn_check_engine.setFixedHeight(36)
        self.btn_check_engine.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check_engine.clicked.connect(self._on_check_engine_clicked)
        btn_row.addWidget(self.btn_check_engine)

        self.btn_update_engine = QPushButton("Update Engine")
        self.btn_update_engine.setObjectName("btnSettingsPrimary")
        self.btn_update_engine.setFixedHeight(36)
        self.btn_update_engine.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update_engine.clicked.connect(self._on_update_engine_clicked)
        self.btn_update_engine.hide()
        btn_row.addWidget(self.btn_update_engine)

        self.btn_rollback_engine = QPushButton("Roll Back")
        self.btn_rollback_engine.setObjectName("btnSettingsAction")
        self.btn_rollback_engine.setFixedHeight(36)
        self.btn_rollback_engine.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rollback_engine.clicked.connect(self._on_rollback_engine_clicked)
        self.btn_rollback_engine.hide()
        btn_row.addWidget(self.btn_rollback_engine)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addSpacing(6)
        layout.addWidget(self._create_divider())
        layout.addSpacing(6)

        # ── Check for updates on launch (Image 3) ──
        row_check_launch = QHBoxLayout()
        row_check_launch.setSpacing(16)
        launch_text_col = QVBoxLayout()
        launch_text_col.setSpacing(4)

        lbl_launch_title = QLabel("Check for updates on launch")
        lbl_launch_title.setObjectName("settingsItemTitle")
        launch_text_col.addWidget(lbl_launch_title)

        lbl_launch_desc = QLabel("Automatically check if download engine updates are available upon starting the application.")
        lbl_launch_desc.setObjectName("settingsItemDesc")
        lbl_launch_desc.setWordWrap(True)
        launch_text_col.addWidget(lbl_launch_desc)
        row_check_launch.addLayout(launch_text_col, 1)

        t = get_theme(load_theme())
        self.switch_check_launch = Switch(
            checked=load_check_updates_on_launch(),
            accent_color=t.accent,
            accent_text_color=t.accent_text,
            is_dark=t.is_dark
        )
        self.switch_check_launch.toggled_state.connect(self._on_check_launch_toggled)
        row_check_launch.addWidget(self.switch_check_launch)
        layout.addLayout(row_check_launch)

        self.content_layout.addWidget(card)

    # ── Section 4: Troubleshooting ──
    def _build_troubleshooting_card(self):
        card = QFrame()
        card.setObjectName("settingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        lbl_section = QLabel("TROUBLESHOOTING")
        lbl_section.setObjectName("settingsSectionTitle")
        layout.addWidget(lbl_section)

        # Reset Dependency Configuration
        row_reset = QHBoxLayout()
        row_reset.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        lbl_reset_title = QLabel("Reset Dependency Configuration")
        lbl_reset_title.setObjectName("settingsItemTitle")
        text_col.addWidget(lbl_reset_title)

        lbl_reset_desc = QLabel("Remove custom paths, delete user engine overrides, and restore default autodetection settings.")
        lbl_reset_desc.setObjectName("settingsItemDesc")
        lbl_reset_desc.setWordWrap(True)
        text_col.addWidget(lbl_reset_desc)
        row_reset.addLayout(text_col, 1)

        self.btn_reset_config = QPushButton("Reset Config")
        self.btn_reset_config.setObjectName("btnSettingsWarning")
        self.btn_reset_config.setFixedHeight(36)
        self.btn_reset_config.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_config.clicked.connect(self._on_reset_dependency_config_clicked)
        row_reset.addWidget(self.btn_reset_config)

        layout.addLayout(row_reset)
        self.content_layout.addWidget(card)

    def _on_reset_dependency_config_clicked(self):
        theme_id = load_theme()
        confirmed = ConfirmDialog.ask(
            parent=self.window() or self,
            title="Reset Dependency Configuration",
            message="Reset dependency configuration? This will clear custom paths and re-run system detection.",
            confirm_text="Reset Config",
            cancel_text="Cancel",
            is_destructive=True,
            theme_id=theme_id
        )
        if not confirmed:
            return

        try:
            self.dep_manager.reset()
            self.refresh_all()
            self.toast_requested.emit("Dependency configuration reset to defaults.", "success")
            ver = self.dep_manager.versions().get("ytdlp", {}).get("version")
            self.engine_status_changed.emit({
                "status": "reset",
                "version": ver,
                "update_available": False
            })
        except Exception as e:
            logger.error(f"Failed to reset dependency configuration: {e}")
            self.toast_requested.emit("Failed to reset dependency configuration.", "error")

    # ── Section 5: About Bemudex ──
    def _build_about_card(self):
        card = QFrame()
        card.setObjectName("settingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        lbl_section = QLabel("ABOUT BEMUDEX")
        lbl_section.setObjectName("settingsSectionTitle")
        layout.addWidget(lbl_section)

        # Grid of metadata
        about_grid = QVBoxLayout()
        about_grid.setSpacing(12)

        def make_meta_row(key: str, val: str) -> QHBoxLayout:
            r = QHBoxLayout()
            r.setSpacing(16)
            k = QLabel(key)
            k.setObjectName("settingsItemDesc")
            k.setFixedWidth(160)
            v = QLabel(val)
            v.setObjectName("settingsMetaVal")
            r.addWidget(k)
            r.addWidget(v, 1)
            return r

        about_grid.addLayout(make_meta_row("Application Version", f"{VERSION} ({RELEASE_CHANNEL})"))
        about_grid.addLayout(make_meta_row("Build Number", BUILD))
        about_grid.addLayout(make_meta_row("License", "GNU General Public License v3.0 (GPLv3)"))
        about_grid.addLayout(make_meta_row("Runtime", f"Python {sys.version.split()[0]} • PyQt6 Native"))
        about_grid.addLayout(make_meta_row("Repository", "https://github.com/vish-1109/Bemudex"))
        layout.addLayout(about_grid)

        layout.addSpacing(6)

        # Open Repository button
        btn_repo = QPushButton("Open GitHub Repository")
        btn_repo.setObjectName("btnSettingsAction")
        btn_repo.setFixedHeight(36)
        btn_repo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_repo.clicked.connect(lambda: open_url_in_browser("https://github.com/vish-1109/Bemudex"))
        layout.addWidget(btn_repo, 0, Qt.AlignmentFlag.AlignLeft)

        self.content_layout.addWidget(card)

    def _create_divider(self) -> QFrame:
        div = QFrame()
        div.setObjectName("settingsDivider")
        div.setFixedHeight(1)
        return div

    # ── Data & Refresh Logic ──
    def refresh_all(self):
        """Refreshes all configuration inputs, FFmpeg detection, and engine info."""
        # 0. Theme
        theme = load_theme()
        idx = self.combo_theme.findData(theme)
        if idx >= 0 and self.combo_theme.currentIndex() != idx:
            self.combo_theme.blockSignals(True)
            self.combo_theme.setCurrentIndex(idx)
            self.combo_theme.blockSignals(False)

        # 1. Folders
        vid_folder = load_video_folder()
        self.input_video_folder.setText(vid_folder)
        aud_folder = load_audio_folder()
        self.input_audio_folder.setText(aud_folder)

        # 2. Audio Format
        fmt = load_audio_format()
        index_map = {"mp3": 0, "m4a": 1, "flac": 2, "wav": 3, "aac": 4}
        self.combo_audio.blockSignals(True)
        self.combo_audio.setCurrentIndex(index_map.get(fmt, 0))
        self.combo_audio.blockSignals(False)

        # 3. Auto-close panel toggle
        if hasattr(self, 'switch_auto_close'):
            self.switch_auto_close.setChecked(load_auto_close_panel())
        if hasattr(self, 'switch_desktop_notify'):
            self.switch_desktop_notify.setChecked(load_desktop_notifications())

        # Enhancements & Playback
        if hasattr(self, 'switch_compat_mode'):
            self.switch_compat_mode.setChecked(load_compatibility_mode())
        if hasattr(self, 'switch_sponsorblock'):
            self.switch_sponsorblock.setChecked(load_sponsorblock_enabled())
        if hasattr(self, 'switch_crop_artwork'):
            self.switch_crop_artwork.setChecked(load_crop_artwork())
        if hasattr(self, 'input_sub_langs'):
            self.input_sub_langs.setText(load_subtitle_languages())
        if hasattr(self, 'switch_auto_subs'):
            self.switch_auto_subs.setChecked(load_auto_subtitles())

        # UI Scaling combo
        if hasattr(self, 'combo_scale'):
            scale = load_ui_scale()
            s_idx = self.combo_scale.findData(scale)
            if s_idx >= 0 and self.combo_scale.currentIndex() != s_idx:
                self.combo_scale.blockSignals(True)
                self.combo_scale.setCurrentIndex(s_idx)
                self.combo_scale.blockSignals(False)

        # Check updates on launch toggle
        if hasattr(self, 'switch_check_launch'):
            self.switch_check_launch.setChecked(load_check_updates_on_launch())

        # Cookies Source & Custom File
        if hasattr(self, 'combo_cookies'):
            c_src = load_cookies_source()
            c_idx = self.combo_cookies.findData(c_src)
            if c_idx >= 0 and self.combo_cookies.currentIndex() != c_idx:
                self.combo_cookies.blockSignals(True)
                self.combo_cookies.setCurrentIndex(c_idx)
                self.combo_cookies.blockSignals(False)
            if hasattr(self, 'cookie_file_container'):
                self.cookie_file_container.setVisible(c_src == "file")
        if hasattr(self, 'input_cookies_file'):
            self.input_cookies_file.setText(load_cookies_file())

        # 3. FFmpeg
        ff_info = self.dep_manager.detect()
        custom_ff = load_ffmpeg_path()
        if custom_ff:
            self.input_ffmpeg.setText(custom_ff)
            if ff_info.get("installed"):
                self.lbl_ff_status.setText(f"✓ Custom FFmpeg active (version {ff_info.get('version', 'unknown')})")
            else:
                self.lbl_ff_status.setText("⚠️ Custom path is invalid or unexecutable")
        else:
            self.input_ffmpeg.setText("")
            if ff_info.get("installed"):
                self.lbl_ff_status.setText(f"✓ System FFmpeg detected at {ff_info.get('path')} (version {ff_info.get('version')})")
            else:
                self.lbl_ff_status.setText("⚠️ FFmpeg was not detected on system PATH")

        # 4. Engine Version & Source
        versions = self.dep_manager.versions()
        ytdlp_ver = versions.get("ytdlp", {}).get("version", "Unknown")
        self.lbl_engine_ver.setText(ytdlp_ver)

        is_user_engine = os.path.exists(YT_DLP_ENGINE_DIR) and os.path.exists(os.path.join(YT_DLP_ENGINE_DIR, "__init__.py"))
        self.lbl_engine_src.setText("User override (~/.bemudex/engine)" if is_user_engine else "Bundled / System package")

        # 5. Engine Channel
        if hasattr(self, 'combo_engine_channel'):
            ch = load_engine_channel()
            ch_idx = self.combo_engine_channel.findData(ch)
            if ch_idx >= 0 and self.combo_engine_channel.currentIndex() != ch_idx:
                self.combo_engine_channel.blockSignals(True)
                self.combo_engine_channel.setCurrentIndex(ch_idx)
                self.combo_engine_channel.blockSignals(False)

        # Rollback button visibility
        can_rollback = self.dep_manager.can_rollback()
        self.btn_rollback_engine.setVisible(can_rollback)

        # 5. Health Summary
        self.update_health_summary()

    def update_folder(self, folder: str = ""):
        """Synchronizes folder display when changed externally from HomeView."""
        if hasattr(self, 'input_video_folder'):
            self.input_video_folder.setText(load_video_folder())
        if hasattr(self, 'input_audio_folder'):
            self.input_audio_folder.setText(load_audio_folder())
        self.update_health_summary()

    def apply_theme(self, theme_id: str):
        t = get_theme(theme_id)
        if hasattr(self, 'switch_auto_close'):
            self.switch_auto_close.set_theme(t.accent, t.accent_text, t.is_dark)
        if hasattr(self, 'switch_desktop_notify'):
            self.switch_desktop_notify.set_theme(t.accent, t.accent_text, t.is_dark)
        if hasattr(self, 'switch_check_launch'):
            self.switch_check_launch.set_theme(t.accent, t.accent_text, t.is_dark)
        if hasattr(self, 'switch_compat_mode'):
            self.switch_compat_mode.set_theme(t.accent, t.accent_text, t.is_dark)
        if hasattr(self, 'switch_sponsorblock'):
            self.switch_sponsorblock.set_theme(t.accent, t.accent_text, t.is_dark)
        if hasattr(self, 'switch_crop_artwork'):
            self.switch_crop_artwork.set_theme(t.accent, t.accent_text, t.is_dark)
        if hasattr(self, 'switch_auto_subs'):
            self.switch_auto_subs.set_theme(t.accent, t.accent_text, t.is_dark)
        self.update_health_summary()

    def _is_folder_writable(self, folder: str) -> bool:
        if not folder:
            return False
        if os.path.exists(folder):
            test_file = os.path.join(folder, f".bemudex_test_write_{os.getpid()}")
            try:
                with open(test_file, "w") as f:
                    f.write("ok")
                os.remove(test_file)
                return True
            except Exception:
                return False

        # If the target directory does not exist yet (created on first download),
        # verify that the closest existing parent directory is writable.
        parent = os.path.abspath(folder)
        while parent and not os.path.exists(parent):
            prev = parent
            parent = os.path.dirname(parent)
            if parent == prev:
                break
        if parent and os.path.exists(parent):
            test_file = os.path.join(parent, f".bemudex_test_write_{os.getpid()}")
            try:
                with open(test_file, "w") as f:
                    f.write("ok")
                os.remove(test_file)
                return True
            except Exception:
                return False
        return False

    def update_health_summary(self, ytdlp_status: str = "healthy"):
        if not hasattr(self, 'health_frame'):
            return

        self.lbl_health_bemudex.setText("<span style='color: #10b981; font-size: 14px;'>●</span>  Bemudex")

        if ytdlp_status == "warning":
            self.lbl_health_ytdlp.setText("<span style='color: #f59e0b; font-size: 14px;'>●</span>  yt-dlp")
        elif ytdlp_status == "error":
            self.lbl_health_ytdlp.setText("<span style='color: #ef4444; font-size: 14px;'>●</span>  yt-dlp")
        else:
            self.lbl_health_ytdlp.setText("<span style='color: #10b981; font-size: 14px;'>●</span>  yt-dlp")

        ff_info = self.dep_manager.detect()
        ff_ok = bool(ff_info.get("installed"))
        if ff_ok:
            self.lbl_health_ffmpeg.setText("<span style='color: #10b981; font-size: 14px;'>●</span>  FFmpeg")
        else:
            self.lbl_health_ffmpeg.setText("<span style='color: #ef4444; font-size: 14px;'>●</span>  FFmpeg")

        target_vid = self.input_video_folder.text() if hasattr(self, 'input_video_folder') else load_video_folder()
        target_aud = self.input_audio_folder.text() if hasattr(self, 'input_audio_folder') else load_audio_folder()
        vid_ok = self._is_folder_writable(target_vid)
        aud_ok = self._is_folder_writable(target_aud)
        folder_ok = vid_ok and aud_ok
        if folder_ok:
            self.lbl_health_folder.setText("<span style='color: #10b981; font-size: 14px;'>●</span>  Download Folders")
        else:
            self.lbl_health_folder.setText("<span style='color: #ef4444; font-size: 14px;'>●</span>  Download Folders")

        if not ff_ok:
            self.health_frame.setProperty("status", "danger")
            self.lbl_health_status.setStyleSheet("color: #ef4444; font-weight: 700;")
            self.lbl_health_status.setText("⚠ Attention Required: FFmpeg Missing")
        elif not folder_ok:
            self.health_frame.setProperty("status", "danger")
            self.lbl_health_status.setStyleSheet("color: #ef4444; font-weight: 700;")
            if not vid_ok and not aud_ok:
                self.lbl_health_status.setText("⚠ Attention Required: Video & Audio folders are not writable.")
            elif not vid_ok:
                self.lbl_health_status.setText("⚠ Attention Required: Video download folder is not writable.")
            else:
                self.lbl_health_status.setText("⚠ Attention Required: Audio download folder is not writable.")
        elif ytdlp_status == "warning":
            self.health_frame.setProperty("status", "warning")
            self.lbl_health_status.setStyleSheet("color: #f59e0b; font-weight: 700;")
            self.lbl_health_status.setText("⚠ Attention Required: yt-dlp Update Available")
        else:
            self.health_frame.setProperty("status", "ready")
            self.lbl_health_status.setStyleSheet("color: #10b981; font-weight: 700;")
            self.lbl_health_status.setText("✓ Ready to Download")

        self.health_frame.style().unpolish(self.health_frame)
        self.health_frame.style().polish(self.health_frame)

    def notify_update_available(self, res: dict):
        installed = res.get("installed", "unknown")
        latest = res.get("latest", "unknown")
        ch_name = res.get("channel", load_engine_channel()).capitalize()
        self.lbl_engine_status.setText(f"Update available ({ch_name})! (Current: {installed} → Latest: {latest})")
        self.lbl_engine_status.setStyleSheet("color: #f59e0b; font-weight: 600;")
        self.btn_update_engine.show()
        self.update_health_summary(ytdlp_status="warning")

    def notify_engine_updated(self, version: str):
        self.btn_update_engine.hide()
        ver_str = f" (version {version})" if version else ""
        self.lbl_engine_status.setText(f"✓ Engine is up to date{ver_str}.")
        self.lbl_engine_status.setStyleSheet("color: #10b981; font-weight: 500;")
        self.refresh_all()

    # ── Event Handlers: Appearance & Preferences ──
    def _on_theme_changed(self, index: int):
        theme_id = self.combo_theme.itemData(index)
        if theme_id:
            save_theme(theme_id)
            self.apply_theme(theme_id)
            self.theme_changed.emit(theme_id)

    def _on_ui_scale_changed(self, index: int):
        scale = self.combo_scale.itemData(index)
        if scale:
            save_ui_scale(scale)
            self.ui_scale_changed.emit(scale)

    def _on_check_launch_toggled(self, checked: bool):
        save_check_updates_on_launch(checked)

    def _on_browse_video_folder_clicked(self):
        current = self.input_video_folder.text() or get_default_video_folder()
        chosen = QFileDialog.getExistingDirectory(self, "Select Video Download Directory", current)
        if chosen:
            try:
                os.makedirs(chosen, exist_ok=True)
            except Exception:
                pass
            save_video_folder(chosen)
            self.input_video_folder.setText(chosen)
            self.video_folder_changed.emit(chosen)
            self.update_health_summary()

    def _on_reset_video_folder_clicked(self):
        default_dir = get_default_video_folder()
        save_video_folder(default_dir)
        self.input_video_folder.setText(default_dir)
        self.video_folder_changed.emit(default_dir)
        self.update_health_summary()

    def _on_browse_audio_folder_clicked(self):
        current = self.input_audio_folder.text() or get_default_audio_folder()
        chosen = QFileDialog.getExistingDirectory(self, "Select Audio Download Directory", current)
        if chosen:
            try:
                os.makedirs(chosen, exist_ok=True)
            except Exception:
                pass
            save_audio_folder(chosen)
            self.input_audio_folder.setText(chosen)
            self.audio_folder_changed.emit(chosen)
            self.update_health_summary()

    def _on_reset_audio_folder_clicked(self):
        default_dir = get_default_audio_folder()
        save_audio_folder(default_dir)
        self.input_audio_folder.setText(default_dir)
        self.audio_folder_changed.emit(default_dir)
        self.update_health_summary()

    def _on_browse_folder_clicked(self):
        self._on_browse_video_folder_clicked()

    def _on_reset_folder_clicked(self):
        self._on_reset_video_folder_clicked()

    def _on_audio_format_changed(self, index: int):
        codecs = ["mp3", "m4a", "flac", "wav", "aac"]
        selected = codecs[index] if index < len(codecs) else "mp3"
        save_audio_format(selected)
        self.audio_format_changed.emit(selected)

    def _on_auto_close_toggled(self, checked: bool):
        save_auto_close_panel(checked)

    def _on_desktop_notify_toggled(self, checked: bool):
        save_desktop_notifications(checked)
        status_msg = "Desktop notifications enabled" if checked else "Desktop notifications disabled"
        self.toast_requested.emit(status_msg, "info")

    def scroll_to_cookies(self):
        if hasattr(self, 'scroll') and hasattr(self, 'card_cookies'):
            self.scroll.ensureWidgetVisible(self.card_cookies, 0, 50)

    def _on_compat_mode_toggled(self, checked: bool):
        save_compatibility_mode(checked)
        status_msg = "Device compatibility mode (H.264/MP4) enabled" if checked else "Standard high-efficiency mode (AV1/VP9) enabled"
        self.toast_requested.emit(status_msg, "info")

    def _on_sponsorblock_toggled(self, checked: bool):
        save_sponsorblock_enabled(checked)
        status_msg = "SponsorBlock enabled: Sponsor segments will be skipped" if checked else "SponsorBlock disabled"
        self.toast_requested.emit(status_msg, "info")

    def _on_crop_artwork_toggled(self, checked: bool):
        save_crop_artwork(checked)
        status_msg = "Square 1:1 artwork cropping enabled for audio" if checked else "Square artwork cropping disabled"
        self.toast_requested.emit(status_msg, "info")

    def _on_sub_langs_changed(self):
        text = self.input_sub_langs.text().strip()
        save_subtitle_languages(text)
        self.toast_requested.emit(f"Subtitle languages saved: {text or 'en, en-US, en-GB'}", "info")

    def _on_auto_subs_toggled(self, checked: bool):
        save_auto_subtitles(checked)
        status_msg = "Auto-generated subtitles enabled" if checked else "Auto-generated subtitles disabled"
        self.toast_requested.emit(status_msg, "info")

    def _on_cookies_source_changed(self, index: int):
        source = self.combo_cookies.itemData(index) or "none"
        save_cookies_source(source)
        if hasattr(self, 'cookie_file_container'):
            self.cookie_file_container.setVisible(source == "file")
        self.toast_requested.emit(f"Cookies source updated: {self.combo_cookies.currentText()}", "success")

    def _on_browse_cookies_file_clicked(self):
        current_file = load_cookies_file()
        start_dir = os.path.dirname(current_file) if current_file else os.path.expanduser("~")
        chosen, _ = QFileDialog.getOpenFileName(self, "Select cookies.txt File", start_dir, "Text Files (*.txt);;All Files (*)")
        if chosen and os.path.exists(chosen):
            save_cookies_file(chosen)
            self.input_cookies_file.setText(chosen)
            self.toast_requested.emit("Cookies file saved.", "success")

    def _on_clear_cookies_file_clicked(self):
        save_cookies_file("")
        self.input_cookies_file.setText("")
        self.toast_requested.emit("Cookies file cleared.", "info")

    def _on_browse_ffmpeg_clicked(self):
        chosen, _ = QFileDialog.getOpenFileName(self, "Select FFmpeg Executable", "/usr/bin", "Executables (*)")
        if chosen and os.path.exists(chosen):
            ver = self.dep_manager._probe_ffmpeg(chosen)
            if ver:
                save_ffmpeg_path(chosen)
                self.dep_manager.detect(force_recheck=True)
                self.refresh_all()
            else:
                self.lbl_ff_status.setText(f"❌ The selected binary at '{chosen}' is not a valid FFmpeg executable.")

    def _on_auto_ffmpeg_clicked(self):
        save_ffmpeg_path("")
        self.dep_manager.detect(force_recheck=True)
        self.refresh_all()
        self.btn_auto_ff.setText("✓ Detected")
        QTimer.singleShot(1500, lambda: self.btn_auto_ff.setText("Auto-Detect"))

    # ── Event Handlers: Engine Updates ──
    def _on_engine_channel_changed(self, index: int):
        channel = self.combo_engine_channel.itemData(index) or "nightly"
        save_engine_channel(channel)
        channel_name = "Nightly (Daily Fixes)" if channel == "nightly" else "Stable (Official)"
        self.toast_requested.emit(f"yt-dlp channel set to {channel_name}. Checking for updates...", "info")
        self._on_check_engine_clicked()

    def _on_check_engine_clicked(self):
        self.btn_check_engine.setEnabled(False)
        self.btn_check_engine.setText("Checking...")
        self.lbl_engine_status.setText("Connecting to PyPI registry...")

        self.check_worker = EngineCheckWorker()
        self.check_worker.checked.connect(self._on_check_finished)
        self.check_worker.start()

    @pyqtSlot(dict)
    def _on_check_finished(self, res: dict):
        self.btn_check_engine.setEnabled(True)
        self.btn_check_engine.setText("Check for Updates")

        status = res.get("status")
        if status == "success":
            installed = res.get("installed")
            latest = res.get("latest")
            update_available = res.get("update_available", False)
            ch_name = res.get("channel", "nightly").capitalize()

            if update_available:
                self.lbl_engine_status.setText(f"Update available ({ch_name})! (Current: {installed} → Latest: {latest})")
                self.btn_update_engine.show()
                self.update_health_summary(ytdlp_status="warning")
            else:
                self.lbl_engine_status.setText(f"✓ Engine is up to date on {ch_name} channel (version {installed}).")
                self.btn_update_engine.hide()
                self.update_health_summary(ytdlp_status="healthy")

            self.engine_status_changed.emit({
                "status": "checked",
                "version": installed,
                "update_available": update_available
            })
        else:
            msg = res.get("message", "Failed to check for updates.")
            self.lbl_engine_status.setText(f"⚠️ {msg}")
            self.update_health_summary(ytdlp_status="healthy")

    def _on_update_engine_clicked(self):
        self.btn_update_engine.setEnabled(False)
        self.btn_update_engine.setText("Updating...")
        self.btn_check_engine.setEnabled(False)
        self.lbl_engine_status.setText("Downloading and validating yt-dlp wheel package...")

        self.update_worker = EngineUpdateWorker()
        self.update_worker.updated.connect(self._on_update_finished)
        self.update_worker.start()

    @pyqtSlot(dict)
    def _on_update_finished(self, res: dict):
        self.btn_check_engine.setEnabled(True)
        self.btn_update_engine.setEnabled(True)
        self.btn_update_engine.setText("Update Engine")

        status = res.get("status")
        if status == "success":
            self.btn_update_engine.hide()
            new_ver = res.get("version", "")
            self.lbl_engine_status.setText(f"✓ Engine updated to {new_ver} successfully.")
            self.refresh_all()
            self.engine_status_changed.emit({
                "status": "success",
                "version": new_ver,
                "update_available": False
            })
            self.toast_requested.emit(f"yt-dlp updated to {new_ver} successfully.", "success")
        elif status == "up_to_date":
            self.btn_update_engine.hide()
            self.lbl_engine_status.setText(res.get("message", "Already up to date."))
            self.refresh_all()
            self.engine_status_changed.emit({
                "status": "up_to_date",
                "version": res.get("version", ""),
                "update_available": False
            })
            self.toast_requested.emit(res.get("message", "yt-dlp is up to date."), "info")
        else:
            msg = res.get("message", "Engine update failed.")
            self.lbl_engine_status.setText(f"❌ {msg}")
            self.toast_requested.emit(msg, "error")

    def _on_rollback_engine_clicked(self):
        self.btn_rollback_engine.setEnabled(False)
        self.btn_rollback_engine.setText("Restoring...")
        self.lbl_engine_status.setText("Restoring engine from backup...")

        self.rollback_worker = EngineRollbackWorker()
        self.rollback_worker.rolled_back.connect(self._on_rollback_finished)
        self.rollback_worker.start()

    @pyqtSlot(dict)
    def _on_rollback_finished(self, res: dict):
        self.btn_rollback_engine.setEnabled(True)
        self.btn_rollback_engine.setText("Roll Back")

        status = res.get("status")
        if status == "success":
            self.lbl_engine_status.setText(res.get("message", "Rolled back successfully."))
            self.refresh_all()
            ver = self.dep_manager.versions().get("ytdlp", {}).get("version")
            self.engine_status_changed.emit({
                "status": "rollback",
                "version": ver,
                "update_available": False
            })
        else:
            self.lbl_engine_status.setText(f"❌ {res.get('message', 'Rollback failed.')}")
