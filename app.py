import os
import shutil
import sys

# Restore original library environment variables for child processes (like system FFmpeg)
# to prevent loader conflicts caused by PyInstaller or AppImage LD_LIBRARY_PATH overrides.
if getattr(sys, 'frozen', False):
    for var in ['LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH']:
        orig_var = var + '_ORIG'
        if orig_var in os.environ:
            os.environ[var] = os.environ[orig_var]
        else:
            os.environ.pop(var, None)

import json
import subprocess
import threading
from datetime import datetime
import webview

from core.logger import logger
from core.constants import (
    HISTORY_LIMIT,
    HISTORY_DEBOUNCE_DELAY,
    WRITE_TEST_FILE,
    YT_DLP_ENGINE_PARENT_DIR,
    YT_DLP_ENGINE_DIR,
    YT_DLP_ENGINE_BACKUP_DIR
)

# Startup verification & fallback logic for user-installed override engine
if os.path.exists(YT_DLP_ENGINE_DIR) and os.path.exists(os.path.join(YT_DLP_ENGINE_DIR, "__init__.py")):
    sys.path.insert(0, YT_DLP_ENGINE_PARENT_DIR)
    try:
        import yt_dlp
        _ = yt_dlp.version.__version__
        logger.info(f"Loaded override yt-dlp engine from user folder (version: {yt_dlp.version.__version__})")
    except Exception as e:
        logger.error(f"Failed to load user-installed yt-dlp engine: {e}")
        if YT_DLP_ENGINE_PARENT_DIR in sys.path:
            sys.path.remove(YT_DLP_ENGINE_PARENT_DIR)
        for key in list(sys.modules.keys()):
            if key == 'yt_dlp' or key.startswith('yt_dlp.'):
                try:
                    del sys.modules[key]
                except KeyError:
                    pass
        
        if os.path.exists(YT_DLP_ENGINE_BACKUP_DIR) and os.path.exists(os.path.join(YT_DLP_ENGINE_BACKUP_DIR, "__init__.py")):
            logger.info("Restoring override engine from backup folder...")
            try:
                if os.path.exists(YT_DLP_ENGINE_DIR):
                    shutil.rmtree(YT_DLP_ENGINE_DIR)
                shutil.copytree(YT_DLP_ENGINE_BACKUP_DIR, YT_DLP_ENGINE_DIR)
                sys.path.insert(0, YT_DLP_ENGINE_PARENT_DIR)
                import yt_dlp
                _ = yt_dlp.version.__version__
                logger.info(f"Successfully rolled back and loaded backup engine (version: {yt_dlp.version.__version__})")
            except Exception as ex:
                logger.error(f"Rollback to backup engine failed: {ex}")
                if YT_DLP_ENGINE_PARENT_DIR in sys.path:
                    sys.path.remove(YT_DLP_ENGINE_PARENT_DIR)
                for key in list(sys.modules.keys()):
                    if key == 'yt_dlp' or key.startswith('yt_dlp.'):
                        try:
                            del sys.modules[key]
                        except KeyError:
                            pass
        else:
            logger.info("No valid backup engine found to restore. Falling back to bundled copy.")
else:
    # If the user engine directory is missing or is corrupted (missing __init__.py), trigger rollback immediately if backup is available
    if os.path.exists(YT_DLP_ENGINE_BACKUP_DIR) and os.path.exists(os.path.join(YT_DLP_ENGINE_BACKUP_DIR, "__init__.py")):
        if os.path.exists(YT_DLP_ENGINE_DIR):
            logger.warning("User engine directory is corrupted (missing __init__.py). Restoring active engine from backup folder...")
        else:
            logger.info("User engine directory is missing. Restoring active engine from backup folder...")
        try:
            if os.path.exists(YT_DLP_ENGINE_DIR):
                shutil.rmtree(YT_DLP_ENGINE_DIR)
            shutil.copytree(YT_DLP_ENGINE_BACKUP_DIR, YT_DLP_ENGINE_DIR)
            sys.path.insert(0, YT_DLP_ENGINE_PARENT_DIR)
            import yt_dlp
            _ = yt_dlp.version.__version__
            logger.info(f"Successfully loaded restored backup engine (version: {yt_dlp.version.__version__})")
        except Exception as ex:
            logger.error(f"Failed to restore backup engine: {ex}")
            if YT_DLP_ENGINE_PARENT_DIR in sys.path:
                sys.path.remove(YT_DLP_ENGINE_PARENT_DIR)
            for key in list(sys.modules.keys()):
                if key == 'yt_dlp' or key.startswith('yt_dlp.'):
                    try:
                        del sys.modules[key]
                    except KeyError:
                        pass
    else:
        if os.path.exists(YT_DLP_ENGINE_DIR):
            logger.warning("User engine directory is corrupted (missing __init__.py) and no valid backup engine is available. Falling back to bundled copy.")
        else:
            logger.info("No user engine directory or valid backup engine available. Falling back to bundled copy.")



