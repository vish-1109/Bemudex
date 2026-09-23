import os
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QWidget
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from services.history_manager import get_file_size_str
from ui.linux_desktop import open_file_in_default_app, show_file_in_file_manager


class DownloadCard(QFrame):
    """Card widget representing an individual download in active, queued, completed, or failed state."""
    cancel_requested = pyqtSignal(str)
    retry_requested = pyqtSignal(dict)
    dismiss_requested = pyqtSignal(str)

    def __init__(self, download_id: str, payload: dict, parent=None):
        super().__init__(parent)
        self.download_id = download_id
        self.payload = payload
        self.status = "queued"
        self.files = []
        self.thumbnail_url = payload.get('thumbnail', '')
        self.title_text = payload.get('title', 'Media Download')
        self.dl_type = payload.get('type', 'video')
        self.quality = payload.get('quality', '1080')
        self.audio_format = payload.get('audio_format', 'mp3')

        self.network_mgr = QNetworkAccessManager(self)
        self.network_mgr.finished.connect(self._on_thumbnail_loaded)

        self._init_ui()
        if self.thumbnail_url:
            self._load_thumbnail(self.thumbnail_url)

    def _init_ui(self):
        self.setObjectName("downloadCard")
        self.setProperty("status", self.status)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Top row: Thumbnail + Title & Meta Column + Cancel Button
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)

        # Thumbnail
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setObjectName("cardThumbnail")
        self.lbl_thumb.setFixedSize(58, 35)
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_placeholder_thumbnail()
        top_layout.addWidget(self.lbl_thumb)

        # Info column
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        self.lbl_title = QLabel(self.title_text)
        self.lbl_title.setObjectName("cardTitle")
        self.lbl_title.setWordWrap(True)
        info_layout.addWidget(self.lbl_title)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)

        fmt_desc = f"{self.dl_type.upper()} • {self.quality}p" if self.dl_type == "video" else f"AUDIO • {self.audio_format.upper()}"
        self.lbl_meta = QLabel(fmt_desc)
        self.lbl_meta.setObjectName("cardMeta")
        meta_row.addWidget(self.lbl_meta)

        self.lbl_badge = QLabel("Queued")
        self.lbl_badge.setObjectName("cardBadge")
        meta_row.addWidget(self.lbl_badge)
        meta_row.addStretch()

        info_layout.addLayout(meta_row)
        top_layout.addLayout(info_layout, 1)

        # Cancel / Dismiss button
        self.btn_cancel = QPushButton("✕")
        self.btn_cancel.setObjectName("btnCardCancel")
        self.btn_cancel.setFixedSize(22, 22)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setToolTip("Cancel this download")
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        top_layout.addWidget(self.btn_cancel)

        layout.addLayout(top_layout)

        # Progress bar
        self.bar_progress = QProgressBar()
        self.bar_progress.setObjectName("downloadProgress")
        self.bar_progress.setValue(0)
        self.bar_progress.setTextVisible(False)
        layout.addWidget(self.bar_progress)

        # Stats label
        self.lbl_stats = QLabel("Waiting in queue...")
        self.lbl_stats.setObjectName("cardStats")
        self.lbl_stats.setWordWrap(True)
        layout.addWidget(self.lbl_stats)

        # Action buttons row (for completed / failed downloads)
        self.actions_widget = QWidget()
        actions_layout = QHBoxLayout(self.actions_widget)
        actions_layout.setContentsMargins(0, 4, 0, 0)
        actions_layout.setSpacing(8)

        self.btn_retry = QPushButton("Retry")
        self.btn_retry.setObjectName("btnCardRetry")
        self.btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_retry.clicked.connect(self._on_retry_clicked)
        actions_layout.addWidget(self.btn_retry)
        self.btn_retry.hide()

        self.btn_open = QPushButton("Open File")
        self.btn_open.setObjectName("btnCardAction")
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.clicked.connect(self._on_open_clicked)
        actions_layout.addWidget(self.btn_open)

        self.btn_folder = QPushButton("Show in Folder")
        self.btn_folder.setObjectName("btnCardAction")
        self.btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_folder.clicked.connect(self._on_folder_clicked)
        actions_layout.addWidget(self.btn_folder)

        actions_layout.addStretch()
        layout.addWidget(self.actions_widget)
        self.actions_widget.hide()

    def _set_placeholder_thumbnail(self):
        icon = "🎬" if self.dl_type == "video" else "🎵"
        self.lbl_thumb.setText(icon)
        self.lbl_thumb.setStyleSheet("")

    def _load_thumbnail(self, url: str):
        if url.startswith("http://") or url.startswith("https://"):
            self.network_mgr.get(QNetworkRequest(QUrl(url)))
        elif os.path.exists(url):
            pix = QPixmap(url)
            if not pix.isNull():
                self._apply_pixmap(pix)

    @pyqtSlot(QNetworkReply)
    def _on_thumbnail_loaded(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            pix = QPixmap()
            pix.loadFromData(reply.readAll())
            if not pix.isNull():
                self._apply_pixmap(pix)
        reply.deleteLater()

    def _apply_pixmap(self, pix: QPixmap):
        scaled = pix.scaled(
            58, 35,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        self.lbl_thumb.setPixmap(scaled)
        self.lbl_thumb.setStyleSheet("background-color: #000; border-radius: 4px;")

    def set_active(self):
        """Marks card as actively downloading."""
        self.status = "downloading"
        self.lbl_badge.setText("Downloading")
        self.lbl_stats.setText("Starting download...")
        self.bar_progress.show()
        self.btn_cancel.show()
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setToolTip("Cancel this download")
        self.btn_retry.hide()
        self.actions_widget.hide()
        self._polish_style()

    def set_queued(self):
        """Resets card to queued state for retry."""
        self.status = "queued"
        self.lbl_badge.setText("Queued")
        self.lbl_stats.setText("Waiting in queue...")
        self.bar_progress.setValue(0)
        self.bar_progress.show()
        self.btn_cancel.show()
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setToolTip("Cancel this download")
        self.btn_retry.hide()
        self.btn_open.hide()
        self.btn_folder.hide()
        self.actions_widget.hide()
        self._polish_style()

    def update_progress(self, data: dict):
        """Updates UI with progress payload from yt-dlp hook."""
        status = data.get('status', '')
        if status == 'downloading':
            self.status = "downloading"
            self.lbl_badge.setText("Downloading")
            pct = int(data.get('percent', 0))
            self.bar_progress.setValue(pct)
            self.bar_progress.show()
            speed = data.get('speed', '0 B/s')
            eta = data.get('eta', '0:00')
            size_info = data.get('sizeInfo', '')
            self.lbl_stats.setText(f"{pct}% • {speed} • {size_info} • ETA {eta}")

            # Update title and thumbnail if discovered dynamically
            incoming_title = data.get('title')
            if incoming_title and incoming_title != 'Extracting video info...' and self.title_text == 'Media Download':
                self.title_text = incoming_title
                self.lbl_title.setText(incoming_title)
            incoming_thumb = data.get('thumbnail')
            if incoming_thumb and not self.thumbnail_url:
                self.thumbnail_url = incoming_thumb
                self._load_thumbnail(incoming_thumb)

        elif status == 'converting':
            self.status = "converting"
            self.lbl_badge.setText("Processing")
            self.bar_progress.setValue(100)
            self.lbl_stats.setText("Processing & embedding tags...")
            self.btn_cancel.setEnabled(False)

        elif status == 'failed':
            self.set_failed(data.get('sizeInfo', 'Download failed'))

        self._polish_style()

    def set_finished(self, files: list):
        """Marks card as successfully completed."""
        self.status = "finished"
        self.files = files
        self.bar_progress.hide()
        self.btn_cancel.hide()
        self.btn_retry.hide()
        self.btn_open.show()
        self.btn_folder.show()

        count = len(files)
        if count > 1:
            self.lbl_badge.setText("Completed")
            self.lbl_stats.setText(f"✓ Completed ({count} files)")
        elif count == 1:
            self.lbl_badge.setText("Completed")
            size_str = get_file_size_str(files[0])
            filename = os.path.basename(files[0])
            self.lbl_title.setText(filename)
            self.lbl_stats.setText(f"✓ Completed • {size_str}")
        else:
            self.set_failed("No output files generated")
            return

        self.actions_widget.show()
        self._polish_style()

    def set_cancelled(self):
        """Marks card as cancelled by user with option to retry."""
        self.status = "cancelled"
        self.bar_progress.hide()
        self.btn_cancel.show()
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setToolTip("Dismiss")
        self.lbl_badge.setText("Cancelled")
        self.lbl_stats.setText("Cancelled by user")
        self.btn_retry.show()
        self.btn_open.hide()
        self.btn_folder.hide()
        self.actions_widget.show()
        self._polish_style()

    def set_failed(self, reason: str = "Download failed"):
        """Marks card as failed with specific error reason and displays Retry."""
        self.status = "failed"
        self.bar_progress.hide()
        self.btn_cancel.show()
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setToolTip("Dismiss")
        self.lbl_badge.setText("Failed")
        self.lbl_stats.setText(f"❌ {reason}")
        self.btn_retry.show()
        if self.files:
            self.btn_open.show()
            self.btn_folder.show()
        else:
            self.btn_open.hide()
            self.btn_folder.hide()
        self.actions_widget.show()
        self._polish_style()

    def _polish_style(self):
        self.setProperty("status", self.status)
        self.style().polish(self)
        self.lbl_badge.setProperty("status", self.status)
        self.lbl_badge.style().polish(self.lbl_badge)

    def _on_cancel_clicked(self):
        if self.status in ('failed', 'cancelled', 'finished'):
            self.dismiss_requested.emit(self.download_id)
        else:
            self.cancel_requested.emit(self.download_id)

    def _on_retry_clicked(self):
        self.retry_requested.emit(self.payload)

    def _on_open_clicked(self):
        if self.files:
            open_file_in_default_app(self.files[0])

    def _on_folder_clicked(self):
        if self.files:
            show_file_in_file_manager(self.files[0])
        elif self.payload.get('folder'):
            show_file_in_file_manager(self.payload['folder'])
