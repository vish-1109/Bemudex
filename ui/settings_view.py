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
    load_last_folder, save_last_folder, get_default_download_folder,
    load_audio_format, save_audio_format,
    load_ffmpeg_path, save_ffmpeg_path,
    load_theme, save_theme,
    load_auto_close_panel, save_auto_close_panel,
    load_ui_scale, save_ui_scale,
    load_check_updates_on_launch, save_check_updates_on_launch
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
        scroll = QScrollArea()
        scroll.setObjectName("settingsScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(300)

        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        self.content_layout = QVBoxLayout(scroll_content)
        self.content_layout.setContentsMargins(0, 10, 8, 36)
        self.content_layout.setSpacing(26)

        # Card 1: Appearance & Theme
        self._build_appearance_card()

        # Card 2: Download Preferences
        self._build_preferences_card()

        # Card 3: yt-dlp Engine
        self._build_engine_card()

        # Card 4: Troubleshooting
        self._build_troubleshooting_card()

        # Card 5: About Section
        self._build_about_card()

        self.content_layout.addStretch()
        scroll.setWidget(scroll_content)
        root_layout.addWidget(scroll, 1)

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

        # 1. Default Download Directory
        row_dir = QVBoxLayout()
        row_dir.setSpacing(6)
        lbl_dir_title = QLabel("Default Download Location")
        lbl_dir_title.setObjectName("settingsItemTitle")
        row_dir.addWidget(lbl_dir_title)

        lbl_dir_desc = QLabel("Downloaded media files will be saved here automatically.")
        lbl_dir_desc.setObjectName("settingsItemDesc")
        lbl_dir_desc.setWordWrap(True)
        row_dir.addWidget(lbl_dir_desc)

        row_dir.addSpacing(4)

        self.input_folder = QLineEdit()
        self.input_folder.setObjectName("settingsPathInput")
        self.input_folder.setFixedHeight(38)
        self.input_folder.setReadOnly(True)
        row_dir.addWidget(self.input_folder)

        row_dir.addSpacing(6)

        dir_btn_row = QHBoxLayout()
        dir_btn_row.setSpacing(10)
        btn_browse_folder = QPushButton("Browse Folder...")
        btn_browse_folder.setObjectName("btnSettingsAction")
        btn_browse_folder.setFixedHeight(36)
        btn_browse_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse_folder.clicked.connect(self._on_browse_folder_clicked)
        dir_btn_row.addWidget(btn_browse_folder)

        btn_default_folder = QPushButton("Reset to Default")
        btn_default_folder.setObjectName("btnSettingsAction")
        btn_default_folder.setFixedHeight(36)
        btn_default_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_default_folder.clicked.connect(self._on_reset_folder_clicked)
        dir_btn_row.addWidget(btn_default_folder)
        dir_btn_row.addStretch()
        row_dir.addLayout(dir_btn_row)
        layout.addLayout(row_dir)

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

    # ── Section 2: yt-dlp Engine ──
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

        # 1. Folder
        folder = load_last_folder()
        self.input_folder.setText(folder)

        # 2. Audio Format
        fmt = load_audio_format()
        index_map = {"mp3": 0, "m4a": 1, "flac": 2, "wav": 3, "aac": 4}
        self.combo_audio.blockSignals(True)
        self.combo_audio.setCurrentIndex(index_map.get(fmt, 0))
        self.combo_audio.blockSignals(False)

        # 3. Auto-close panel toggle
        if hasattr(self, 'switch_auto_close'):
            self.switch_auto_close.setChecked(load_auto_close_panel())

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

        # Rollback button visibility
        can_rollback = self.dep_manager.can_rollback()
        self.btn_rollback_engine.setVisible(can_rollback)

        # 5. Health Summary
        self.update_health_summary()

    def update_folder(self, folder: str):
        """Synchronizes folder display when changed externally from HomeView."""
        self.input_folder.setText(folder)
        self.update_health_summary()

    def apply_theme(self, theme_id: str):
        t = get_theme(theme_id)
        if hasattr(self, 'switch_auto_close'):
            self.switch_auto_close.set_theme(t.accent, t.accent_text, t.is_dark)
        if hasattr(self, 'switch_check_launch'):
            self.switch_check_launch.set_theme(t.accent, t.accent_text, t.is_dark)
        self.update_health_summary()

    def _is_folder_writable(self, folder: str) -> bool:
        if not folder or not os.path.exists(folder):
            return False
        test_file = os.path.join(folder, f".bemudex_test_write_{os.getpid()}")
        try:
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return True
        except Exception:
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

        target_folder = self.input_folder.text() or load_last_folder()
        folder_ok = self._is_folder_writable(target_folder)
        if folder_ok:
            self.lbl_health_folder.setText("<span style='color: #10b981; font-size: 14px;'>●</span>  Download Folder")
        else:
            self.lbl_health_folder.setText("<span style='color: #ef4444; font-size: 14px;'>●</span>  Download Folder")

        if not ff_ok:
            self.health_frame.setProperty("status", "danger")
            self.lbl_health_status.setStyleSheet("color: #ef4444; font-weight: 700;")
            self.lbl_health_status.setText("⚠ Attention Required: FFmpeg Missing")
        elif not folder_ok:
            self.health_frame.setProperty("status", "danger")
            self.lbl_health_status.setStyleSheet("color: #ef4444; font-weight: 700;")
            self.lbl_health_status.setText("⚠ Attention Required: Download folder is not writable.")
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
        self.lbl_engine_status.setText(f"Update available! (Current: {installed} → Latest: {latest})")
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

    def _on_browse_folder_clicked(self):
        current = self.input_folder.text() or get_default_download_folder()
        chosen = QFileDialog.getExistingDirectory(self, "Select Download Directory", current)
        if chosen and os.path.exists(chosen):
            save_last_folder(chosen)
            self.input_folder.setText(chosen)
            self.folder_changed.emit(chosen)

    def _on_reset_folder_clicked(self):
        default_dir = get_default_download_folder()
        save_last_folder(default_dir)
        self.input_folder.setText(default_dir)
        self.folder_changed.emit(default_dir)

    def _on_audio_format_changed(self, index: int):
        codecs = ["mp3", "m4a", "flac", "wav", "aac"]
        selected = codecs[index] if index < len(codecs) else "mp3"
        save_audio_format(selected)
        self.audio_format_changed.emit(selected)

    def _on_auto_close_toggled(self, checked: bool):
        save_auto_close_panel(checked)

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

            if update_available:
                self.lbl_engine_status.setText(f"Update available! (Current: {installed} → Latest: {latest})")
                self.btn_update_engine.show()
                self.update_health_summary(ytdlp_status="warning")
            else:
                self.lbl_engine_status.setText(f"✓ Engine is up to date (version {installed}).")
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
        elif status == "up_to_date":
            self.btn_update_engine.hide()
            self.lbl_engine_status.setText(res.get("message", "Already up to date."))
            self.refresh_all()
            self.engine_status_changed.emit({
                "status": "up_to_date",
                "version": res.get("version", ""),
                "update_available": False
            })
        else:
            msg = res.get("message", "Engine update failed.")
            self.lbl_engine_status.setText(f"❌ {msg}")

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
