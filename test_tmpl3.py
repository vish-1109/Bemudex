from yt_dlp import YoutubeDL
ydl = YoutubeDL({'outtmpl': '%(playlist_index&{:02d} - |)s%(title)s.ext'})
print(ydl.prepare_filename({'title': 'test', 'playlist_index': 5}))

ydl2 = YoutubeDL({'outtmpl': '%(playlist_index&%02d - |)s%(title)s.ext'})
print(ydl2.prepare_filename({'title': 'test', 'playlist_index': 5}))
