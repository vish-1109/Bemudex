import os
import sys
import re
import threading
import json
import yt_dlp

from core.logger import logger
from core.constants import CONFIG_FILE
from services.config_manager import load_cookies_source, load_cookies_file


def clean_media_url(url: str) -> str:
    """Sanitizes media URLs by stripping tracking queries and auto-generated radio mixes."""
    if not url:
        return ""
    url = url.strip()
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return url
        
        qs = parse_qs(parsed.query, keep_blank_values=False)
        domain = parsed.netloc.lower()
        
        # General tracking parameters across platforms (YouTube, TikTok, Instagram, FB, etc.)
        tracking_params = {
            'si', 'feature', 'pp', 'utm_source', 'utm_medium', 
            'utm_campaign', 'utm_term', 'utm_content', '_r', '_t', 
            'is_from_webapp', 'sender_device', 'fbclid', 'gclid', 'igsh'
        }
        # On Twitter/X, 's' and 't' are tracking query params
        if 'twitter.com' in domain or 'x.com' in domain:
            tracking_params.update({'s', 't'})

        for tp in list(qs.keys()):
            if tp.lower() in tracking_params or tp.lower().startswith('utm_'):
                qs.pop(tp, None)
            
        # Strip YouTube radio/infinite mix playlists attached to single video watch URLs
        if 'youtube.com' in domain or 'youtu.be' in domain:
            if 'watch' in parsed.path:
                lists = qs.get('list', [])
                for l_val in lists:
                    if l_val.startswith(('RD', 'UL', 'LL', 'WL')):
                        qs.pop('list', None)
                        qs.pop('index', None)
                        qs.pop('start_radio', None)
                        break

        new_query = urlencode(qs, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    except Exception:
        return url


def get_base_ydl_opts():
    # Ensure local JS runtimes (~/.deno/bin, ~/.bun/bin) are in PATH
    for _d in [os.path.expanduser('~/.deno/bin'), os.path.expanduser('~/.bun/bin')]:
        if os.path.isdir(_d) and _d not in os.environ.get('PATH', ''):
            os.environ['PATH'] = _d + os.pathsep + os.environ.get('PATH', '')

    if sys.platform.startswith('linux') and 'DBUS_SESSION_BUS_ADDRESS' not in os.environ:
        bus_sock = f"/run/user/{os.getuid()}/bus"
        if os.path.exists(bus_sock):
            os.environ['DBUS_SESSION_BUS_ADDRESS'] = f"unix:path={bus_sock}"

    opts = {
        'js_runtimes': {'deno': {}, 'bun': {}, 'node': {}},
        'socket_timeout': 10,
        'check_formats': False,
        'get_comments': False,
        'lazy_playlist': True,
        'no_warnings': True,
        'concurrent_fragment_downloads': 8,
        'buffersize': 1048576,        # 1 MiB write buffer for smooth disk I/O
        'retries': 3,
        'fragment_retries': 3,
    }
    cookie_source = load_cookies_source()
    if cookie_source in ['chrome', 'brave', 'chromium', 'edge']:
        keyring = 'GNOMEKEYRING' if sys.platform.startswith('linux') else None
        opts['cookiesfrombrowser'] = (cookie_source, None, keyring, None)
    elif cookie_source == 'firefox':
        opts['cookiesfrombrowser'] = (cookie_source, None, None, None)
    elif cookie_source == 'file':
        cookie_file = load_cookies_file()
        if cookie_file and os.path.exists(cookie_file):
            opts['cookiefile'] = cookie_file
    return opts


def get_ffmpeg_path():
    # 1. Check custom path in config first
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                custom_path = config.get("ffmpeg_path", "")
                if custom_path and os.path.exists(custom_path):
                    return custom_path
        except Exception:
            pass

    # 2. Bundled check
    if getattr(sys, 'frozen', False):
        binary = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
        path = os.path.join(sys._MEIPASS, binary)
        if os.path.exists(path):
            return path
    if sys.platform == "win32":
        return 'ffmpeg.exe'
    return None


class CropSquareArtworkPP(yt_dlp.postprocessor.PostProcessor):
    """Crops downloaded audio thumbnail to a centered 1:1 square for native music player compatibility."""
    def run(self, info):
        thumbnails = info.get('thumbnails') or []
        for t in thumbnails:
            path = t.get('filepath')
            if path and os.path.exists(path):
                self._crop_image(path)
        main_path = info.get('_filename') or info.get('filepath')
        if main_path:
            base, _ = os.path.splitext(main_path)
            for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                candidate = base + ext
                if os.path.exists(candidate):
                    self._crop_image(candidate)
        return [], info

    def _crop_image(self, path):
        try:
            from PyQt6.QtGui import QImage
            img = QImage(path)
            if not img.isNull() and img.width() > 0 and img.height() > 0:
                w, h = img.width(), img.height()
                if w != h:
                    side = min(w, h)
                    x = (w - side) // 2
                    y = (h - side) // 2
                    cropped = img.copy(x, y, side, side)
                    cropped.save(path)
                    logger.debug(f"Cropped audio artwork to square: {path} ({side}x{side})")
        except Exception as e:
            logger.warning(f"Could not crop thumbnail {path}: {e}")


def start_download(url, folder, download_type, quality, on_progress, on_log, on_done,
                   on_playlist_metadata=None, stop_event=None,
                   audio_format='mp3', title=None, artist=None,
                   embed_thumbnail=True, embed_tags=True, embed_chapters=True,
                   custom_thumbnail=None, ratelimit=None, playlist_index=None,
                   embed_subtitles=False, is_playlist=None,
                   crop_artwork=True, sponsorblock=False,
                   compatibility_mode=False, subtitles_langs='en, en-US, en-GB',
                   auto_subtitles=True):
    url = clean_media_url(url)
    downloaded_files = []
    append_lock = threading.Lock()

    def hook(d):
        if stop_event and stop_event.is_set():
            raise Exception("Download cancelled by user")

        info = d.get('info_dict', {})
        title_text = info.get('title', 'Extracting video info...')
        video_id = info.get('id', 'temp_id')

        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            percent = (downloaded / total * 100) if total > 0 else 0
            
            # Format download speed
            speed_bytes = d.get('speed')
            if speed_bytes:
                if speed_bytes > 1024 * 1024:
                    speed_str = f"{speed_bytes / (1024 * 1024):.1f} MB/s"
                elif speed_bytes > 1024:
                    speed_str = f"{speed_bytes / 1024:.1f} KB/s"
                else:
                    speed_str = f"{speed_bytes} B/s"
            else:
                speed_str = "0 B/s"
                
            # Format ETA
            eta_sec = d.get('eta')
            if eta_sec is not None:
                try:
                    mins, secs = divmod(int(eta_sec), 60)
                    hours, mins = divmod(mins, 60)
                    eta_str = f"{hours}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins}:{secs:02d}"
                except Exception:
                    eta_str = "0:00"
            else:
                eta_str = "0:00"

            # Format size information (e.g. 1.2 MB / 132.4 MB)
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            if total > 0:
                size_info = f"{downloaded_mb:.1f} MB / {total_mb:.1f} MB"
            else:
                size_info = f"{downloaded_mb:.1f} MB"

            # Send structured progress update
            on_progress({
                'id': video_id,
                'title': title_text,
                'percent': percent,
                'speed': speed_str,
                'eta': eta_str,
                'sizeInfo': size_info,
                'status': 'downloading',
                'format': download_type,
                'quality': quality,
                'thumbnail': info.get('thumbnail', '')
            })

            # Send raw text log
            on_log(f"⬇️ Downloading: {title_text} — {percent:.1f}% ({speed_str}, ETA: {eta_str})")
            
        elif d['status'] == 'finished':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            total_mb = total / (1024 * 1024)
            size_info = f"{total_mb:.1f} MB" if total > 0 else "Processing"

            on_progress({
                'id': video_id,
                'title': title_text,
                'percent': 100,
                'speed': '0 KB/s',
                'eta': '0:00',
                'sizeInfo': size_info,
                'status': 'converting',
                'format': download_type,
                'quality': quality
            })
            on_log(f"🎵 Download finished for '{title_text}'. Processing/converting file...")

    def post_hook(d):
        if d['status'] == 'finished':
            info = d.get('info_dict', {})
            filepath = info.get('filepath') or info.get('_filename')
            video_id = info.get('id', 'temp_id')
            title_text = info.get('title', 'Completed download')

            if filepath:
                # Map file extensions based on download format to track final file path
                if download_type == 'audio':
                    base, _ = os.path.splitext(filepath)
                    ext = audio_format if audio_format != 'aac' else 'm4a'
                    filepath = base + '.' + ext
                elif download_type == 'video':
                    base, _ = os.path.splitext(filepath)
                    filepath = base + '.mp4'
                
                # Check for existence (might take a second to write, but we gather it)
                with append_lock:
                    if filepath not in downloaded_files:
                        downloaded_files.append(filepath)

                # Send finished status for the specific item
                on_progress({
                    'id': video_id,
                    'title': title_text,
                    'percent': 100,
                    'speed': '0 KB/s',
                    'eta': '0:00',
                    'sizeInfo': 'Finished',
                    'status': 'finished',
                    'format': download_type,
                    'quality': quality,
                    'filePath': filepath,
                    'thumbnail': info.get('thumbnail', '')
                })

    def run():
        nonlocal is_playlist
        playlist_title = ""
        target_folder = folder
        entries = []
        was_cancelled = False
        final_existing_files = []

        try:
            # Determine whether upfront playlist extraction is required
            should_extract_playlist = True
            if is_playlist is False or playlist_index is not None:
                should_extract_playlist = False
            elif is_playlist is True:
                should_extract_playlist = True
            else:
                # Auto-detect from URL: if no playlist indicator is present, skip upfront extraction
                has_playlist_param = any(param in url.lower() for param in [
                    'list=', '/playlist', '/sets/', '/album/', '/albums/', '/series/', '/show/'
                ])
                if not has_playlist_param:
                    should_extract_playlist = False

            if should_extract_playlist:
                try:
                    # 1. Extract playlist metadata upfront to populate queue
                    on_log("🔍 Extracting playlist metadata...")
                    extract_opts = {
                        'extract_flat': 'in_playlist',
                        'skip_download': True,
                        'ignoreerrors': True,
                        **get_base_ydl_opts()
                    }
                    ffmpeg_path = get_ffmpeg_path()
                    if ffmpeg_path:
                        extract_opts['ffmpeg_location'] = ffmpeg_path
                        
                    with yt_dlp.YoutubeDL(extract_opts) as ydl:
                        try:
                            info = ydl.extract_info(url, download=False)
                            if info:
                                if '_type' in info and info['_type'] == 'playlist':
                                    is_playlist = True
                                    raw_title = info.get('title') or title or 'Playlist'
                                    clean_title = re.sub(r'[\\/*?:"<>|]', '', str(raw_title))
                                    clean_title = re.sub(r'[\x00-\x1f\x7f]', '', clean_title).strip('. ')
                                    playlist_title = clean_title or "Playlist"

                                    if os.path.basename(os.path.normpath(folder)).lower() == playlist_title.lower():
                                        target_folder = folder
                                    else:
                                        target_folder = os.path.join(folder, playlist_title)

                                    os.makedirs(target_folder, exist_ok=True)
                                    on_log(f"📁 Saving playlist to: {os.path.basename(target_folder)}")
                                    entries = info.get('entries', [])
                                    items = []
                                    for i, entry in enumerate(entries):
                                        if entry:
                                            items.append({
                                                'id': entry.get('id', 'temp_id'),
                                                'title': entry.get('title', 'Extracting video info...'),
                                                'format': download_type,
                                                'quality': quality,
                                                'index': i + 1,
                                                'folder': target_folder
                                            })
                                    if items and on_playlist_metadata:
                                        try:
                                            on_playlist_metadata(items, target_folder)
                                        except TypeError:
                                            on_playlist_metadata(items)
                        except Exception as e:
                            logger.error(f"Error extracting playlist metadata: {e}")
                except Exception as e:
                    logger.error(f"Upfront playlist extraction failed: {e}")

            if stop_event and stop_event.is_set():
                raise Exception("Download cancelled by user")

            # 2. Proceed with actual download
            def download_entry(idx, entry):
                if stop_event and stop_event.is_set():
                    return
                video_id = entry.get('id', 'temp_id')
                entry_url = entry.get('webpage_url') or entry.get('url')
                if not entry_url or not str(entry_url).startswith(('http://', 'https://')):
                    entry_url = f"https://www.youtube.com/watch?v={video_id}"
                
                class EntryLogger:
                    def debug(self, msg):
                        print(f"[debug] {msg}")
                    def warning(self, msg):
                        print(f"[warning] {msg}")
                        logger.warning(f"[yt-dlp] [{video_id}] {msg}")
                    def error(self, msg):
                        print(f"[error] {msg}")
                        logger.error(f"[yt-dlp] [{video_id}] {msg}")
                        
                        err_text = "Download failed"
                        if "403" in msg or "forbidden" in msg.lower():
                            err_text = "HTTP Error 403: Forbidden"
                        elif "sign in" in msg.lower():
                            err_text = "Bot verification/Sign in required"
                        elif "private video" in msg.lower():
                            err_text = "Private video"
                        elif "removed" in msg.lower():
                            err_text = "Video removed"
                        elif "copyright" in msg.lower():
                            err_text = "Copyright blocked"
                        elif "geo-blocked" in msg.lower() or "region" in msg.lower() or "country" in msg.lower():
                            err_text = "Geo-blocked"
                        elif "members-only" in msg.lower():
                            err_text = "Members-only content"
                        
                        on_progress({
                            'id': video_id,
                            'title': entry.get('title', 'Error'),
                            'percent': 0,
                            'speed': 'Failed',
                            'eta': 'Error',
                            'sizeInfo': err_text,
                            'status': 'failed',
                            'format': download_type,
                            'quality': quality
                        })
                # Resume/retry support: skip tracks that were already downloaded in the destination folder
                prefix = f"{idx:02d} - "
                try:
                    existing_tracks = [
                        f for f in os.listdir(target_folder)
                        if f.startswith(prefix)
                        and not f.endswith(('.part', '.ytdl', '.temp'))
                        and os.path.isfile(os.path.join(target_folder, f))
                        and os.path.getsize(os.path.join(target_folder, f)) > 1024
                    ]
                    if existing_tracks:
                        full_existing_path = os.path.join(target_folder, existing_tracks[0])
                        on_log(f"⏩ Track {idx} already exists on disk: {existing_tracks[0]}")
                        with append_lock:
                            if full_existing_path not in downloaded_files:
                                downloaded_files.append(full_existing_path)
                        on_progress({
                            'id': video_id,
                            'title': entry.get('title', existing_tracks[0]),
                            'percent': 100,
                            'speed': '0 KB/s',
                            'eta': '0:00',
                            'sizeInfo': 'Finished',
                            'status': 'finished',
                            'format': download_type,
                            'quality': quality,
                            'filePath': full_existing_path,
                            'thumbnail': entry.get('thumbnail', '')
                        })
                        return
                except Exception as e:
                    logger.debug(f"Track resume check error: {e}")

                worker_opts = {
                    'outtmpl': os.path.join(target_folder, f"{idx:02d} - %(title).180B.%(ext)s"),
                    'progress_hooks': [hook],
                    'postprocessor_hooks': [post_hook],
                    'allow_playlist_files': False,
                    'noplaylist': True,
                    'check_formats': False,
                    'logger': EntryLogger(),
                    'retries': 3,
                    'fragment_retries': 3,
                    'concurrent_fragment_downloads': 8,
                    'overwrites': True,
                    **get_base_ydl_opts()
                }
                
                if ratelimit:
                    worker_opts['ratelimit'] = ratelimit

                if download_type == 'audio':
                    temp_dir = os.path.join(target_folder, '.bemudex_temp')
                    os.makedirs(temp_dir, exist_ok=True)
                    worker_opts['paths'] = {'temp': temp_dir}

                should_embed_thumbnail = embed_thumbnail and not (download_type == 'audio' and audio_format == 'wav')
                
                has_custom_thumb = False
                if custom_thumbnail and os.path.exists(custom_thumbnail) and should_embed_thumbnail:
                    try:
                        with yt_dlp.YoutubeDL(worker_opts) as ydl:
                            info = ydl.extract_info(entry_url, download=False)
                            filename = ydl.prepare_filename(info)
                            base, _ = os.path.splitext(filename)
                            target_thumb = base + ".jpg"
                            import shutil
                            shutil.copy2(custom_thumbnail, target_thumb)
                            has_custom_thumb = True
                    except Exception as e:
                        logger.error(f"Failed to prepare custom thumbnail: {e}")
                
                ffmpeg_path = get_ffmpeg_path()
                if ffmpeg_path:
                    worker_opts['ffmpeg_location'] = ffmpeg_path
                
                worker_opts['writethumbnail'] = should_embed_thumbnail if not has_custom_thumb else False
                
                if download_type == 'audio':
                    worker_opts['format'] = 'bestaudio[format_note*=original]/bestaudio/best'
                    postprocessors = [
                        {
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': audio_format,
                            'preferredquality': quality if audio_format in ['mp3', 'm4a', 'aac'] else None,
                        }
                    ]
                    if sponsorblock:
                        sb_categories = {'sponsor', 'selfpromo', 'interaction', 'intro', 'outro'}
                        postprocessors.append({
                            'key': 'SponsorBlock',
                            'categories': sb_categories,
                            'when': 'after_filter'
                        })
                        postprocessors.append({
                            'key': 'ModifyChapters',
                            'remove_sponsor_segments': sb_categories,
                            'force_keyframes': False
                        })
                    if embed_tags or embed_chapters:
                        postprocessors.append({
                            'key': 'FFmpegMetadata',
                            'add_metadata': embed_tags,
                            'add_chapters': embed_chapters
                        })
                    if should_embed_thumbnail:
                        postprocessors.append({'key': 'EmbedThumbnail'})
                        
                    worker_opts['postprocessors'] = postprocessors
                    
                    ffmpeg_args = []
                    if is_playlist:
                        album_val = playlist_title or title
                        if album_val:
                            # Use playlist title as the album metadata tag
                            ffmpeg_args.extend(['-metadata', f'album={album_val}'])
                    else:
                        if title:
                            # Use custom title as the track title metadata tag
                            ffmpeg_args.extend(['-metadata', f'title={title}'])
                    if artist:
                        ffmpeg_args.extend(['-metadata', f'artist={artist}'])
                    if ffmpeg_args:
                        worker_opts['postprocessor_args'] = {'ffmpeg': ffmpeg_args}
                else:
                    best_audio = '(bestaudio[format_note*=original]/bestaudio)'
                    if compatibility_mode:
                        compat_audio = '(bestaudio[acodec^=mp4a][format_note*=original]/bestaudio[acodec^=mp4a]/bestaudio[format_note*=original]/bestaudio)'
                        if quality != 'best':
                            worker_opts['format'] = (
                                f'bestvideo[vcodec^=avc1][height<={quality}]+{compat_audio}/'
                                f'bestvideo[vcodec^=avc1][height<={quality}]+{best_audio}/'
                                f'bestvideo[height<={quality}]+{best_audio}/best'
                            )
                        else:
                            worker_opts['format'] = (
                                f'bestvideo[vcodec^=avc1]+{compat_audio}/'
                                f'bestvideo[vcodec^=avc1]+{best_audio}/'
                                f'bestvideo+{best_audio}/best'
                            )
                    else:
                        if quality != 'best':
                            worker_opts['format'] = f'bestvideo[height<={quality}]+{best_audio}/best'
                        else:
                            worker_opts['format'] = f'bestvideo+{best_audio}/best'
                        
                    worker_opts['merge_output_format'] = 'mp4'
                    postprocessors = []
                    if embed_subtitles:
                        worker_opts['writesubtitles'] = True
                        worker_opts['writeautomaticsub'] = bool(auto_subtitles)
                        if isinstance(subtitles_langs, str):
                            parsed_langs = [l.strip() for l in re.split(r'[,;\s]+', subtitles_langs) if l.strip()]
                        elif isinstance(subtitles_langs, (list, tuple)):
                            parsed_langs = [str(l).strip() for l in subtitles_langs if str(l).strip()]
                        else:
                            parsed_langs = []
                        if not parsed_langs:
                            parsed_langs = ['en', 'en-US', 'en-GB']
                        worker_opts['subtitleslangs'] = parsed_langs
                        worker_opts['convertsubtitles'] = 'srt'
                        postprocessors.append({'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'})
                        postprocessors.append({'key': 'FFmpegEmbedSubtitle', 'already_have_subtitle': False})
                    if sponsorblock:
                        sb_categories = {'sponsor', 'selfpromo', 'interaction', 'intro', 'outro'}
                        postprocessors.append({
                            'key': 'SponsorBlock',
                            'categories': sb_categories,
                            'when': 'after_filter'
                        })
                        postprocessors.append({
                            'key': 'ModifyChapters',
                            'remove_sponsor_segments': sb_categories,
                            'force_keyframes': False
                        })
                    if embed_tags:
                        postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})
                    if embed_thumbnail:
                        postprocessors.append({'key': 'EmbedThumbnail'})
                    worker_opts['postprocessors'] = postprocessors
                
                try:
                    with yt_dlp.YoutubeDL(worker_opts) as ydl:
                        if download_type == 'audio' and should_embed_thumbnail and crop_artwork:
                            embed_idx = next((i for i, p in enumerate(ydl._pps.get('post_process', [])) if p.__class__.__name__ == 'EmbedThumbnailPP'), None)
                            if embed_idx is not None:
                                ydl._pps['post_process'].insert(embed_idx, CropSquareArtworkPP(ydl))
                            else:
                                ydl.add_post_processor(CropSquareArtworkPP(ydl))
                        ydl.download([entry_url])
                except Exception as e:
                    logger.error(f"Error downloading entry {video_id}: {e}")
                    on_progress({
                        'id': video_id,
                        'title': entry.get('title', 'Error'),
                        'percent': 0,
                        'speed': 'Failed',
                        'eta': 'Error',
                        'sizeInfo': str(e),
                        'status': 'failed',
                        'format': download_type,
                        'quality': quality
                    })

            if is_playlist:
                from concurrent.futures import ThreadPoolExecutor
                valid_entries = [(i + 1, entry) for i, entry in enumerate(entries) if entry]
                if valid_entries:
                    max_workers = 2
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = [executor.submit(download_entry, idx, entry) for idx, entry in valid_entries]
                        for future in futures:
                            future.result()
            else:
                single_video_id = 'temp_id'
                match = re.search(r'(?:v=|\/)([a-zA-Z0-9_-]{11})(?:&|#|\?|$)', url)
                if match:
                    single_video_id = match.group(1)

                class SingleLogger:
                    def debug(self, msg):
                        print(f"[debug] {msg}")
                    def warning(self, msg):
                        print(f"[warning] {msg}")
                        logger.warning(f"[yt-dlp] [{single_video_id}] {msg}")
                    def error(self, msg):
                        print(f"[error] {msg}")
                        logger.error(f"[yt-dlp] [{single_video_id}] {msg}")
                        
                        err_text = "Download failed"
                        if "403" in msg or "forbidden" in msg.lower():
                            err_text = "HTTP Error 403: Forbidden"
                        elif "sign in" in msg.lower():
                            err_text = "Bot verification/Sign in required"
                        elif "private video" in msg.lower():
                            err_text = "Private video"
                        elif "removed" in msg.lower():
                            err_text = "Video removed"
                        elif "copyright" in msg.lower():
                            err_text = "Copyright blocked"
                        elif "geo-blocked" in msg.lower() or "region" in msg.lower() or "country" in msg.lower():
                            err_text = "Geo-blocked"
                        elif "members-only" in msg.lower():
                            err_text = "Members-only content"
                        
                        on_progress({
                            'id': single_video_id,
                            'title': 'Error',
                            'percent': 0,
                            'speed': 'Failed',
                            'eta': 'Error',
                            'sizeInfo': err_text,
                            'status': 'failed',
                            'format': download_type,
                            'quality': quality
                        })

                try:
                    os.makedirs(folder, exist_ok=True)
                except Exception as ex:
                    logger.warning(f"Could not ensure destination folder {folder}: {ex}")

                if playlist_index is not None:
                    try:
                        outtmpl = os.path.join(folder, f"{int(playlist_index):02d} - %(title).180B.%(ext)s")
                    except (ValueError, TypeError):
                        outtmpl = os.path.join(folder, '%(title).180B.%(ext)s')
                else:
                    outtmpl = os.path.join(folder, '%(title).180B.%(ext)s')

                ydl_opts = {
                    'outtmpl': outtmpl,
                    'progress_hooks': [hook],
                    'postprocessor_hooks': [post_hook],
                    'allow_playlist_files': False,
                    'noplaylist': True,
                    'check_formats': False,
                    'logger': SingleLogger(),
                    'retries': 3,
                    'fragment_retries': 3,
                    'concurrent_fragment_downloads': 8,
                    'overwrites': True,
                    **get_base_ydl_opts()
                }
                
                if ratelimit:
                    ydl_opts['ratelimit'] = ratelimit

                if download_type == 'audio':
                    temp_dir = os.path.join(folder, '.bemudex_temp')
                    os.makedirs(temp_dir, exist_ok=True)
                    ydl_opts['paths'] = {'temp': temp_dir}

                should_embed_thumbnail = embed_thumbnail and not (download_type == 'audio' and audio_format == 'wav')
                
                has_custom_thumb = False
                if custom_thumbnail and os.path.exists(custom_thumbnail) and should_embed_thumbnail:
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(url, download=False)
                            filename = ydl.prepare_filename(info)
                            base, _ = os.path.splitext(filename)
                            target_thumb = base + ".jpg"
                            import shutil
                            shutil.copy2(custom_thumbnail, target_thumb)
                            has_custom_thumb = True
                    except Exception as e:
                        logger.error(f"Failed to prepare custom thumbnail: {e}")
                
                ffmpeg_path = get_ffmpeg_path()
                if ffmpeg_path:
                    ydl_opts['ffmpeg_location'] = ffmpeg_path
                
                ydl_opts['writethumbnail'] = should_embed_thumbnail if not has_custom_thumb else False
                
                if download_type == 'audio':
                    ydl_opts['format'] = 'bestaudio[format_note*=original]/bestaudio/best'
                    postprocessors = [
                        {
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': audio_format,
                            'preferredquality': quality if audio_format in ['mp3', 'm4a', 'aac'] else None,
                        }
                    ]
                    if sponsorblock:
                        sb_categories = {'sponsor', 'selfpromo', 'interaction', 'intro', 'outro'}
                        postprocessors.append({
                            'key': 'SponsorBlock',
                            'categories': sb_categories,
                            'when': 'after_filter'
                        })
                        postprocessors.append({
                            'key': 'ModifyChapters',
                            'remove_sponsor_segments': sb_categories,
                            'force_keyframes': False
                        })
                    if embed_tags or embed_chapters:
                        postprocessors.append({
                            'key': 'FFmpegMetadata',
                            'add_metadata': embed_tags,
                            'add_chapters': embed_chapters
                        })
                    if should_embed_thumbnail:
                        postprocessors.append({'key': 'EmbedThumbnail'})
                        
                    ydl_opts['postprocessors'] = postprocessors
                    
                    if title:
                        ydl_opts['postprocessor_args'] = {'ffmpeg': ['-metadata', f'title={title}']}
                    if artist:
                        if 'postprocessor_args' in ydl_opts:
                            ydl_opts['postprocessor_args']['ffmpeg'].extend(['-metadata', f'artist={artist}'])
                        else:
                            ydl_opts['postprocessor_args'] = {'ffmpeg': ['-metadata', f'artist={artist}']}
                else:
                    best_audio = '(bestaudio[format_note*=original]/bestaudio)'
                    if compatibility_mode:
                        compat_audio = '(bestaudio[acodec^=mp4a][format_note*=original]/bestaudio[acodec^=mp4a]/bestaudio[format_note*=original]/bestaudio)'
                        if quality != 'best':
                            ydl_opts['format'] = (
                                f'bestvideo[vcodec^=avc1][height<={quality}]+{compat_audio}/'
                                f'bestvideo[vcodec^=avc1][height<={quality}]+{best_audio}/'
                                f'bestvideo[height<={quality}]+{best_audio}/best'
                            )
                        else:
                            ydl_opts['format'] = (
                                f'bestvideo[vcodec^=avc1]+{compat_audio}/'
                                f'bestvideo[vcodec^=avc1]+{best_audio}/'
                                f'bestvideo+{best_audio}/best'
                            )
                    else:
                        if quality != 'best':
                            ydl_opts['format'] = f'bestvideo[height<={quality}]+{best_audio}/best'
                        else:
                            ydl_opts['format'] = f'bestvideo+{best_audio}/best'
                        
                    ydl_opts['merge_output_format'] = 'mp4'
                    postprocessors = []
                    if embed_subtitles:
                        ydl_opts['writesubtitles'] = True
                        ydl_opts['writeautomaticsub'] = bool(auto_subtitles)
                        if isinstance(subtitles_langs, str):
                            parsed_langs = [l.strip() for l in re.split(r'[,;\s]+', subtitles_langs) if l.strip()]
                        elif isinstance(subtitles_langs, (list, tuple)):
                            parsed_langs = [str(l).strip() for l in subtitles_langs if str(l).strip()]
                        else:
                            parsed_langs = []
                        if not parsed_langs:
                            parsed_langs = ['en', 'en-US', 'en-GB']
                        ydl_opts['subtitleslangs'] = parsed_langs
                        ydl_opts['convertsubtitles'] = 'srt'
                        postprocessors.append({'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'})
                        postprocessors.append({'key': 'FFmpegEmbedSubtitle', 'already_have_subtitle': False})
                    if sponsorblock:
                        sb_categories = {'sponsor', 'selfpromo', 'interaction', 'intro', 'outro'}
                        postprocessors.append({
                            'key': 'SponsorBlock',
                            'categories': sb_categories,
                            'when': 'after_filter'
                        })
                        postprocessors.append({
                            'key': 'ModifyChapters',
                            'remove_sponsor_segments': sb_categories,
                            'force_keyframes': False
                        })
                    if embed_tags:
                        postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})
                    if embed_thumbnail:
                        postprocessors.append({'key': 'EmbedThumbnail'})
                    ydl_opts['postprocessors'] = postprocessors
                
                try:
                    on_log("⚡ Connecting to stream and starting download...")
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        if download_type == 'audio' and should_embed_thumbnail and crop_artwork:
                            embed_idx = next((i for i, p in enumerate(ydl._pps.get('post_process', [])) if p.__class__.__name__ == 'EmbedThumbnailPP'), None)
                            if embed_idx is not None:
                                ydl._pps['post_process'].insert(embed_idx, CropSquareArtworkPP(ydl))
                            else:
                                ydl.add_post_processor(CropSquareArtworkPP(ydl))
                        ydl.download([url])
                except Exception as e:
                    on_progress({
                        'id': single_video_id,
                        'title': 'Error',
                        'percent': 0,
                        'speed': 'Failed',
                        'eta': 'Error',
                        'sizeInfo': str(e),
                        'status': 'failed',
                        'format': download_type,
                        'quality': quality
                    })
                    raise e

            if stop_event and stop_event.is_set():
                raise Exception("Download cancelled by user")
            
            with append_lock:
                final_existing_files = [f for f in downloaded_files if os.path.exists(f) and os.path.getsize(f) > 0]
            
            if not final_existing_files:
                raise Exception("No media files were generated. Download failed.")

            on_log("✅ All downloads completed successfully!")
        except Exception as e:
            was_cancelled = "cancelled" in str(e).lower()
            if stop_event and stop_event.is_set():
                was_cancelled = True
                
            if was_cancelled:
                on_log("⚠️ Download cancelled by user.")
            else:
                on_log(f"❌ Error: {e}")
                logger.error(f"Download worker error: {e}", exc_info=True)
        finally:
            try:
                import time
                current_time = time.time()
                cleanup_dirs = [folder]
                if is_playlist and target_folder != folder and os.path.exists(target_folder):
                    cleanup_dirs.append(target_folder)
                for d in cleanup_dirs:
                    if not os.path.exists(d):
                        continue
                    for item in os.listdir(d):
                        if item.startswith('.') and ('_custom_cover_' in item or 'write_test' in item or item == '.bemudex_temp'):
                            try:
                                item_path = os.path.join(d, item)
                                if os.path.isdir(item_path):
                                    import shutil
                                    shutil.rmtree(item_path, ignore_errors=True)
                                else:
                                    os.remove(item_path)
                            except Exception:
                                pass
                        if item.endswith(('.webp', '.jpg', '.jpeg', '.png', '.part', '.ytdl', '.vtt', '.srt')):
                            full_path = os.path.join(d, item)
                            if os.path.isfile(full_path) and (current_time - os.path.getmtime(full_path) < 120):
                                try:
                                    os.remove(full_path)
                                    logger.info(f"Cleaned up temporary file: {full_path}")
                                except Exception:
                                    pass
                # Clean up empty playlist directory if aborted before any tracks succeeded
                if is_playlist and target_folder != folder and os.path.exists(target_folder):
                    remaining = [f for f in os.listdir(target_folder) if not f.startswith('.')]
                    if not remaining:
                        try:
                            import shutil
                            shutil.rmtree(target_folder, ignore_errors=True)
                            logger.info(f"Removed empty playlist folder: {target_folder}")
                        except Exception:
                            pass
            except Exception as ex:
                logger.error(f"Failed to cleanup temp files: {ex}")
                
            if was_cancelled or not final_existing_files:
                on_done([], len(entries) if is_playlist else 1, was_cancelled)
            else:
                on_done(final_existing_files, len(entries) if is_playlist else 1, False)

    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()
