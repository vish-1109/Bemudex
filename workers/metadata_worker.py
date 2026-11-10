import re
import yt_dlp
from PyQt6.QtCore import QThread, pyqtSignal

from services.downloader import get_ffmpeg_path, get_base_ydl_opts, clean_media_url
from core.logger import logger


class YtdlPlaylistLogger:
    """Intercepts yt-dlp extraction logs to notify about playlist items in real time."""
    def __init__(self, on_count):
        self.on_count = on_count
        self._emitted = False
        self.last_error = ""

    def debug(self, msg):
        if not self._emitted:
            m = re.search(r'Downloading\s+(\d+)\s+items', msg, re.IGNORECASE)
            if not m:
                m = re.search(r'playlist.*:\s*(\d+)\s*entries', msg, re.IGNORECASE)
            if m:
                try:
                    self._emitted = True
                    self.on_count(int(m.group(1)))
                except Exception:
                    pass

    def info(self, msg):
        self.debug(msg)

    def warning(self, msg):
        pass

    def error(self, msg):
        self.last_error = str(msg)


class MetadataWorker(QThread):
    """Background worker for extracting video/playlist metadata via yt-dlp without blocking the Qt GUI."""
    metadata_ready = pyqtSignal(dict)
    metadata_error = pyqtSignal(str)
    playlist_detected = pyqtSignal(int)

    def __init__(self, url: str):
        super().__init__()
        self.url = clean_media_url(url.strip())

    def run(self):
        playlist_logger = YtdlPlaylistLogger(lambda c: self.playlist_detected.emit(c))
        try:
            base_opts = get_base_ydl_opts()
            base_opts.pop('remote_components', None)
            
            is_playlist_hint = any(k in self.url.lower() for k in ['list=', 'playlist', '/sets/', 'album'])
            
            ydl_opts = {
                **base_opts,
                'skip_download': True,
                'ignoreerrors': True,
                'extract_flat': 'in_playlist',
                'lazy_playlist': True,
                'noplaylist': not is_playlist_hint,
                'check_formats': False,
                'get_comments': False,
                'no_warnings': True,
                'quiet': True,
                'socket_timeout': 10,
                'retries': 2,
                'fragment_retries': 2,
                'logger': playlist_logger,
            }
            ffmpeg_path = get_ffmpeg_path()
            if ffmpeg_path:
                ydl_opts['ffmpeg_location'] = ffmpeg_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)

            if not info:
                err_text = playlist_logger.last_error or "Could not extract info from URL"
                if "sign in" in err_text.lower() or "bot" in err_text.lower():
                    err_text = "YouTube bot verification triggered: Enable browser cookies in Settings to bypass."
                elif "private video" in err_text.lower():
                    err_text = "This video is private."
                elif "unavailable" in err_text.lower():
                    err_text = "This video is unavailable."
                elif "members-only" in err_text.lower():
                    err_text = "This video is members-only."
                self.metadata_error.emit(err_text)
                return

            is_playlist = info.get('_type') == 'playlist'
            playlist_count = len(info.get('entries', [])) if is_playlist else 0
            if is_playlist and playlist_count > 0:
                self.playlist_detected.emit(playlist_count)

            # Use first entry for detailed format info if playlist
            video_info = info
            if is_playlist:
                entries = info.get('entries', [])
                for entry in entries:
                    if entry:
                        video_info = entry
                        break

            # Duration formatting
            duration = video_info.get('duration') or 0
            if duration > 0:
                mins, secs = divmod(int(duration), 60)
                hours, mins = divmod(mins, 60)
                duration_str = f"{hours}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins}:{secs:02d}"
            else:
                duration_str = "0:00"

            formats = video_info.get('formats', [])
            resolutions = sorted(set(
                f.get('height') for f in formats
                if f.get('height') and f.get('vcodec') != 'none'
            ), reverse=True)

            thumbnails = video_info.get('thumbnails', [])
            thumb_url = ''
            if thumbnails:
                # Pick the ideal size for 220x124 preview (300px - 720px) to avoid downloading massive 2-4MB 4K images
                suitable = [t for t in thumbnails if t.get('width') and 300 <= t.get('width') <= 720]
                if suitable:
                    thumb_url = suitable[-1].get('url', '')
                else:
                    thumb_url = thumbnails[-1].get('url', '')
            if not thumb_url:
                thumb_url = video_info.get('thumbnail', '')

            views = video_info.get('view_count')
            if views:
                if views >= 1_000_000:
                    view_str = f"{views / 1_000_000:.1f}M views"
                elif views >= 1_000:
                    view_str = f"{views / 1_000:.1f}K views"
                else:
                    view_str = f"{views} views"
            else:
                view_str = ""

            # Upload date formatting (relative)
            upload_date_raw = video_info.get('upload_date')
            upload_date_str = ""
            if upload_date_raw:
                try:
                    from datetime import datetime as dt
                    upload = dt.strptime(str(upload_date_raw), '%Y%m%d')
                    now = dt.now()
                    diff = now - upload
                    days = diff.days
                    if days == 0:
                        upload_date_str = "Today"
                    elif days == 1:
                        upload_date_str = "Yesterday"
                    elif days < 7:
                        upload_date_str = f"{days} days ago"
                    elif days < 30:
                        weeks = max(1, days // 7)
                        upload_date_str = f"{weeks} week{'s' if weeks > 1 else ''} ago"
                    elif days < 365:
                        months = max(1, days // 30)
                        upload_date_str = f"{months} month{'s' if months > 1 else ''} ago"
                    else:
                        years = max(1, days // 365)
                        upload_date_str = f"{years} year{'s' if years > 1 else ''} ago"
                except Exception:
                    upload_date_str = str(upload_date_raw)

            # Codec detection
            has_av1 = any(
                f.get('vcodec') and ('av01' in f.get('vcodec').lower() or 'av1' in f.get('vcodec').lower())
                for f in formats
            )
            has_vp9 = any(
                f.get('vcodec') and 'vp9' in f.get('vcodec').lower()
                for f in formats
            )
            has_hdr = any(
                'hdr' in str(f.get('dynamic_range', '')).lower()
                for f in formats
            )
            fps_values = [
                f.get('fps') for f in formats
                if f.get('fps') and f.get('vcodec') != 'none'
            ]
            max_fps = int(max(fps_values)) if fps_values else int(video_info.get('fps') or 0)

            # File size estimation per resolution
            duration_est = duration if duration > 0 else 300
            resolution_sizes = {}
            audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
            best_audio_size_rate = 16000  # 128 kbps fallback
            if audio_formats:
                best_audio = audio_formats[-1]
                best_audio_size_rate = (best_audio.get('filesize') or best_audio.get('filesize_approx') or 0) / (duration_est or 1)
                if best_audio_size_rate == 0:
                    best_audio_size_rate = (best_audio.get('tbr') or 128) * 1000 / 8

            for h in resolutions:
                v_formats = [f for f in formats if f.get('height') == h and f.get('vcodec') != 'none']
                if v_formats:
                    best_vf = v_formats[-1]
                    v_size = best_vf.get('filesize') or best_vf.get('filesize_approx')
                    if not v_size:
                        tbr = best_vf.get('tbr') or (h * h * 0.002)
                        v_size = tbr * 1000 / 8 * duration_est

                    total_estimated_size = v_size + (best_audio_size_rate * duration_est)

                    if total_estimated_size > 1024 * 1024 * 1024:
                        size_str = f"≈{total_estimated_size / (1024 ** 3):.1f} GB"
                    elif total_estimated_size > 1024 * 1024:
                        size_str = f"≈{total_estimated_size / (1024 ** 2):.0f} MB"
                    else:
                        size_str = f"≈{total_estimated_size / 1024:.0f} KB"

                    resolution_sizes[str(h)] = size_str

            if resolutions and str(resolutions[0]) in resolution_sizes:
                resolution_sizes['best'] = resolution_sizes[str(resolutions[0])]

            data = {
                'title': info.get('title', 'Unknown Title'),
                'channel': info.get('uploader') or info.get('channel', 'Unknown Creator'),
                'duration': duration,
                'duration_str': duration_str,
                'view_str': view_str,
                'view_count': views,
                'upload_date': upload_date_str,
                'thumbnail': thumb_url,
                'resolutions': resolutions,
                'resolution_sizes': resolution_sizes,
                'fps': max_fps,
                'has_av1': has_av1,
                'has_vp9': has_vp9,
                'has_hdr': has_hdr,
                'is_playlist': is_playlist,
                'playlist_count': playlist_count,
                'url': self.url
            }
            self.metadata_ready.emit(data)
        except Exception as e:
            logger.exception(f"Metadata extraction error: {e}")
            err_text = str(e)
            if "sign in" in err_text.lower() or "bot" in err_text.lower():
                err_text = "YouTube bot verification triggered: Enable browser cookies in Settings to bypass."
            elif "private video" in err_text.lower():
                err_text = "This video is private."
            elif "unavailable" in err_text.lower():
                err_text = "This video is unavailable."
            elif "members-only" in err_text.lower():
                err_text = "This video is members-only."
            self.metadata_error.emit(err_text)