from services.config_manager import load_config, save_config, load_last_folder, save_last_folder
from services.history_manager import load_history, save_history, get_file_size_str
from services.clipboard_manager import get_clipboard_text, read_clipboard, copy_to_clipboard
from services.dependency_manager import DependencyManager
from services.downloader import start_download, get_ffmpeg_path


def check_ffmpeg():
    ffmpeg_path = get_ffmpeg_path()
    try:
        subprocess.run([ffmpeg_path or "ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def platform_open(path):
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=True)
        else:
            subprocess.run(["xdg-open", path], check=True)
        return True
    except Exception as e:
        logger.error(f"Platform open error for {path}: {e}")
        return False


def get_folder_dialog_constant():
    try:
        return webview.FileDialog.FOLDER
    except AttributeError:
        return webview.FOLDER_DIALOG


class Api:
    def __init__(self):
        self.stop_event = None
        self.window = None
        self.js_lock = threading.Lock()
        self.deps = DependencyManager()
        self.history_cache = None
        self.history_lock = threading.Lock()
        self.save_timer = None
        logger.info("Bemudex Api initialized")

    def set_window(self, window):
        self.window = window

    def check_ffmpeg(self):
        return check_ffmpeg()

    def load_last_folder(self):
        return load_last_folder()

    def read_clipboard(self):
        return read_clipboard()

    def copy_to_clipboard(self, text):
        logger.info("copy_to_clipboard API called")
        return copy_to_clipboard(text)

    def browse_folder(self):
        if self.window:
            dialog_type = get_folder_dialog_constant()
            result = self.window.create_file_dialog(dialog_type)
            if result:
                folder = result[0]
                save_last_folder(folder)
                return folder
        return None

    def open_folder(self, path):
        if not path:
            self._log("⚠️ No valid path provided.")
            return False

        if os.path.isfile(path):
            folder = os.path.dirname(path)
        else:
            folder = path

        if not os.path.exists(folder):
            self._log("⚠️ No valid folder selected.")
            return False

        return platform_open(folder)

    def get_history(self):
        with self.history_lock:
            if self.history_cache is None:
                self.history_cache = load_history()
            return self.history_cache

    def save_history_debounced(self, history):
        with self.history_lock:
            self.history_cache = history
            if self.save_timer is not None:
                self.save_timer.cancel()

            def flush():
                with self.history_lock:
                    to_save = list(self.history_cache)
                save_history(to_save)
                logger.info("History flushed to disk.")

            self.save_timer = threading.Timer(HISTORY_DEBOUNCE_DELAY, flush)
            self.save_timer.start()

    def clear_history(self):
        with self.history_lock:
            self.history_cache = []
            if self.save_timer is not None:
                self.save_timer.cancel()
                self.save_timer = None
        save_history([])
        logger.info("History cleared and written to disk.")
        return True

    def remove_history_item(self, file_path):
        try:
            history = self.get_history()
            new_history = [item for item in history if item.get('filePath') != file_path]
            self.save_history_debounced(new_history)
            return True
        except Exception:
            return False

    def play_file(self, file_path):
        if not file_path or not os.path.exists(file_path):
            return False
        return platform_open(file_path)

    def get_dependency_status(self):
        logger.info("get_dependency_status API called")
        try:
            folder = self.load_last_folder()
            versions = self.deps.versions()
            detect_info = self.deps.detect()

            # Folder writable check
            folder_writable = False
            if folder and os.path.exists(folder):
                temp_file = os.path.join(folder, WRITE_TEST_FILE)
                try:
                    with open(temp_file, "w") as f:
                        f.write("test")
                    folder_writable = True
                except Exception as e:
                    logger.warning(f"Download folder {folder} is not writable: {e}")
                finally:
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except Exception:
                            pass

            return {
                "bemudex": versions["bemudex"],
                "ytdlp": {
                    "version": versions["ytdlp"]["version"],
                    "status": "unknown"
                },
                "ffmpeg": {
                    "installed": detect_info["installed"],
                    "version": detect_info["version"] or "",
                    "path": detect_info["path"] or ""
                },
                "folder_writable": folder_writable,
                "status": "ready" if (detect_info["installed"] and folder_writable) else "attention_required"
            }
        except Exception as e:
            logger.exception(f"Error getting dependency status: {e}")
            return {"status": "error", "error": str(e), "message": str(e)}

    def check_ytdlp_updates(self):
        logger.info("check_ytdlp_updates API called")
        try:
            return self.deps.check()
        except Exception as e:
            logger.exception(f"Failed to check yt-dlp updates: {e}")
            return {"status": "error", "error": str(e), "message": str(e)}

    def update_ytdlp(self):
        logger.info("update_ytdlp API called")
        try:
            return self.deps.update()
        except Exception as e:
            logger.exception(f"Failed to update yt-dlp: {e}")
            return {"status": "error", "error": str(e), "message": str(e)}

    def get_ytdlp_version(self):
        try:
            return self.deps.versions()["ytdlp"]["version"]
        except Exception:
            return "Unknown"

    def locate_ffmpeg(self):
        logger.info("locate_ffmpeg API called")
        if not self.window:
            logger.error("Pywebview window not available for locate_ffmpeg")
            return {"status": "error", "message": "Application window is not available."}
        try:
            # Open file dialog
            file_types = ('Executables (*.exe; ffmpeg)', 'All files (*.*)') if sys.platform == 'win32' else ('All files (*)',)
            result = self.window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types)
            if not result or len(result) == 0:
                logger.info("Locate FFmpeg file dialog cancelled by user")
                return {"status": "cancelled"}

            selected_path = result[0]
            logger.info(f"User selected FFmpeg path: {selected_path}")

            # Validate selected path
            ver = self.deps._probe_ffmpeg(selected_path)
            if ver:
                config = load_config()
                config["ffmpeg_path"] = selected_path
                save_config(config)
                self.deps.detect(force_recheck=True)
                logger.info(f"Custom FFmpeg configured successfully at {selected_path} (Version: {ver})")
                return {
                    "status": "success",
                    "path": selected_path,
                    "version": ver
                }
            else:
                logger.error(f"Selected file is not a valid FFmpeg executable: {selected_path}")
                return {
                    "status": "error",
                    "message": "Selected file is not a valid FFmpeg executable."
                }
        except Exception as e:
            logger.exception(f"Failed to locate FFmpeg: {e}")
            return {
                "status": "error",
                "error": f"Failed to locate FFmpeg: {str(e)}",
                "message": f"Failed to locate FFmpeg: {str(e)}"
            }

    def detect_ffmpeg_api(self):
        logger.info("detect_ffmpeg_api API called")
        try:
            detect_info = self.deps.detect()
            return {
                "installed": detect_info["installed"],
                "version": detect_info["version"] or "",
                "path": detect_info["path"] or ""
            }
        except Exception as e:
            logger.exception(f"Failed to detect FFmpeg: {e}")
            return {"status": "error", "installed": False, "version": "", "path": "", "error": str(e), "message": str(e)}

    def get_diagnostics(self, current_theme="dark"):
        logger.info("get_diagnostics API called")
        try:
            folder = self.load_last_folder()
            return self.deps.diagnostics(folder, current_theme)
        except Exception as e:
            logger.exception(f"Failed to generate diagnostics: {e}")
            return {"status": "error", "error": str(e), "message": str(e)}

    def reset_dependency_config(self):
        logger.info("reset_dependency_config API called")
        try:
            detect_info = self.deps.reset()
            folder = self.load_last_folder()

            # Recheck writable
            folder_writable = False
            if folder and os.path.exists(folder):
                temp_file = os.path.join(folder, WRITE_TEST_FILE)
                try:
                    with open(temp_file, "w") as f:
                        f.write("test")
                    folder_writable = True
                except Exception:
                    pass
                finally:
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except Exception:
                            pass

            versions = self.deps.versions()
            return {
                "bemudex": versions["bemudex"],
                "ytdlp": {
                    "version": versions["ytdlp"]["version"],
                    "status": "unknown"
                },
                "ffmpeg": {
                    "installed": detect_info["installed"],
                    "version": detect_info["version"] or "",
                    "path": detect_info["path"] or ""
                },
                "folder_writable": folder_writable,
                "status": "ready" if (detect_info["installed"] and folder_writable) else "attention_required"
            }
        except Exception as e:
            logger.exception(f"Failed to reset dependency config: {e}")
            return {"status": "error", "error": str(e), "message": str(e)}

    def start_download(self, url, folder, download_type, quality, options=None):
        if self.is_downloading():
            logger.warning("Download request rejected: another download is already in progress.")
            raise Exception("Another download is already in progress.")

        self.stop_event = threading.Event()
        logger.info(f"start_download called for URL: {url} (type: {download_type}, quality: {quality}, folder: {folder})")

        opt_dict = options or {}
        audio_format = opt_dict.get('audioFormat', 'mp3')
        custom_title = opt_dict.get('title')
        custom_artist = opt_dict.get('artist')
        embed_thumbnail = opt_dict.get('embedThumbnail', True)
        embed_tags = opt_dict.get('embedTags', True)
        embed_chapters = opt_dict.get('embedChapters', True)
        playlist_index = opt_dict.get('playlistIndex')

        # Decode custom cover art base64 string if present
        custom_cover = opt_dict.get('customCover')
        custom_thumbnail_path = None
        if custom_cover:
            try:
                if ',' in custom_cover:
                    _, base64_data = custom_cover.split(',', 1)
                else:
                    base64_data = custom_cover
                import base64
                image_data = base64.b64decode(base64_data)

                # Write to a temp file in destination folder
                from core.constants import CUSTOM_COVER_PREFIX
                temp_filename = f"{CUSTOM_COVER_PREFIX}{int(datetime.now().timestamp())}.jpg"
                custom_thumbnail_path = os.path.join(folder, temp_filename)
                with open(custom_thumbnail_path, 'wb') as img_f:
                    img_f.write(image_data)
            except Exception as e:
                logger.error(f"Failed to decode custom cover art: {e}")
                custom_thumbnail_path = None

        # Parse bandwidth limit (in MB/s)
        ratelimit_mb = opt_dict.get('ratelimit', 0)
        ratelimit_bytes = int(ratelimit_mb * 1024 * 1024) if ratelimit_mb > 0 else None

        def on_progress(data):
            if self.window:
                with self.js_lock:
                    try:
                        self.window.evaluate_js(f"window.onProgress({json.dumps(data)})")
                    except Exception as e:
                        logger.error(f"JS onProgress call failed: {e}")

        def on_playlist_metadata(items):
            if self.window:
                with self.js_lock:
                    try:
                        self.window.evaluate_js(f"window.onPlaylistMetadata({json.dumps(items)})")
                    except Exception as e:
                        logger.error(f"JS onPlaylistMetadata call failed: {e}")

        def on_done(files, total_count=1, was_cancelled=False):
            logger.info(f"Download finished. Files saved: {files}, total: {total_count}, cancelled: {was_cancelled}")
            # Write to history file on completion
            history = self.get_history()
            for f in files:
                title = os.path.basename(f)
                size_str = get_file_size_str(f)
                history.append({
                    'title': title,
                    'filePath': f,
                    'fileSize': size_str,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'format': download_type,
                    'url': url
                })
            # Truncate history to latest entries
            history = history[-HISTORY_LIMIT:]
            self.save_history_debounced(history)

            # Clean up temporary cover image
            if custom_thumbnail_path and os.path.exists(custom_thumbnail_path):
                try:
                    os.remove(custom_thumbnail_path)
                except Exception:
                    pass

            if self.window:
                with self.js_lock:
                    try:
                        self.window.evaluate_js(f"window.onDownloadFinished({json.dumps(files)}, {total_count}, {json.dumps(was_cancelled)})")
                    except Exception as e:
                        logger.error(f"JS onDownloadFinished call failed: {e}")
            self.stop_event = None

        try:
            start_download(
                url=url,
                folder=folder,
                download_type=download_type,
                quality=quality,
                on_progress=on_progress,
                on_log=self._log,
                on_done=on_done,
                on_playlist_metadata=on_playlist_metadata,
                stop_event=self.stop_event,
                audio_format=audio_format,
                title=custom_title,
                artist=custom_artist,
                embed_thumbnail=embed_thumbnail,
                embed_tags=embed_tags,
                embed_chapters=embed_chapters,
                custom_thumbnail=custom_thumbnail_path,
                ratelimit=ratelimit_bytes,
                playlist_index=playlist_index
            )
        except Exception as e:
            logger.exception(f"Download thread crashed: {e}")
            if self.window:
                with self.js_lock:
                    try:
                        self.window.evaluate_js("window.onDownloadFinished([], 0, false)")
                    except Exception:
                        pass
            self.stop_event = None

    def is_downloading(self):
        return self.stop_event is not None

    def check_overwrite(self, folder, title, download_type, audio_format='mp3'):
        logger.info(f"check_overwrite API called: folder={folder}, title={title}, type={download_type}, format={audio_format}")
        try:
            if not folder or not os.path.exists(folder):
                return {"exists": False}

            # Sanitise title
            sanitized = title
            for c in r'\/:*?"<>|':
                sanitized = sanitized.replace(c, '_')

            ext = 'mp4' if download_type == 'video' else audio_format
            expected_path = os.path.join(folder, f"{sanitized}.{ext}")

            exists = os.path.exists(expected_path)
            logger.info(f"Overwrite check for {expected_path}: exists={exists}")
            return {"exists": exists, "path": expected_path}
        except Exception as e:
            logger.error(f"Error checking overwrite: {e}")
            return {"exists": False}

    def get_clipboard_text(self):
        return get_clipboard_text()

    def fetch_metadata(self, url):
        def _format_duration(seconds):
            if not seconds:
                return '0:00'
            mins, secs = divmod(int(seconds), 60)
            hours, mins = divmod(mins, 60)
            if hours > 0:
                return f'{hours}:{mins:02d}:{secs:02d}'
            return f'{mins}:{secs:02d}'

        def _format_upload_date(date_str):
            if not date_str:
                return 'Unknown'
            try:
                from datetime import datetime as dt
                upload = dt.strptime(date_str, '%Y%m%d')
                now = dt.now()
                diff = now - upload
                days = diff.days
                if days == 0:
                    return 'Today'
                elif days == 1:
                    return 'Yesterday'
                elif days < 7:
                    return f'{days} days ago'
                elif days < 30:
                    weeks = days // 7
                    return f'{weeks} week{"s" if weeks > 1 else ""} ago'
                elif days < 365:
                    months = days // 30
                    return f'{months} month{"s" if months > 1 else ""} ago'
                else:
                    years = days // 365
                    return f'{years} year{"s" if years > 1 else ""} ago'
            except Exception:
                return date_str

        def _fetch():
            try:
                import yt_dlp
                ydl_opts = {
                    'skip_download': True,
                    'ignoreerrors': True,
                }
                ffmpeg_path = get_ffmpeg_path()
                if ffmpeg_path:
                    ydl_opts['ffmpeg_location'] = ffmpeg_path

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                if not info:
                    raise Exception('Could not extract info from URL')

                is_playlist = info.get('_type') == 'playlist'
                playlist_count = len(info.get('entries', [])) if is_playlist else 0

                # For playlists, use the first entry for detailed format info
                video_info = info
                if is_playlist:
                    entries = info.get('entries', [])
                    for entry in entries:
                        if entry:
                            video_info = entry
                            break

                formats = video_info.get('formats', [])
                resolutions = sorted(set(
                    f.get('height') for f in formats
                    if f.get('height') and f.get('vcodec') != 'none'
                ), reverse=True)

                has_hdr = any(
                    'hdr' in str(f.get('dynamic_range', '')).lower()
                    for f in formats
                )

                fps_values = [
                    f.get('fps') for f in formats
                    if f.get('fps') and f.get('vcodec') != 'none'
                ]
                max_fps = max(fps_values) if fps_values else 0

                # Codec detection
                has_av1 = any(
                    f.get('vcodec') and ('av01' in f.get('vcodec').lower() or 'av1' in f.get('vcodec').lower())
                    for f in formats
                )
                has_vp9 = any(
                    f.get('vcodec') and 'vp9' in f.get('vcodec').lower()
                    for f in formats
                )

                duration = video_info.get('duration') or 0
                duration_est = duration if duration > 0 else 300

                # Estimate file size per resolution
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

                # Detect chapters
                has_chapters = bool(video_info.get('chapters'))

                thumbnails = video_info.get('thumbnails', [])
                thumbnail = thumbnails[-1].get('url', '') if thumbnails else video_info.get('thumbnail', '')

                filesize_approx = video_info.get('filesize_approx') or video_info.get('filesize')

                data = {
                    'title': info.get('title', ''),
                    'channel': info.get('uploader') or info.get('channel', ''),
                    'duration': video_info.get('duration') or 0,
                    'duration_str': _format_duration(video_info.get('duration')),
                    'view_count': video_info.get('view_count'),
                    'upload_date': _format_upload_date(video_info.get('upload_date')),
                    'thumbnail': thumbnail,
                    'is_live': bool(video_info.get('is_live')),
                    'is_playlist': is_playlist,
                    'playlist_count': playlist_count,
                    'resolutions': resolutions,
                    'has_hdr': has_hdr,
                    'has_av1': has_av1,
                    'has_vp9': has_vp9,
                    'has_chapters': has_chapters,
                    'resolution_sizes': resolution_sizes,
                    'fps': int(max_fps) if max_fps else 0,
                    'filesize_approx': filesize_approx,
                }

                if self.window:
                    with self.js_lock:
                        try:
                            self.window.evaluate_js(f"window.onMetadata({json.dumps(data)})")
                        except Exception as e:
                            logger.error(f"JS onMetadata call failed: {e}")
            except Exception as e:
                if self.window:
                    with self.js_lock:
                        try:
                            self.window.evaluate_js(f"window.onMetadata({json.dumps({'error': str(e)})})")
                        except Exception:
                            pass

        thread = threading.Thread(target=_fetch, daemon=True)
        thread.start()

    def get_disk_usage(self, folder):
        try:
            usage = shutil.disk_usage(folder)
            total_gb = usage.total / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'free_str': f'{free_gb:.1f} GB',
                'total_str': f'{total_gb:.0f} GB' if total_gb >= 1 else f'{usage.total / (1024 ** 2):.1f} MB',
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "message": str(e)}

    def cancel_download(self):
        if self.stop_event:
            self._log("⚠️ Cancelling download... Please wait.")
            self.stop_event.set()

    def _log(self, message):
        if "Downloading:" in message:
            print(f"[Python Downloader Log] {message}")
        else:
            logger.info(f"[Downloader] {message}")

        if self.window:
            with self.js_lock:
                try:
                    self.window.evaluate_js(f"window.onLog({json.dumps(message)})")
                except Exception:
                    pass


