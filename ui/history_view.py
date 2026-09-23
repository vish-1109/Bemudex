import os
from datetime import datetime, timedelta
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QSizePolicy
)

from services.history_manager import load_history, save_history, get_file_size_str
from services.config_manager import load_theme
from ui.confirm_dialog import ConfirmDialog
from ui.linux_desktop import open_file_in_default_app, show_file_in_file_manager


def format_date_group(timestamp_str: str) -> str:
    """Classifies a timestamp string into a human-readable group: Today, Yesterday, or formatted date."""
    if not timestamp_str:
        return "Earlier"
    try:
        date_part = timestamp_str.split()[0]
        today_str = datetime.now().strftime("%Y-%m-%d")
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if date_part == today_str:
            return "Today"
        elif date_part == yesterday_str:
            return "Yesterday"
        else:
            dt = datetime.strptime(date_part, "%Y-%m-%d")
            return dt.strftime("%B %d, %Y")
    except Exception:
        return "Earlier"


class HistoryItemCard(QFrame):
    """Card widget representing an individual download history record."""
    delete_requested = pyqtSignal(dict)

    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.item = item
        self.file_path = item.get('filePath', '')
        self.file_exists = os.path.exists(self.file_path) if self.file_path else False
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("historyItemCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        # 1. Format Icon Fallback
        fmt = self.item.get('format', 'video').lower()
        self.lbl_icon = QLabel("🎬" if fmt == 'video' else "🎵")
        self.lbl_icon.setObjectName("historyIcon")
        self.lbl_icon.setFixedSize(48, 48)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_icon)

        # 2. Details Column
        details_layout = QVBoxLayout()
        details_layout.setSpacing(6)

        title_text = self.item.get('title', 'Unknown Media')
        self.lbl_title = QLabel(title_text)
        self.lbl_title.setObjectName("historyTitle")
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.lbl_title.setMinimumWidth(0)
        details_layout.addWidget(self.lbl_title)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)

        # Format Badge
        badge_fmt = QLabel(fmt.upper())
        badge_fmt.setProperty("class", "badge-pill")
        meta_row.addWidget(badge_fmt)

        # File Size Badge
        size_str = self.item.get('fileSize')
        if not size_str or size_str == 'Unknown size':
            if self.file_exists:
                size_str = get_file_size_str(self.file_path)
            else:
                size_str = "Unavailable"
        badge_size = QLabel(size_str)
        badge_size.setProperty("class", "badge-pill")
        meta_row.addWidget(badge_size)

        # Timestamp
        ts = self.item.get('timestamp', '')
        if ts:
            lbl_time = QLabel(ts)
            lbl_time.setObjectName("historyTimestamp")
            meta_row.addWidget(lbl_time)

        meta_row.addStretch()
        details_layout.addLayout(meta_row)

        # Missing File Notice
        if not self.file_exists:
            missing_row = QHBoxLayout()
            missing_row.setContentsMargins(0, 3, 0, 0)
            lbl_missing = QLabel("⚠️  File no longer exists on disk")
            lbl_missing.setObjectName("missingFileNotice")
            missing_row.addWidget(lbl_missing)
            missing_row.addStretch()
            details_layout.addLayout(missing_row)

        layout.addLayout(details_layout, 1)

        # 3. Actions Column
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)

        self.btn_open = QPushButton("Open")
        self.btn_open.setObjectName("btnHistoryAction")
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.setEnabled(self.file_exists)
        if not self.file_exists:
            self.btn_open.setToolTip("File no longer exists on disk")
        else:
            self.btn_open.setToolTip("Open media file in default application")
        self.btn_open.clicked.connect(self._on_open_clicked)
        actions_layout.addWidget(self.btn_open)

        self.btn_folder = QPushButton("Folder")
        self.btn_folder.setObjectName("btnHistoryAction")
        self.btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_folder.setToolTip("Reveal in system file manager")
        self.btn_folder.clicked.connect(self._on_folder_clicked)
        actions_layout.addWidget(self.btn_folder)

        self.btn_delete = QPushButton("✕")
        self.btn_delete.setObjectName("btnHistoryDelete")
        self.btn_delete.setFixedSize(24, 24)
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setToolTip("Remove from history")
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.item))
        actions_layout.addWidget(self.btn_delete)

        layout.addLayout(actions_layout)

    def _on_open_clicked(self):
        if self.file_exists:
            open_file_in_default_app(self.file_path)

    def _on_folder_clicked(self):
        if self.file_path:
            show_file_in_file_manager(self.file_path)


