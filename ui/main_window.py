import os
import time
from datetime import datetime
from PyQt6.QtCore import pyqtSlot, Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QStackedWidget, QFrame, QApplication, QSplitter
)

from core.version import VERSION
from core.constants import HISTORY_LIMIT
from core.logger import logger
from services.history_manager import load_history, save_history, get_file_size_str
from services.dependency_manager import DependencyManager
from services.config_manager import (
    load_theme, load_auto_close_panel, load_ui_scale, load_check_updates_on_launch
)
from ui.sidebar import Sidebar
from ui.home_view import HomeView
from ui.history_view import HistoryView
from ui.settings_view import SettingsView
from ui.downloads_panel import DownloadsPanel
from ui.styles import get_stylesheet
from ui.themes import get_theme, create_theme_palette
from ui.toast import ToastManager
from ui.confirm_dialog import ConfirmDialog
from workers.download_worker import DownloadWorker
from workers.engine_worker import EngineCheckWorker
from yt_dlp.utils import sanitize_filename


class MainWindow(QMainWindow):
    """Main application window for Bemudex 3.0 Native Qt."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.download_queue = []       # list of queued payload dicts
        self.current_worker = None      # active DownloadWorker
        self.current_payload = None     # payload dict of currently downloading item
        self.id_counter = 0

        self.setWindowTitle(f"Bemudex {VERSION}")
        self.resize(1180, 740)
        self.setMinimumSize(930, 620)

        self._set_app_icon()
        self._init_ui()
        self._wire_signals()

        # Apply initial theme from config
        self.apply_theme(load_theme())

        # Update initial disk storage in sidebar
        self.sidebar.update_storage(self.home_view.active_folder)
        try:
            self.sidebar.set_history_count(len(self.history_view.all_history))
        except Exception:
            pass

        # Periodic timer to keep storage info synchronized
        self._storage_timer = QTimer(self)
        self._storage_timer.setInterval(30000)
        self._storage_timer.timeout.connect(lambda: self.sidebar.update_storage(self.home_view.active_folder))
        self._storage_timer.start()

        # Check dependencies on startup
        QTimer.singleShot(800, self._check_dependencies_on_launch)

        # Check for updates on launch if configured
        if load_check_updates_on_launch():
            QTimer.singleShot(1600, self._check_updates_on_launch)

    def _set_app_icon(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'bemudex_256.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Navigation Sidebar
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        # 2. Content & Downloads Splitter
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setObjectName("contentSplitter")
        self.content_splitter.setHandleWidth(4)
        self.content_splitter.setChildrenCollapsible(False)

        # Center Stacked Pages
        self.stack = QStackedWidget()
        self.stack.setObjectName("pageStack")
        self.stack.setMinimumWidth(300)

        # Page 0: Downloader (Home)
        self.home_view = HomeView()
        self.stack.addWidget(self.home_view)

        # Page 1: History View
        self.history_view = HistoryView()
        self.stack.addWidget(self.history_view)

        # Page 2: Settings View
        self.settings_view = SettingsView()
        self.stack.addWidget(self.settings_view)

        self.content_splitter.addWidget(self.stack)

        # 3. Right Active Downloads & Recent Queue Panel
        self.downloads_panel = DownloadsPanel()
        self.content_splitter.addWidget(self.downloads_panel)
        self.downloads_panel.hide()

        self.content_splitter.setStretchFactor(0, 1)
        self.content_splitter.setStretchFactor(1, 0)

        main_layout.addWidget(self.content_splitter, 1)

        # 4. Floating In-App Toast Manager
        self.toast_manager = ToastManager(self)

    def _create_placeholder_page(self, title: str, description: str) -> QWidget:
        container = QWidget()
        container.setObjectName("centerWidget")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(12)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("greetingTitle")
        layout.addWidget(lbl_title)

        card = QFrame()
        card.setProperty("class", "card-frame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(8)

        lbl_desc = QLabel(description)
        lbl_desc.setObjectName("cardMeta")
        lbl_desc.setWordWrap(True)
        card_layout.addWidget(lbl_desc)

        layout.addWidget(card)
        layout.addStretch()
        return container

    def _wire_signals(self):
        # Sidebar navigation
        self.sidebar.page_changed.connect(self._on_page_changed)
        self.sidebar.toast_requested.connect(self.show_toast)

        # Home view events
        self.home_view.folder_changed.connect(self.sidebar.update_storage)
        self.home_view.folder_changed.connect(self.settings_view.update_folder)
        self.home_view.download_requested.connect(self._on_download_requested)
        self.home_view.cancel_requested.connect(self._on_home_cancel_requested)

        # Settings view events
        self.settings_view.folder_changed.connect(self._on_settings_folder_changed)
        self.settings_view.audio_format_changed.connect(self.home_view.set_default_audio_format)
        self.settings_view.theme_changed.connect(self.apply_theme)
        self.settings_view.ui_scale_changed.connect(self.apply_ui_scale)
        self.settings_view.toast_requested.connect(self.show_toast)
        self.settings_view.engine_status_changed.connect(self._on_engine_status_changed)
        self.sidebar.engine_check_finished.connect(self._on_sidebar_engine_checked)
        self.sidebar.engine_updated.connect(self._on_sidebar_engine_updated)

        # History view events
        self.history_view.toast_requested.connect(self.show_toast)
        self.history_view.history_count_changed.connect(self.sidebar.set_history_count)

        # Downloads panel events
        self.downloads_panel.cancel_requested.connect(self._on_cancel_requested)
        self.downloads_panel.retry_requested.connect(self._on_retry_requested)

    @pyqtSlot(str, str)
    def show_toast(self, message: str, toast_type: str = "success"):
        """Displays a floating in-app pill notification at the bottom-center of the window."""
        theme_id = self.home_view.theme.id if hasattr(self, 'home_view') and hasattr(self.home_view, 'theme') else None
        self.toast_manager.show_toast(message, toast_type=toast_type, theme_id=theme_id)

    @pyqtSlot(str)
    def apply_theme(self, theme_id: str):
        """Dynamically applies the theme stylesheet and palette across all widgets without restart."""
        app = QApplication.instance()
        t = get_theme(theme_id)
        if app:
            hints = app.styleHints()
            if hasattr(hints, "setColorScheme"):
                hints.setColorScheme(Qt.ColorScheme.Dark if t.is_dark else Qt.ColorScheme.Light)
            scale = load_ui_scale() / 100.0
            app.setStyleSheet(get_stylesheet(t, scale=scale))
            app.setPalette(create_theme_palette(t))
        self.sidebar.apply_theme(theme_id)
        self.home_view.apply_theme(theme_id)
        self.settings_view.apply_theme(theme_id)

    @pyqtSlot(int)
    def apply_ui_scale(self, scale_percent: int):
        """Dynamically adjusts base application font size and scales stylesheet without restart."""
        app = QApplication.instance()
        scale = scale_percent / 100.0
        if app:
            base_font = app.font()
            base_font.setPointSize(max(7, int(round(10 * scale))))
            app.setFont(base_font)
            theme_id = load_theme()
            t = get_theme(theme_id)
            app.setStyleSheet(get_stylesheet(t, scale=scale))

    def _check_dependencies_on_launch(self):
        """Checks system dependencies and alerts the user if FFmpeg is missing."""
        ff_info = DependencyManager().detect(force_recheck=True)
        if not ff_info.get("installed"):
            self.show_toast("FFmpeg was not detected on system PATH. Install FFmpeg for media conversions.", "error")

    def _check_updates_on_launch(self):
        """Triggers asynchronous update check against PyPI for yt-dlp on application launch."""
        self._launch_check_worker = EngineCheckWorker(self)
        self._launch_check_worker.checked.connect(self._on_launch_check_finished)
        self._launch_check_worker.start()

    @pyqtSlot(dict)
    def _on_launch_check_finished(self, res: dict):
        if res.get("status") == "success":
            update_avail = res.get("update_available", False)
            installed_ver = res.get("installed")
            self.sidebar.refresh_engine_status(version=installed_ver, update_available=update_avail)
            if update_avail:
                self.settings_view.notify_update_available(res)
                self.show_toast(f"yt-dlp update available ({res.get('latest')})", "info")

    @pyqtSlot(dict)
    def _on_engine_status_changed(self, data: dict):
        update_avail = data.get("update_available", False)
        ver = data.get("version")
        self.sidebar.refresh_engine_status(version=ver, update_available=update_avail)

    @pyqtSlot(dict)
    def _on_sidebar_engine_checked(self, res: dict):
        if res.get("status") == "success":
            if res.get("update_available"):
                self.settings_view.notify_update_available(res)
            else:
                self.settings_view.refresh_all()

    @pyqtSlot(dict)
    def _on_sidebar_engine_updated(self, res: dict):
        new_ver = res.get("version", "")
        self.settings_view.notify_engine_updated(new_ver)

    @pyqtSlot(str)
    def _on_page_changed(self, page_name: str):
        self.sidebar.update_storage(self.home_view.active_folder)
        if page_name == "home":
            self.stack.setCurrentIndex(0)
        elif page_name == "history":
            self.history_view.refresh()
            self.stack.setCurrentIndex(1)
        elif page_name == "settings":
            self.settings_view.refresh_all()
            self.stack.setCurrentIndex(2)

    @pyqtSlot(str)
    def _on_settings_folder_changed(self, folder: str):
        self.home_view.set_active_folder(folder)
        self.sidebar.update_storage(folder)

    def _check_file_exists(self, folder: str, title: str, dl_type: str, audio_fmt: str) -> tuple[bool, str]:
        if not folder or not os.path.exists(folder) or not title or title == 'Media Download':
            return False, ""
        
        # Extensions to check
        if dl_type == 'audio':
            exts = [audio_fmt.lower(), 'mp3', 'm4a', 'flac', 'wav', 'aac', 'opus']
        else:
            exts = ['mp4', 'mkv', 'webm']
        
        sanitized_title = sanitize_filename(title)
        
        for ext in exts:
            p1 = os.path.join(folder, f"{sanitized_title}.{ext}")
            if os.path.exists(p1):
                return True, p1
            p2 = os.path.join(folder, f"{title}.{ext}")
            if os.path.exists(p2):
                return True, p2
                
        try:
            target_stems = {sanitized_title.lower(), title.lower()}
            for entry in os.listdir(folder):
                name, ext = os.path.splitext(entry)
                if ext.lstrip('.').lower() in exts and name.lower() in target_stems:
                    return True, os.path.join(folder, entry)
        except Exception:
            pass
            
        return False, ""

    @pyqtSlot(dict)
    def _on_download_requested(self, payload: dict):
        folder = payload.get('folder', '')
        title = payload.get('title', '')
        dl_type = payload.get('type', 'video')
        audio_fmt = payload.get('audio_format', 'mp3')

        # Check if file already exists in target destination folder
        exists, existing_path = self._check_file_exists(folder, title, dl_type, audio_fmt)
        if exists:
            display_name = os.path.splitext(os.path.basename(existing_path))[0] if existing_path else title
            theme_id = self.home_view.theme.id if hasattr(self.home_view, 'theme') else 'dark'
            confirmed = ConfirmDialog.ask_overwrite(self, filename=display_name, theme_id=theme_id)
            if not confirmed:
                self.home_view.set_status("Download cancelled (file already exists)")
                return

        self.id_counter += 1
        dl_id = f"dl_{int(time.time() * 1000)}_{self.id_counter}"
        payload['id'] = dl_id

        # Instantiate download card in panel immediately
        self.downloads_panel.add_download(payload)
        self.download_queue.append(payload)

        if self.current_worker and self.current_worker.isRunning():
            queue_len = len(self.download_queue)
            self.home_view.set_status(f"Added to queue: {payload['title']} ({queue_len} in queue)")
            self.home_view.set_downloading(True)
        else:
            self._process_queue()

    def _process_queue(self):
        if self.current_worker and self.current_worker.isRunning():
            return

        if not self.download_queue:
            self.current_worker = None
            self.current_payload = None
            self.home_view.set_downloading(False)
            self.home_view.set_status("Ready to analyze media link.")
            if load_auto_close_panel():
                if not self.downloads_panel.has_active_downloads() and not self.downloads_panel.has_failed_downloads():
                    QTimer.singleShot(1400, self._auto_close_panel_if_idle)
            return

        self.current_payload = self.download_queue.pop(0)
        dl_id = self.current_payload['id']

        self.home_view.set_downloading(True)
        self.home_view.set_status(f"Starting download: {self.current_payload['title']}")
        self.downloads_panel.mark_download_active(dl_id)

        worker_quality = self.current_payload.get('audio_bitrate', self.current_payload.get('quality', '320')) if self.current_payload.get('type') == 'audio' else self.current_payload.get('quality', 'best')

        self.current_worker = DownloadWorker(
            download_id=dl_id,
            url=self.current_payload['url'],
            folder=self.current_payload['folder'],
            download_type=self.current_payload['type'],
            quality=worker_quality,
            audio_format=self.current_payload.get('audio_format', 'mp3'),
            custom_title=self.current_payload.get('title') if self.current_payload.get('title') != 'Media Download' and not self.current_payload.get('is_playlist_item') else None,
            custom_artist=self.current_payload.get('artist') or None,
            embed_thumbnail=self.current_payload.get('embed_artwork', True),
            embed_tags=self.current_payload.get('write_id3', True),
            embed_chapters=self.current_payload.get('embed_chapters', True),
            embed_subtitles=self.current_payload.get('embed_subtitles', False),
            playlist_index=self.current_payload.get('playlist_index')
        )
        self.current_worker.progress.connect(self._on_download_progress)
        self.current_worker.finished.connect(self._on_download_finished)
        self.current_worker.log_msg.connect(self._on_download_log)
        self.current_worker.playlist_metadata.connect(self._on_playlist_metadata)
        self.current_worker.start()

    def _auto_close_panel_if_idle(self):
        if not self.current_worker and not self.download_queue:
            if load_auto_close_panel() and not self.downloads_panel.has_active_downloads() and not self.downloads_panel.has_failed_downloads():
                self.downloads_panel.hide()

    @pyqtSlot(dict)
    def _on_retry_requested(self, payload: dict):
        # Match main: block retry if any download is currently running
        if self.current_worker and self.current_worker.isRunning():
            self.show_toast("⚠️ Finish current download before retrying.", "warning")
            return

        dl_id = payload.get('id')
        if not dl_id:
            return
        card = self.downloads_panel.cards.get(dl_id)
        if card:
            card.set_queued()
            self.downloads_panel.move_to_active(card)

        # Append payload to queue if not already present
        if not any(item.get('id') == dl_id for item in self.download_queue):
            self.download_queue.append(payload)

        self._process_queue()

    @pyqtSlot(list, str)
    def _on_playlist_metadata(self, items: list, target_folder: str):
        if not items:
            return

        # 1. Remove the temporary playlist placeholder card
        if self.current_payload:
            placeholder_id = self.current_payload.get('id')
            if placeholder_id and placeholder_id in self.downloads_panel.cards:
                self.downloads_panel.remove_card(placeholder_id)

        parent_payload = self.current_payload or {}
        dl_folder = target_folder or parent_payload.get('folder', '')
        dl_type = parent_payload.get('type', 'audio')
        audio_fmt = parent_payload.get('audio_format', 'mp3')
        quality = parent_payload.get('quality', '320')
        audio_bitrate = parent_payload.get('audio_bitrate', '320')
        embed_art = parent_payload.get('embed_artwork', True)
        write_tags = parent_payload.get('write_id3', True)
        embed_chap = parent_payload.get('embed_chapters', True)
        embed_subs = parent_payload.get('embed_subtitles', False)

        # 2. Add individual cards for each track
        for item in items:
            track_id = item.get('id', 'temp_id')
            track_index = item.get('index', 1)
            raw_title = item.get('title', f"Track {track_index}")
            track_title = f"{track_index:02d} - {raw_title}"
            track_url = f"https://www.youtube.com/watch?v={track_id}"

            track_payload = {
                'id': track_id,
                'url': track_url,
                'folder': dl_folder,
                'title': track_title,
                'raw_title': raw_title,
                'type': dl_type,
                'quality': quality,
                'audio_format': audio_fmt,
                'audio_bitrate': audio_bitrate,
                'playlist_index': track_index,
                'playlist_title': os.path.basename(dl_folder),
                'embed_artwork': embed_art,
                'write_id3': write_tags,
                'embed_chapters': embed_chap,
                'embed_subtitles': embed_subs,
                'status': 'queued',
                'is_playlist_item': True
            }
            self.downloads_panel.add_download(track_payload)

        self.home_view.set_status(f"Downloading playlist: {len(items)} tracks queued")
        self.show_toast(f"Playlist added ({len(items)} tracks)", "info")

    @pyqtSlot(str, dict)
    def _on_download_progress(self, dl_id: str, data: dict):
        target_id = dl_id if dl_id in self.downloads_panel.cards else (data.get('id') if data.get('id') in self.downloads_panel.cards else dl_id)
        self.downloads_panel.update_progress(target_id, data)

        status = data.get('status', '')
        if status == 'downloading':
            pct = data.get('percent', 0)
            speed = data.get('speed', '0 B/s')
            eta = data.get('eta', '0:00')
            title = data.get('title', '')
            if title and title != 'Extracting video info...':
                self.home_view.set_status(f"Downloading: {title} — {pct:.1f}% ({speed})")
            else:
                self.home_view.set_status(f"Downloading: {pct:.1f}% ({speed}, ETA {eta})")
        elif status == 'converting':
            self.home_view.set_status("Processing & embedding metadata...")

    @pyqtSlot(str, str)
    def _on_download_log(self, dl_id: str, msg: str):
        logger.debug(f"[{dl_id}] {msg}")

    @pyqtSlot(str, list, int, bool)
    def _on_download_finished(self, dl_id: str, files: list, total_count: int, was_cancelled: bool):
        if dl_id in self.downloads_panel.cards:
            self.downloads_panel.set_download_finished(dl_id, files, was_cancelled, total_count=total_count)

        finished_title = self.current_payload.get('title', 'Media') if self.current_payload else 'Media'

        if was_cancelled:
            self.home_view.set_status(f"Cancelled download: {finished_title}")
            self.downloads_panel.mark_remaining_as_cancelled()
        elif files:
            if total_count > 1 and len(files) < total_count:
                self.home_view.set_status(f"⚠️ Partial download: {len(files)}/{total_count} tracks completed ({finished_title})")
                self.show_toast(f"Partial download: {len(files)}/{total_count} tracks", "warning")
            else:
                self.home_view.set_status(f"✓ Download completed: {finished_title}")
                self.show_toast("Download completed", "success")
            # Record in history file
            try:
                history = load_history()
                for f in files:
                    if not any(h.get('filePath') == f for h in history):
                        history.append({
                            'title': os.path.basename(f),
                            'filePath': f,
                            'fileSize': get_file_size_str(f),
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"),
                            'format': self.current_payload['type'] if self.current_payload else 'video',
                            'url': self.current_payload['url'] if self.current_payload else ''
                        })
                save_history(history[-HISTORY_LIMIT:])
                self.history_view.refresh()
            except Exception as e:
                logger.error(f"Failed to append to history for {dl_id}: {e}")

            # Update available storage in sidebar
            self.sidebar.update_storage(self.home_view.active_folder)
        else:
            self.home_view.set_status(f"❌ Download failed: {finished_title}")
            self.show_toast("Download failed. Click Retry in Downloads panel.", "error")

        # Reset active worker and process next queued item
        self.current_worker = None
        self.current_payload = None
        self._process_queue()

    @pyqtSlot(str)
    def _on_cancel_requested(self, dl_id: str):
        if self.current_worker and self.current_payload and self.current_payload.get('id') == dl_id:
            self.home_view.set_status("Cancelling active download...")
            self.current_worker.cancel()
        else:
            # Check if waiting in queue
            for idx, item in enumerate(self.download_queue):
                if item.get('id') == dl_id:
                    self.download_queue.pop(idx)
                    self.downloads_panel.set_download_cancelled(dl_id)
                    self.home_view.set_status(f"Cancelled queued download: {item.get('title', 'Media')}")
                    break

    @pyqtSlot()
    def _on_home_cancel_requested(self):
        if self.current_worker and self.current_worker.isRunning():
            self.home_view.set_status("Cancelling active download...")
            self.current_worker.cancel()

    def closeEvent(self, event):
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait(1500)
        event.accept()
