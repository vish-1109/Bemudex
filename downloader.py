import os
import threading
import yt_dlp

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
                'outtmpl': os.path.join(folder, '%(playlist_index)02d - %(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': quality,
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
            
            # Cleanup NA prefix (single video case)
            for filename in os.listdir(folder):
                if filename.startswith('NA') and filename.endswith('.mp3'):
                    old_path = os.path.join(folder, filename)
                    new_filename = filename[2:]
                    # Also remove leading dash if present
                    if new_filename.startswith('- '):
                        new_filename = new_filename[2:]
                    new_path = os.path.join(folder, new_filename)
                    os.rename(old_path, new_path)
            
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