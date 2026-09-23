import os
import shutil
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QWidget
)

from services.dependency_manager import DependencyManager
from ui.icon_provider import get_icon, get_pixmap
from workers.engine_worker import EngineCheckWorker, EngineUpdateWorker


class Sidebar(QFrame):
    """Navigation sidebar for Bemudex 3.0 supporting both expanded and collapsed modes."""
    page_changed = pyqtSignal(str)
    toast_requested = pyqtSignal(str, str)
    engine_check_finished = pyqtSignal(dict)
    engine_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarFrame")
        self.setFixedWidth(215)
        self.is_collapsed = False
        self.current_page = "home"
        self.current_theme_id = "dark"
        self.dep_mgr = DependencyManager()
        self.check_thread = None
        self.update_worker = None
        self.is_update_available = False
        self.is_updating = False
        self.storage_usage_str = "Storage: Ready"
        self.history_count = 0

        self._init_ui()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 18, 14, 18)
        self.main_layout.setSpacing(6)

        # ── Header ──
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(36)
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(8)

        self.logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'bemudex_32.png')
        if os.path.exists(logo_path):
            logo_pix = QPixmap(logo_path).scaled(
                24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.logo_label.setPixmap(logo_pix)
        self.header_layout.addWidget(self.logo_label)

        self.title_label = QLabel("Bemudex")
        self.title_label.setObjectName("sidebarAppName")
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()

        self.btn_collapse = QPushButton()
        self.btn_collapse.setObjectName("btnSidebarCollapse")
        self.btn_collapse.setFixedSize(24, 24)
        self.btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse.clicked.connect(self._toggle_collapse)
        self.header_layout.addWidget(self.btn_collapse)

        self.main_layout.addWidget(self.header_widget)
        self.main_layout.addSpacing(12)

        # ── Nav Buttons ──
        self.btn_home = QPushButton("  Home")
        self.btn_home.setProperty("class", "sidebar-btn active")
        self.btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_home.clicked.connect(lambda: self._on_nav_clicked("home"))
        self.main_layout.addWidget(self.btn_home)

        self.btn_history = QPushButton("  History")
        self.btn_history.setProperty("class", "sidebar-btn")
        self.btn_history.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_history.clicked.connect(lambda: self._on_nav_clicked("history"))

        hist_btn_layout = QHBoxLayout(self.btn_history)
        hist_btn_layout.setContentsMargins(0, 0, 8, 0)
        hist_btn_layout.addStretch()
        self.lbl_history_badge = QLabel()
        self.lbl_history_badge.setObjectName("sidebarBadge")
        self.lbl_history_badge.hide()
        hist_btn_layout.addWidget(self.lbl_history_badge)

        self.main_layout.addWidget(self.btn_history)

        self.btn_settings = QPushButton("  Settings")
        self.btn_settings.setProperty("class", "sidebar-btn")
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(lambda: self._on_nav_clicked("settings"))
        self.main_layout.addWidget(self.btn_settings)

        # ── Coming Soon Section ──
        self.lbl_coming_soon = QLabel("COMING SOON")
        self.lbl_coming_soon.setObjectName("lblComingSoon")
        self.main_layout.addSpacing(8)
        self.main_layout.addWidget(self.lbl_coming_soon)

        self.btn_playlists = QPushButton("  Playlists")
        self.btn_playlists.setProperty("class", "sidebar-btn")
        self.btn_playlists.setEnabled(False)
        self.main_layout.addWidget(self.btn_playlists)

        self.main_layout.addStretch()

        # ── Footer: Storage & Engine Status ──
        self.footer = QFrame()
        self.footer.setObjectName("sidebarFooter")
        self.footer_layout = QVBoxLayout(self.footer)
        self.footer_layout.setContentsMargins(0, 4, 0, 0)
        self.footer_layout.setSpacing(8)

        # Storage Header
        storage_header = QHBoxLayout()
        storage_header.setSpacing(8)
        self.lbl_storage_icon = QLabel()
        storage_header.addWidget(self.lbl_storage_icon)

        self.lbl_storage_title = QLabel("STORAGE")
        self.lbl_storage_title.setObjectName("sidebarStorageLabel")
        storage_header.addWidget(self.lbl_storage_title)
        storage_header.addStretch()
        self.footer_layout.addLayout(storage_header)

        # Progress bar
        self.storage_bar = QProgressBar()
        self.storage_bar.setObjectName("sidebarStorageBar")
        self.storage_bar.setTextVisible(False)
        self.storage_bar.setRange(0, 100)
        self.storage_bar.setValue(20)
        self.footer_layout.addWidget(self.storage_bar)

        # Storage text
        self.lbl_storage_text = QLabel("Storage: Ready")
        self.lbl_storage_text.setObjectName("engineStatusText")
        self.footer_layout.addWidget(self.lbl_storage_text)

        self.footer_layout.addSpacing(6)

        # Engine Header (Title on left, Status Dot + Label on right)
        engine_header = QHBoxLayout()
        engine_header.setSpacing(6)

        lbl_engine_title = QLabel("ENGINE")
        lbl_engine_title.setObjectName("sidebarStorageLabel")
        engine_header.addWidget(lbl_engine_title)
        engine_header.addStretch()

        self.dot_status = QLabel()
        self.dot_status.setObjectName("engineStatusDot")
        self.dot_status.setStyleSheet("background-color: #10b981; border-radius: 3.5px; min-width: 7px; max-width: 7px; min-height: 7px; max-height: 7px;")
        engine_header.addWidget(self.dot_status)

        self.lbl_engine_status = QLabel("Up to date")
        self.lbl_engine_status.setObjectName("engineStatusText")
        self.lbl_engine_status.setStyleSheet("color: #10b981; font-weight: 500;")
        engine_header.addWidget(self.lbl_engine_status)
        self.footer_layout.addLayout(engine_header)

        # Engine Version Subtext
        try:
            versions = self.dep_mgr.versions()
            ytdlp_ver = versions.get("ytdlp", {}).get("version", "Active")
        except Exception:
            ytdlp_ver = "Active"

        self.lbl_engine_ver = QLabel(f"v{ytdlp_ver}")
        self.lbl_engine_ver.setObjectName("engineStatusText")
        self.lbl_engine_ver.setToolTip(f"Installed yt-dlp version: {ytdlp_ver}")
        self.footer_layout.addWidget(self.lbl_engine_ver)

        self.footer_layout.addSpacing(4)

        # Check for Updates Button
        self.btn_update = QPushButton("  Check for Updates")
        self.btn_update.setObjectName("btnUpdateEngine")
        self.btn_update.setFixedHeight(34)
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.clicked.connect(self._on_update_button_clicked)
        self.footer_layout.addWidget(self.btn_update)

        self.main_layout.addWidget(self.footer)

        # Collapsed divider above storage icon
        self.collapsed_divider = QFrame()
        self.collapsed_divider.setFixedSize(30, 1)
        self.collapsed_divider.setObjectName("sidebarDivider")
        self.collapsed_divider.hide()
        self.main_layout.addWidget(self.collapsed_divider, 0, Qt.AlignmentFlag.AlignCenter)

        # Collapsed storage icon indicator (hidden initially)
        self.lbl_collapsed_storage = QLabel()
        self.lbl_collapsed_storage.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_collapsed_storage.setToolTip(self.storage_usage_str)
        self.lbl_collapsed_storage.setFixedSize(40, 36)
        self.lbl_collapsed_storage.hide()
        self.main_layout.addWidget(self.lbl_collapsed_storage, 0, Qt.AlignmentFlag.AlignCenter)

        self._update_icons()

    def _toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.setFixedWidth(64)
            self.main_layout.setContentsMargins(8, 16, 8, 16)
            self.title_label.hide()
            self.lbl_coming_soon.hide()
            self.footer.hide()
            self.collapsed_divider.show()
            self.lbl_collapsed_storage.show()
            self.lbl_history_badge.hide()

            # Vertically stacked header: Logo centered on top, Toggle centered below it
            self.header_widget.setFixedHeight(68)
            self.header_layout.setDirection(QHBoxLayout.Direction.TopToBottom)
            self.header_layout.setContentsMargins(0, 0, 0, 0)
            self.header_layout.setSpacing(6)
            self.header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.btn_collapse.setFixedSize(20, 20)

            # Collapsed button styles
            for btn, tooltip in [(self.btn_home, "Home"), (self.btn_history, "History"),
                                  (self.btn_settings, "Settings"), (self.btn_playlists, "Playlists")]:
                btn.setText("")
                btn.setToolTip(tooltip)
                is_active = (btn == getattr(self, f"btn_{self.current_page}", None))
                btn.setProperty("class", "sidebar-btn-collapsed active" if is_active else "sidebar-btn-collapsed")
                btn.style().polish(btn)
        else:
            self.setFixedWidth(215)
            self.main_layout.setContentsMargins(14, 18, 14, 18)
            self.title_label.show()
            self.lbl_coming_soon.show()
            self.footer.show()
            self.collapsed_divider.hide()
            self.lbl_collapsed_storage.hide()
            if self.history_count > 0:
                self.lbl_history_badge.show()

            # Restore expanded horizontal header
            self.header_widget.setFixedHeight(36)
            self.header_layout.setDirection(QHBoxLayout.Direction.LeftToRight)
            self.header_layout.setContentsMargins(0, 0, 0, 0)
            self.header_layout.setSpacing(8)
            self.header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.btn_collapse.setFixedSize(24, 24)

            self.btn_home.setText("  Home")
            self.btn_history.setText("  History")
            self.btn_settings.setText("  Settings")
            self.btn_playlists.setText("  Playlists")

            for btn in [self.btn_home, self.btn_history, self.btn_settings, self.btn_playlists]:
                btn.setToolTip("")
                is_active = (btn == getattr(self, f"btn_{self.current_page}", None))
                btn.setProperty("class", "sidebar-btn active" if is_active else "sidebar-btn")
                btn.style().polish(btn)

        self._update_icons()

    def _on_nav_clicked(self, page_name: str):
        self.set_active_page(page_name)
        self.page_changed.emit(page_name)

    def set_active_page(self, page_name: str):
        self.current_page = page_name
        cls_base = "sidebar-btn-collapsed" if self.is_collapsed else "sidebar-btn"

        self.btn_home.setProperty("class", f"{cls_base} active" if page_name == "home" else cls_base)
        self.btn_history.setProperty("class", f"{cls_base} active" if page_name == "history" else cls_base)
        self.btn_settings.setProperty("class", f"{cls_base} active" if page_name == "settings" else cls_base)

        self.btn_home.style().polish(self.btn_home)
        self.btn_history.style().polish(self.btn_history)
        self.btn_settings.style().polish(self.btn_settings)
        self._update_icons()

    def apply_theme(self, theme_id: str):
        self.current_theme_id = theme_id
        self._update_icons()

    def _update_icons(self):
        from ui.themes import get_theme
        t = get_theme(self.current_theme_id)
        active_color = t.accent
        inactive_color = t.text_secondary
        disabled_color = t.text_muted

        self.btn_home.setIcon(get_icon("home", active_color if self.current_page == "home" else inactive_color, 18))
        self.btn_history.setIcon(get_icon("history", active_color if self.current_page == "history" else inactive_color, 18))
        self.btn_settings.setIcon(get_icon("settings", active_color if self.current_page == "settings" else inactive_color, 18))
        self.btn_playlists.setIcon(get_icon("playlists", disabled_color, 18))

        collapse_icon_name = "chevron-right" if self.is_collapsed else "chevron-left"
        self.btn_collapse.setIcon(get_icon(collapse_icon_name, inactive_color, 14))

        self.lbl_storage_icon.setPixmap(get_pixmap("hard-drive", disabled_color, 12))
        self.lbl_collapsed_storage.setPixmap(get_pixmap("hard-drive", disabled_color, 16))
        if getattr(self, "is_update_available", False):
            self.btn_update.setIcon(get_icon("download", t.accent_text, 13))
        else:
            self.btn_update.setIcon(get_icon("refresh", inactive_color, 12))

    def set_history_count(self, count: int):
        self.history_count = count
        if count > 0 and not self.is_collapsed:
            self.lbl_history_badge.setText(str(count))
            self.lbl_history_badge.show()
        else:
            self.lbl_history_badge.hide()

    def update_storage(self, folder_path: str):
        try:
            target = os.path.abspath(folder_path or os.path.expanduser("~"))
            while not os.path.exists(target) and os.path.dirname(target) != target:
                target = os.path.dirname(target)
            if not os.path.exists(target):
                target = os.path.expanduser("~")

            usage = shutil.disk_usage(target)
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            used_pct = int(((usage.total - usage.free) / usage.total) * 100) if usage.total > 0 else 0
            self.storage_bar.setValue(used_pct)

            total_str = f"{total_gb:.0f} GB" if total_gb >= 1 else f"{usage.total / (1024 ** 2):.1f} MB"
            free_str = f"{free_gb:.1f} GB" if free_gb >= 1 else f"{usage.free / (1024 ** 2):.1f} MB"

            self.storage_usage_str = f"Storage: {free_str} free of {total_str}"
            self.lbl_storage_text.setText(f"{free_str} free of {total_str}")
            self.lbl_collapsed_storage.setToolTip(self.storage_usage_str)
        except Exception:
            self.lbl_storage_text.setText("Storage: Ready")

    def _on_update_button_clicked(self):
        if self.is_update_available:
            self._on_update_engine_clicked()
        else:
            self._on_check_updates_clicked()

    def _on_check_updates_clicked(self):
        self.btn_update.setEnabled(False)
        self.btn_update.setText("  Checking...")
        self.check_thread = EngineCheckWorker(self)
        self.check_thread.checked.connect(self._on_check_finished)
        self.check_thread.start()

    @pyqtSlot(dict)
    def _on_check_finished(self, res: dict):
        self.btn_update.setEnabled(True)
        if res.get("status") == "success":
            update_avail = res.get("update_available", False)
            installed_ver = res.get("installed")
            self.refresh_engine_status(version=installed_ver, update_available=update_avail)
            if update_avail:
                self.toast_requested.emit("An update for yt-dlp is available.", "info")
            else:
                self.toast_requested.emit("yt-dlp is up to date.", "success")
            self.engine_check_finished.emit(res)
        else:
            self.btn_update.setText("  Update Now" if self.is_update_available else "  Check for Updates")
            self.toast_requested.emit(res.get("message", "Update check failed"), "error")
            self._update_icons()

    def _on_update_engine_clicked(self):
        self.is_updating = True
        self.btn_update.setEnabled(False)
        self.btn_update.setText("  Updating...")
        self.lbl_engine_status.setText("Updating...")
        self.lbl_engine_status.setStyleSheet("color: #f59e0b; font-weight: 500;")

        self.update_worker = EngineUpdateWorker(self)
        self.update_worker.updated.connect(self._on_update_finished)
        self.update_worker.start()

    @pyqtSlot(dict)
    def _on_update_finished(self, res: dict):
        self.is_updating = False
        self.btn_update.setEnabled(True)

        status = res.get("status")
        if status in ("success", "up_to_date"):
            new_ver = res.get("version", "")
            self.refresh_engine_status(version=new_ver, update_available=False)
            msg = f"yt-dlp updated to {new_ver} successfully." if status == "success" else res.get("message", "yt-dlp is up to date.")
            self.toast_requested.emit(msg, "success")
            self.engine_updated.emit(res)
        else:
            msg = res.get("message", "Engine update failed.")
            self.btn_update.setText("  Update Now")
            self.toast_requested.emit(msg, "error")
            self._update_icons()

    def set_update_available(self, available: bool):
        self.is_update_available = available
        if available:
            self.dot_status.setStyleSheet("background-color: #f59e0b; border-radius: 3.5px; min-width: 7px; max-width: 7px; min-height: 7px; max-height: 7px;")
            self.lbl_engine_status.setText("Update Available")
            self.lbl_engine_status.setStyleSheet("color: #f59e0b; font-weight: 500;")
            if not self.is_updating:
                self.btn_update.setText("  Update Now")
                self.btn_update.setToolTip("Download and install the latest yt-dlp release")
                self.btn_update.setProperty("status", "update_available")
        else:
            self.dot_status.setStyleSheet("background-color: #10b981; border-radius: 3.5px; min-width: 7px; max-width: 7px; min-height: 7px; max-height: 7px;")
            self.lbl_engine_status.setText("Up to date")
            self.lbl_engine_status.setStyleSheet("color: #10b981; font-weight: 500;")
            if not self.is_updating:
                self.btn_update.setText("  Check for Updates")
                self.btn_update.setToolTip("Check for yt-dlp engine updates")
                self.btn_update.setProperty("status", "")
        self.btn_update.style().unpolish(self.btn_update)
        self.btn_update.style().polish(self.btn_update)
        self._update_icons()

    def refresh_engine_status(self, version: str = None, update_available: bool = False):
        if not version:
            try:
                versions = self.dep_mgr.versions()
                version = versions.get("ytdlp", {}).get("version", "Active")
            except Exception:
                version = "Active"

        self.lbl_engine_ver.setText(f"v{version}")
        self.lbl_engine_ver.setToolTip(f"Installed yt-dlp version: {version}")
        self.set_update_available(update_available)
