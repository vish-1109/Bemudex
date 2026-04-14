from yt_dlp import YoutubeDL
ydl = YoutubeDL({'outtmpl': '%(playlist_index&{} - |)s%(title)s.ext'}) 
print(ydl.prepare_filename({'title': 'test', 'playlist_index': None}))
print(ydl.prepare_filename({'title': 'test', 'playlist_index': 5}))

# Testing nested:
ydl2 = YoutubeDL({'outtmpl': '%(playlist_index&%(playlist_index)02d - |)s%(title)s.ext'}) 
print(ydl2.prepare_filename({'title': 'test', 'playlist_index': 5}))

# Testing the format trick string:
ydl3 = YoutubeDL({'outtmpl': '%(playlist_index)02d - %(title)s.ext'})
print(ydl3.prepare_filename({'title': 'test', 'playlist_index': 5}))

ydl4 = YoutubeDL({'outtmpl': '%(playlist_index&%02d - |)s%(title)s.ext'})
print(ydl4.prepare_filename({'title': 'test', 'playlist_index': 5}))

