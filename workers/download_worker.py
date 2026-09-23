import threading
from PyQt6.QtCore import QThread, pyqtSignal

from services.downloader import start_download
from core.logger import logger


class DownloadWorker(QThread):
    """Background worker executing start_download with Qt signal dispatching and download IDs."""
    progress = pyqtSignal(str, dict)             # download_id / item_id, progress_data
    finished = pyqtSignal(str, list, int, bool)  # download_id, files, total_count, was_cancelled
    log_msg = pyqtSignal(str, str)               # download_id, msg
    playlist_metadata = pyqtSignal(list, str)    # items, target_folder

    def __init__(self, download_id: str, url: str, folder: str, download_type: str, quality: str,
                 audio_format: str = 'mp3', custom_title: str = None, custom_artist: str = None,
                 embed_thumbnail: bool = True, embed_tags: bool = True, embed_chapters: bool = True,
                 embed_subtitles: bool = False, playlist_index: int = None):
        super().__init__()
        self.download_id = download_id
        self.url = url.strip()
        self.folder = folder
        self.download_type = download_type
        self.quality = quality
        self.audio_format = audio_format
        self.custom_title = custom_title
        self.custom_artist = custom_artist
        self.embed_thumbnail = embed_thumbnail
        self.embed_tags = embed_tags
        self.embed_chapters = embed_chapters
        self.embed_subtitles = embed_subtitles
        self.playlist_index = playlist_index
        self.stop_event = threading.Event()
        self._done_event = threading.Event()
        self.is_playlist = False

    def cancel(self):
        """Signals the downloader to cleanly stop downloading."""
        self.stop_event.set()

    def run(self):
        def _on_progress(data):
            item_id = data.get('id') if self.is_playlist and data.get('id') else self.download_id
            self.progress.emit(item_id, data)

        def _on_log(msg):
            self.log_msg.emit(self.download_id, msg)

        def _on_playlist_metadata(items, target_folder="", is_playlist=True):
            if items and len(items) > 0:
                self.is_playlist = True
                folder_val = target_folder or (items[0].get('folder') if items else "") or self.folder
                self.playlist_metadata.emit(items, folder_val)

        def _on_done(files, total_count=1, was_cancelled=False):
            self.finished.emit(self.download_id, files, total_count, was_cancelled)
            self._done_event.set()

        try:
            start_download(
                url=self.url,
                folder=self.folder,
                download_type=self.download_type,
                quality=self.quality,
                on_progress=_on_progress,
                on_log=_on_log,
                on_done=_on_done,
                on_playlist_metadata=_on_playlist_metadata,
                stop_event=self.stop_event,
                audio_format=self.audio_format,
                title=self.custom_title,
                artist=self.custom_artist,
                embed_thumbnail=self.embed_thumbnail,
                embed_tags=self.embed_tags,
                embed_chapters=self.embed_chapters,
                embed_subtitles=self.embed_subtitles,
                playlist_index=self.playlist_index
            )
            # Block until start_download's daemon thread completes and triggers on_done
            self._done_event.wait()
        except Exception as e:
            logger.error(f"Download execution error for {self.download_id}: {e}")
            self.finished.emit(self.download_id, [], 0, False)
            self._done_event.set()
