from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget, QSplitter
)

from ui.download_card import DownloadCard


class DownloadsPanel(QFrame):
    """Right-hand side downloads panel hosting active, queued, and completed download cards."""
    cancel_requested = pyqtSignal(str)
    retry_requested = pyqtSignal(dict)
    clear_completed_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("downloadsPanel")
        self.setMinimumWidth(360)
        self.setMaximumWidth(650)
        self.cards = {}  # download_id -> DownloadCard

        self._init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        parent = self.parentWidget()
        if isinstance(parent, QSplitter):
            sizes = parent.sizes()
            if len(sizes) == 2 and sizes[1] < 360:
                total = sum(sizes)
                panel_w = min(440, max(360, int(total * 0.35)))
                parent.setSizes([total - panel_w, panel_w])

    def _init_ui(self):
        panel_layout = QVBoxLayout(self)
        panel_layout.setContentsMargins(10, 14, 10, 14)
        panel_layout.setSpacing(10)

        # Header: Title + Status Counter Badge + Clear Button
        header_layout = QHBoxLayout()
        title = QLabel("Downloads")
        title.setObjectName("panelTitle")
        header_layout.addWidget(title)

        self.lbl_count_pill = QLabel("0 Active")
        self.lbl_count_pill.setObjectName("panelCountPill")
        header_layout.addWidget(self.lbl_count_pill)
        header_layout.addStretch()

        self.btn_clear = QPushButton("✕")
        self.btn_clear.setObjectName("btnClearCompleted")
        self.btn_clear.setFixedSize(22, 22)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setToolTip("Close panel (clears completed downloads)")
        self.btn_clear.clicked.connect(self._on_close_clicked)
        header_layout.addWidget(self.btn_clear)

        panel_layout.addLayout(header_layout)

        # Scroll Area for Download Cards
        scroll = QScrollArea()
        scroll.setObjectName("downloadsScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        self.content_layout = QVBoxLayout(scroll_content)
        self.content_layout.setContentsMargins(0, 0, 4, 0)
        self.content_layout.setSpacing(12)

        # Section 1: Active & Queued Downloads
        self.lbl_active_header = QLabel("ACTIVE")
        self.lbl_active_header.setObjectName("panelSectionHeader")
        self.content_layout.addWidget(self.lbl_active_header)
        self.lbl_active_header.hide()

        self.active_container = QVBoxLayout()
        self.active_container.setSpacing(8)
        self.content_layout.addLayout(self.active_container)

        # Section 2: Completed / History Downloads
        self.lbl_completed_header = QLabel("COMPLETED")
        self.lbl_completed_header.setObjectName("panelSectionHeader")
        self.content_layout.addWidget(self.lbl_completed_header)
        self.lbl_completed_header.hide()

        self.completed_container = QVBoxLayout()
        self.completed_container.setSpacing(8)
        self.content_layout.addLayout(self.completed_container)

        self.content_layout.addStretch()
        scroll.setWidget(scroll_content)
        panel_layout.addWidget(scroll)

    def add_download(self, payload: dict) -> DownloadCard:
        """Instantiates a new DownloadCard and places it in the active container."""
        dl_id = payload['id']
        card = DownloadCard(dl_id, payload, self)
        card.cancel_requested.connect(self.cancel_requested.emit)
        card.retry_requested.connect(self.retry_requested.emit)
        card.dismiss_requested.connect(self._on_dismiss_card)

        self.cards[dl_id] = card
        self.active_container.addWidget(card)
        self._update_counts()
        self.show()
        return card

    def mark_download_active(self, download_id: str):
        """Notifies a specific card that its worker thread has begun execution."""
        card = self.cards.get(download_id)
        if card:
            card.set_active()
            self._update_counts()

    def update_progress(self, download_id: str, data: dict):
        """Forwards yt-dlp progress hook data to the matching download card."""
        card = self.cards.get(download_id)
        if card:
            status = data.get('status', '')
            if status == 'finished':
                fp = data.get('filePath')
                files = [fp] if fp else []
                card.set_finished(files)
                self._move_to_completed(card)
            elif status == 'failed':
                card.set_failed(data.get('sizeInfo', 'Download failed'))
                self._move_to_completed(card)
            else:
                card.update_progress(data)
            self._update_counts()

    def remove_card(self, download_id: str):
        """Removes a card (e.g. temporary playlist placeholder) from the panel."""
        card = self.cards.pop(download_id, None)
        if card:
            if self.active_container.indexOf(card) != -1:
                self.active_container.removeWidget(card)
            if self.completed_container.indexOf(card) != -1:
                self.completed_container.removeWidget(card)
            card.deleteLater()
            self._update_counts()

    def mark_remaining_as_cancelled(self):
        """Marks any currently active or queued cards as cancelled."""
        for card in list(self.cards.values()):
            if card.status in ('queued', 'downloading', 'converting'):
                card.set_cancelled()
                self._move_to_completed(card)
        self._update_counts()

    def set_download_finished(self, download_id: str, files: list, was_cancelled: bool = False, total_count: int = 1):
        """Transitions a card from active to completed/cancelled state and moves its layout position."""
        card = self.cards.get(download_id)
        if not card:
            return

        if was_cancelled:
            card.set_cancelled()
        elif files:
            if total_count > 1 and len(files) < total_count:
                card.files = files
                card.set_failed(f"Partial: {len(files)}/{total_count} tracks. Click Retry to resume.")
            else:
                card.set_finished(files)
        else:
            card.set_failed("Download failed. Click Retry.")

        self._move_to_completed(card)
        self._update_counts()

    def set_download_cancelled(self, download_id: str):
        """Explicitly flags a card as cancelled and moves it to completed container."""
        card = self.cards.get(download_id)
        if not card:
            return
        card.set_cancelled()
        self._move_to_completed(card)
        self._update_counts()

    def set_download_failed(self, download_id: str, reason: str = "Download failed"):
        """Explicitly flags a card as failed with a reason and moves it to completed container."""
        card = self.cards.get(download_id)
        if not card:
            return
        card.set_failed(reason)
        self._move_to_completed(card)
        self._update_counts()

    def _move_to_completed(self, card: DownloadCard):
        """Moves card widget from the active VBox to the completed VBox."""
        if self.active_container.indexOf(card) != -1:
            self.active_container.removeWidget(card)
        if self.completed_container.indexOf(card) == -1:
            self.completed_container.insertWidget(0, card)
        card.show()

    def move_to_active(self, card: DownloadCard):
        """Moves card widget from the completed VBox back to the active VBox."""
        self.completed_container.removeWidget(card)
        self.active_container.addWidget(card)
        card.show()
        self._update_counts()

    def _on_dismiss_card(self, dl_id: str):
        """Removes a dismissed card from the panel."""
        card = self.cards.get(dl_id)
        if card:
            self.active_container.removeWidget(card)
            self.completed_container.removeWidget(card)
            if dl_id in self.cards:
                del self.cards[dl_id]
            card.deleteLater()
            self._update_counts()

    def _on_clear_completed(self):
        """Clears all completed cards from the panel."""
        while self.completed_container.count() > 0:
            item = self.completed_container.takeAt(0)
            widget = item.widget()
            if widget:
                # Remove from tracking dictionary
                for dl_id, card in list(self.cards.items()):
                    if card == widget:
                        del self.cards[dl_id]
                        break
                widget.deleteLater()

        self._update_counts()
        self.clear_completed_requested.emit()

    def _on_close_clicked(self):
        """Clears completed downloads and hides the panel."""
        self._on_clear_completed()
        self.hide()

    def _update_counts(self):
        """Recalculates active, queued, and failed counts, updating header badges and section labels."""
        active_count = 0
        queued_count = 0
        completed_count = 0
        failed_count = 0

        for card in self.cards.values():
            if card.status in ('downloading', 'converting'):
                active_count += 1
            elif card.status == 'queued':
                queued_count += 1
            elif card.status == 'failed':
                failed_count += 1
                completed_count += 1
            elif card.status in ('finished', 'cancelled'):
                completed_count += 1

        parts = []
        if active_count > 0:
            parts.append(f"{active_count} Active")
        if queued_count > 0:
            parts.append(f"{queued_count} Queued")
        if failed_count > 0:
            parts.append(f"{failed_count} Failed")

        if parts:
            self.lbl_count_pill.setText(" • ".join(parts))
        elif completed_count > 0:
            self.lbl_count_pill.setText(f"{completed_count} Done")
        else:
            self.lbl_count_pill.setText("0 Active")

        # Toggle section header visibility
        total_active_or_queued = active_count + queued_count
        self.lbl_active_header.setVisible(total_active_or_queued > 0)
        self.lbl_completed_header.setVisible(completed_count > 0)

    def has_active_downloads(self) -> bool:
        """Returns True if any download cards are actively downloading or queued."""
        for card in self.cards.values():
            if card.status in ('downloading', 'converting', 'queued'):
                return True
        return False

    def has_failed_downloads(self) -> bool:
        """Returns True if any download cards are in failed state."""
        for card in self.cards.values():
            if card.status == 'failed':
                return True
        return False
