import os
import sys
import threading
import yt_dlp

def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        if sys.platform.startswith('win'):
            ffmpeg_exe = os.path.join(base_path, 'ffmpeg.exe')
            return ffmpeg_exe if os.path.exists(ffmpeg_exe) else 'ffmpeg'
    return 'ffmpeg'

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
                'ffmpeg_location': get_ffmpeg_path(),
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android_vr'],
                    }
                },
            }
            
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