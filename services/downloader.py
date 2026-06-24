import os
import sys
import threading
import json
import yt_dlp

from core.logger import logger
from core.constants import CONFIG_FILE

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

def start_download(url, folder, download_type, quality, on_progress, on_log, on_done,
                   on_playlist_metadata=None, stop_event=None,
                   audio_format='mp3', title=None, artist=None,
                   embed_thumbnail=True, embed_tags=True, embed_chapters=True,
                   custom_thumbnail=None, ratelimit=None, playlist_index=None):
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
                mins, secs = divmod(eta_sec, 60)
                hours, mins = divmod(mins, 60)
                eta_str = f"{hours}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins}:{secs:02d}"
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
        is_playlist = False
        entries = []
        was_cancelled = False
        final_existing_files = []
        try:
            # 1. Extract playlist/video metadata upfront to populate queue
            on_log("🔍 Extracting playlist/video metadata...")
            extract_opts = {
                'extract_flat': 'in_playlist',
                'skip_download': True,
                'ignoreerrors': True,
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
                            entries = info.get('entries', [])
                            items = []
                            for i, entry in enumerate(entries):
                                if entry:
                                    items.append({
                                        'id': entry.get('id', 'temp_id'),
                                        'title': entry.get('title', 'Extracting video info...'),
                                        'format': download_type,
                                        'quality': quality,
                                        'index': i + 1
                                    })
                            if items and on_playlist_metadata:
                                on_playlist_metadata(items)
                        else:
                            if on_playlist_metadata:
                                on_playlist_metadata([{
                                    'id': info.get('id', 'temp_id'),
                                    'title': info.get('title', 'Extracting video info...'),
                                    'format': download_type,
                                    'quality': quality
                                }])
                except Exception as e:
                    logger.error(f"Error extracting playlist metadata: {e}")

            if stop_event and stop_event.is_set():
                raise Exception("Download cancelled by user")

            # 2. Proceed with actual download
            def download_entry(idx, entry):
                if stop_event and stop_event.is_set():
                    return
                video_id = entry.get('id', 'temp_id')
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

                worker_opts = {
                    'outtmpl': os.path.join(folder, f"{idx:02d} - %(title)s.%(ext)s"),
                    'progress_hooks': [hook],
                    'postprocessor_hooks': [post_hook],
                    'ignoreerrors': True,
                    'allow_playlist_files': False,
                    'logger': EntryLogger(),
                    'retries': 3,
                    'fragment_retries': 3,
                }
                
                if ratelimit:
                    worker_opts['ratelimit'] = ratelimit

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
                    worker_opts['format'] = 'bestaudio/best'
                    postprocessors = [
                        {
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': audio_format,
                            'preferredquality': quality if audio_format in ['mp3', 'm4a', 'aac'] else None,
                        }
                    ]
                    if should_embed_thumbnail:
                        postprocessors.append({'key': 'EmbedThumbnail'})
                    if embed_tags or embed_chapters:
                        postprocessors.append({
                            'key': 'FFmpegMetadata',
                            'add_metadata': embed_tags,
                            'add_chapters': embed_chapters
                        })
                        
                    worker_opts['postprocessors'] = postprocessors
                    
                    ffmpeg_args = []
                    if is_playlist:
                        if title:
                            # Use playlist title as the album metadata tag
                            ffmpeg_args.extend(['-metadata', f'album={title}'])
                    else:
                        if title:
                            # Use custom title as the track title metadata tag
                            ffmpeg_args.extend(['-metadata', f'title={title}'])
                    if artist:
                        ffmpeg_args.extend(['-metadata', f'artist={artist}'])
                    if ffmpeg_args:
                        worker_opts['postprocessor_args'] = {'ffmpeg': ffmpeg_args}
                else:
                    if quality != 'best':
                        worker_opts['format'] = f'bestvideo[height<={quality}]+bestaudio/best'
                    else:
                        worker_opts['format'] = 'bestvideo+bestaudio/best'
                        
                    worker_opts['merge_output_format'] = 'mp4'
                    postprocessors = []
                    if embed_thumbnail:
                        postprocessors.append({'key': 'EmbedThumbnail'})
                    if embed_tags:
                        postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})
                    worker_opts['postprocessors'] = postprocessors
                
                try:
                    with yt_dlp.YoutubeDL(worker_opts) as ydl:
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
                import re
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

                if playlist_index is not None:
                    try:
                        outtmpl = os.path.join(folder, f"{int(playlist_index):02d} - %(title)s.%(ext)s")
                    except (ValueError, TypeError):
                        outtmpl = os.path.join(folder, '%(title)s.%(ext)s')
                else:
                    outtmpl = os.path.join(folder, '%(title)s.%(ext)s')

                ydl_opts = {
                    'outtmpl': outtmpl,
                    'progress_hooks': [hook],
                    'postprocessor_hooks': [post_hook],
                    'ignoreerrors': True,
                    'allow_playlist_files': False,
                    'logger': SingleLogger(),
                    'retries': 3,
                    'fragment_retries': 3,
                }
                
                if ratelimit:
                    ydl_opts['ratelimit'] = ratelimit

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
                    ydl_opts['format'] = 'bestaudio/best'
                    postprocessors = [
                        {
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': audio_format,
                            'preferredquality': quality if audio_format in ['mp3', 'm4a', 'aac'] else None,
                        }
                    ]
                    if should_embed_thumbnail:
                        postprocessors.append({'key': 'EmbedThumbnail'})
                    if embed_tags or embed_chapters:
                        postprocessors.append({
                            'key': 'FFmpegMetadata',
                            'add_metadata': embed_tags,
                            'add_chapters': embed_chapters
                        })
                        
                    ydl_opts['postprocessors'] = postprocessors
                    
                    if title:
                        ydl_opts['postprocessor_args'] = {'ffmpeg': ['-metadata', f'title={title}']}
                    if artist:
                        if 'postprocessor_args' in ydl_opts:
                            ydl_opts['postprocessor_args']['ffmpeg'].extend(['-metadata', f'artist={artist}'])
                        else:
                            ydl_opts['postprocessor_args'] = {'ffmpeg': ['-metadata', f'artist={artist}']}
                else:
                    if quality != 'best':
                        ydl_opts['format'] = f'bestvideo[height<={quality}]+bestaudio/best'
                    else:
                        ydl_opts['format'] = 'bestvideo+bestaudio/best'
                        
                    ydl_opts['merge_output_format'] = 'mp4'
                    postprocessors = []
                    if embed_thumbnail:
                        postprocessors.append({'key': 'EmbedThumbnail'})
                    if embed_tags:
                        postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})
                    ydl_opts['postprocessors'] = postprocessors
                
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
                final_existing_files = [f for f in downloaded_files if os.path.exists(f)]
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
                for item in os.listdir(folder):
                    if item.startswith('.') and ('_custom_cover_' in item or 'write_test' in item):
                        try:
                            os.remove(os.path.join(folder, item))
                        except Exception:
                            pass
                    if item.endswith(('.webp', '.jpg', '.jpeg', '.png', '.part', '.ytdl')):
                        full_path = os.path.join(folder, item)
                        if os.path.isfile(full_path) and (current_time - os.path.getmtime(full_path) < 120):
                            try:
                                os.remove(full_path)
                                logger.info(f"Cleaned up temporary file: {full_path}")
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