class HistoryView(QWidget):
    """Primary History screen displaying past downloads with search, filters, and record management."""
    toast_requested = pyqtSignal(str, str)
    history_count_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("centerWidget")
        self.all_history = []
        self.active_filter = "all"  # "all", "video", "audio"
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(52, 44, 52, 44)
        main_layout.setSpacing(20)

        # 1. Header: Title, Subtitle, and Clear History Button
        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        lbl_title = QLabel("History")
        lbl_title.setObjectName("greetingTitle")
        title_col.addWidget(lbl_title)

        lbl_sub = QLabel("Review, search, and manage your downloaded media.")
        lbl_sub.setObjectName("greetingSubtitle")
        title_col.addWidget(lbl_sub)
        header_row.addLayout(title_col, 1)

        self.btn_clear_all = QPushButton("Clear History")
        self.btn_clear_all.setObjectName("btnClearHistory")
        self.btn_clear_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_all.clicked.connect(self._on_clear_history_clicked)
        header_row.addWidget(self.btn_clear_all)

        main_layout.addLayout(header_row)

        # 2. Search Bar and Filter Chips
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.input_search = QLineEdit()
        self.input_search.setObjectName("historySearchInput")
        self.input_search.setPlaceholderText("Search history by title, format, or file path...")
        self.input_search.textChanged.connect(self._apply_filter)
        filter_bar.addWidget(self.input_search, 1)

        # Clear search input button
        self.btn_clear_search = QPushButton("✕")
        self.btn_clear_search.setObjectName("btnClearSearch")
        self.btn_clear_search.setFixedSize(24, 24)
        self.btn_clear_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_search.setToolTip("Clear search")
        self.btn_clear_search.clicked.connect(self.input_search.clear)
        filter_bar.addWidget(self.btn_clear_search)

        # Format filter chips
        self.btn_filter_all = QPushButton("All")
        self.btn_filter_all.setProperty("class", "filter-chip active")
        self.btn_filter_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_filter_all.clicked.connect(lambda: self._set_format_filter("all"))
        filter_bar.addWidget(self.btn_filter_all)

        self.btn_filter_video = QPushButton("Video")
        self.btn_filter_video.setProperty("class", "filter-chip")
        self.btn_filter_video.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_filter_video.clicked.connect(lambda: self._set_format_filter("video"))
        filter_bar.addWidget(self.btn_filter_video)

        self.btn_filter_audio = QPushButton("Audio")
        self.btn_filter_audio.setProperty("class", "filter-chip")
        self.btn_filter_audio.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_filter_audio.clicked.connect(lambda: self._set_format_filter("audio"))
        filter_bar.addWidget(self.btn_filter_audio)

        main_layout.addLayout(filter_bar)

        # 3. Scroll Area for History List
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("historyScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setMinimumWidth(300)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scrollContent")
        self.list_layout = QVBoxLayout(self.scroll_content)
        self.list_layout.setContentsMargins(0, 4, 4, 12)
        self.list_layout.setSpacing(12)

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

    def refresh(self):
        """Reloads records from history JSON storage and updates view."""
        self.all_history = load_history()
        # Sort newest first
        self.all_history.reverse()
        self.history_count_changed.emit(len(self.all_history))
        self._apply_filter()

    def _set_format_filter(self, fmt: str):
        self.active_filter = fmt
        self.btn_filter_all.setProperty("class", "filter-chip active" if fmt == "all" else "filter-chip")
        self.btn_filter_video.setProperty("class", "filter-chip active" if fmt == "video" else "filter-chip")
        self.btn_filter_audio.setProperty("class", "filter-chip active" if fmt == "audio" else "filter-chip")
        self.btn_filter_all.style().polish(self.btn_filter_all)
        self.btn_filter_video.style().polish(self.btn_filter_video)
        self.btn_filter_audio.style().polish(self.btn_filter_audio)
        self._apply_filter()

    def _apply_filter(self):
        """Filters the stored history items and repopulates the grouped list."""
        query = self.input_search.text().strip().lower()

        # Filter items
        filtered = []
        for item in self.all_history:
            # Format filter match
            item_fmt = item.get('format', 'video').lower()
            if self.active_filter != "all" and item_fmt != self.active_filter:
                continue

            # Query match (title, path, format, url)
            if query:
                title = item.get('title', '').lower()
                path = item.get('filePath', '').lower()
                url = item.get('url', '').lower()
                if query not in title and query not in path and query not in item_fmt and query not in url:
                    continue

            filtered.append(item)

        self._render_list(filtered)

    def _render_list(self, items: list):
        """Renders grouped history cards into the scroll layout."""
        # Clear existing widgets from layout
        while self.list_layout.count() > 0:
            child = self.list_layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
            elif child.layout():
                # Clean sub-layouts
                while child.layout().count() > 0:
                    sub = child.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().setParent(None)
                        sub.widget().deleteLater()

        # Update Clear All button availability
        self.btn_clear_all.setEnabled(len(self.all_history) > 0)

        if not items:
            empty_msg = (
                "No downloads match your search."
                if (self.input_search.text().strip() or self.active_filter != "all")
                else "No downloads in history yet."
            )
            lbl_empty = QLabel(empty_msg)
            lbl_empty.setObjectName("historyEmptyState")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.addWidget(lbl_empty)
            self.list_layout.addStretch()
            return

        # Group items by date string
        groups = {}
        for item in items:
            group_key = format_date_group(item.get('timestamp', ''))
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(item)

        # Render groups
        for group_title, group_items in groups.items():
            # Date group header
            lbl_group = QLabel(group_title)
            lbl_group.setObjectName("historyDateHeader")
            self.list_layout.addWidget(lbl_group)

            # Item cards
            for item in group_items:
                card = HistoryItemCard(item, self.scroll_content)
                card.delete_requested.connect(self._on_delete_item)
                self.list_layout.addWidget(card)

            self.list_layout.addSpacing(6)

        self.list_layout.addStretch()

    @pyqtSlot(dict)
    def _on_delete_item(self, item_to_delete: dict):
        """Deletes an individual history entry from storage and refreshes the view."""
        current_records = load_history()
        target_path = item_to_delete.get('filePath')
        target_ts = item_to_delete.get('timestamp')
        target_url = item_to_delete.get('url')

        new_records = [
            r for r in current_records
            if not (r.get('filePath') == target_path and
                    r.get('timestamp') == target_ts and
                    r.get('url') == target_url)
        ]
        save_history(new_records)
        self.refresh()
        self.toast_requested.emit("Item removed from history.", "success")

    def _on_clear_history_clicked(self):
        """Displays a modern confirmation dialog before clearing all history records."""
        theme_id = load_theme()
        confirmed = ConfirmDialog.ask(
            parent=self.window(),
            title="Clear download history?",
            message="This will remove all download records from Bemudex.\nYour downloaded media files will remain safely on disk.",
            confirm_text="Clear History",
            cancel_text="Cancel",
            is_destructive=True,
            theme_id=theme_id
        )
        if confirmed:
            save_history([])
            self.refresh()
            self.toast_requested.emit("History cleared.", "success")