if __name__ == '__main__':
    api = Api()

    # Auto-detect development mode
    IS_DEV = False
    if not getattr(sys, 'frozen', False):
        try:
            import urllib.request
            with urllib.request.urlopen("http://localhost:5173", timeout=0.5) as conn:
                pass
            IS_DEV = True
        except Exception:
            pass

    if IS_DEV:
        url = "http://localhost:5173"
    else:
        if getattr(sys, 'frozen', False):
            url = os.path.join(sys._MEIPASS, 'frontend', 'dist', 'index.html')
        else:
            url = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend', 'dist', 'index.html')
            if not os.path.exists(url):
                logger.warning(f"Production build not found at {url}.")

    # Set landscape desktop dimensions (950x640)
    window = webview.create_window(
        title="Bemudex",
        url=url,
        js_api=api,
        width=950,
        height=640,
        min_size=(800, 500),
        resizable=True
    )
    api.set_window(window)

    def on_closing():
        with api.history_lock:
            if api.save_timer is not None:
                api.save_timer.cancel()
                if api.history_cache is not None:
                    save_history(api.history_cache)
                    logger.info("History flushed on closing.")

        if api.is_downloading():
            res = window.create_confirmation_dialog(
                "Exit Bemudex?",
                "Downloads are currently in progress. Exit now and cancel all active downloads?"
            )
            return res
        return True

    window.events.closing += on_closing

    webview.start(debug=IS_DEV)