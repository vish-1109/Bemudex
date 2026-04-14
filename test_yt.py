import yt_dlp
import os
def test_tmpl(tmpl, url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': tmpl,
        'simulate': True,
        'forceprint': {'video': ['filepath']}
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

print("--- SINGLE VIDEO ---")
test_tmpl('%(playlist_index&%02d - |)s%(title)s.%(ext)s', 'https://www.youtube.com/watch?v=BaW_jenozKc')
print("--- PLAYLIST ---")
test_tmpl('%(playlist_index&%02d - |)s%(title)s.%(ext)s', 'https://www.youtube.com/playlist?list=PL4lCbG00A2D_eL2L7L81i-Z718_WpB9_K')
