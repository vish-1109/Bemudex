# Bemudex

A clean, simple desktop app to download YouTube videos, playlists and YouTube Music playlists as MP3s in the highest quality available.

## Features

- Download single YouTube videos as MP3
- Download entire YouTube playlists as MP3 (numbered in playlist order)
- Download YouTube Music playlists as MP3
- Select MP3 quality: 128, 192, or 320 kbps
- Cancel downloads in progress
- Open download folder with one click
- Highest quality audio
- Clean dark UI
- Live activity log

## Requirements

- Python 3.7+
- FFmpeg

## Installation

**1. Clone the repository**
git clone https://github.com/vish-1109/Bemudex.git
cd Bemudex

**2. Install FFmpeg**
# Fedora
sudo dnf install ffmpeg -y

# Debian/Ubuntu
sudo apt install ffmpeg -y

# Arch
sudo pacman -S ffmpeg

# macOS
brew install ffmpeg

# Windows
Download from ffmpeg.org and add to PATH

**3. Install Python dependencies**
pip install -r requirements.txt

**4. Run the app**
python app.py

## Usage

1. Paste a YouTube video, playlist, or YouTube Music playlist URL into the URL field
2. Select a download folder
3. Choose your preferred MP3 quality (128/192/320 kbps)
4. Click **Download**

## Notes

1. Playlist downloads are automatically numbered (01, 02, 03...)
2. FFmpeg is required for MP3 conversion
3. Downloaded files save with original video titles

## License

MIT License — free to use, modify and distribute.
