import os
import sys
import threading
import yt_dlp

def get_ffmpeg_path():
    # If we are on Windows, use the local/bundled ffmpeg.exe
    if sys.platform == "win32":
        if getattr(sys, 'frozen', False):
            # If running as a compiled .exe
            return os.path.join(sys._MEIPASS, 'ffmpeg.exe')
        else:
            # If running from source code
            return 'ffmpeg.exe'
            
    # If we are on Linux, return None so yt-dlp uses the system default
    return None

def start_download(url, folder, on_log, on_done, quality='320', stop_event=None):
    def hook(d):
        if stop_event and stop_event.is_set():
            raise Exception("Download cancelled by user")
        if d['status'] == 'downloading':
            filename = d.get('filename', '').split('/')[-1]
            percent = d.get('_percent_str', '').strip()
            display_name = filename.replace('NA', '')
            on_log(f"⬇️  {display_name} — {percent}")
        elif d['status'] == 'finished':
            on_log("🎵 Converting to MP3...")

    def run():
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(folder, '%(playlist_index&{:02d} - |)s%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': quality,
                }],
                'progress_hooks': [hook],
                'ignoreerrors': True,
            }
            
            # Only inject the ffmpeg path if we are on Windows
            ffmpeg_path = get_ffmpeg_path()
            if ffmpeg_path:
                ydl_opts['ffmpeg_location'] = ffmpeg_path
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            on_log("✅ All done! Check your folder.")
        except Exception as e:
            if "cancelled" in str(e).lower():
                on_log("⚠️ Download cancelled.")
            else:
                on_log(f"❌ Error: {e}")
        finally:
            on_done()

    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()
