# Melodex

A clean, simple desktop app to download YouTube videos, playlists and YouTube Music playlists as MP3s in the highest quality available.

## Features

- Download single YouTube videos as MP3
- Download entire YouTube playlists as MP3
- Download YouTube Music playlists as MP3
- Highest quality audio
- Clean dark UI
- Live activity log

## Requirements

- Python 3
- FFmpeg

## Installation

**1. Clone the repository**
```bash
git clone https://github.com/vish-1109/Melodex.git
cd Melodex
```

**2. Install FFmpeg**
```bash
# Fedora
sudo dnf install ffmpeg -y

# Debian/Ubuntu
sudo apt install ffmpeg -y
```

**3. Install Python dependencies**
```bash
pip3 install -r requirements.txt --user
```

**4. Run the app**
```bash
python3 app.py
```

## Usage

1. Paste a YouTube video, playlist, or YouTube Music playlist URL into the URL field
2. Select a download folder
3. Hit **Download**

## License

MIT License — free to use, modify and distribute.
