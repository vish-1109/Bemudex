import os
import threading
import yt_dlp

def start_download(url, folder, on_log, on_done):
    def hook(d):
        if d['status'] == 'downloading':
            filename = d.get('filename', '').split('/')[-1]
            percent = d.get('_percent_str', '').strip()
            on_log(f"⬇️  {filename} — {percent}")
        elif d['status'] == 'finished':
            on_log("🎵 Converting to MP3...")

    def run():
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(folder, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'progress_hooks': [hook],
            'ignoreerrors': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_vr'],
                }
            },
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        on_log("✅ All done! Check your folder.")
        on_done()

    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()