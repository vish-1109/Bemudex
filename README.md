<div align="center">

# 🎧 Bemudex

![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-blue)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-GPL--3.0-green.svg)
![Version](https://img.shields.io/badge/version-v2.0.1-orange.svg)

**A modern desktop media downloader powered by yt-dlp and FFmpeg, featuring audio/video conversions, metadata tagging, and a self-updating engine.**

[⬇️ Download Latest Release](https://github.com/vish-1109/Bemudex/releases)

</div>

---

## ✨ Features

| Feature | Description |
|:---|:---|
| **🎬 Multi-Format Support** | Download high-quality videos as **MP4** or convert audio to **MP3, M4A, FLAC, or WAV**. |
| **⚡ Parallel Download Queue** | Download playlist items concurrently using a multi-threaded queue (up to 2 active downloads). |
| **🔄 Self-Updating Engine** | Built-in updater automatically pulls the latest `yt-dlp` from PyPI with verification and rollback to prevent app breakage when streaming sites update. |
| **🏷️ Automatic Tagging** | Embeds title, artist metadata, chapter markers, and high-quality cover art/thumbnails directly into your media files. |
| **📋 Smart Clipboard Monitor** | Auto-detects media links on your clipboard and prompts you to download with a single click. |
| **🎨 Glassmorphic Interface** | Modern, responsive dark-themed translucent desktop user interface. |
| **💾 Disk Diagnostics** | Real-time disk space checks of download directories before starting a job. |

---

## 📦 Download & Install

### 🐧 Linux (Recommended Installers)

#### Debian / Ubuntu / Linux Mint / Pop!_OS (`.deb`)
Download `bemudex_2.0.1_amd64.deb` from the [Releases](https://github.com/vish-1109/Bemudex/releases) page and install it:
```bash
sudo dpkg -i bemudex_2.0.1_amd64.deb
sudo apt-get install -f  # Installs any missing dependencies
```
*(Or double-click the `.deb` file to install it directly using your system software center.)*

#### Universal Linux (`.AppImage`)
Download `Bemudex-x86_64.AppImage` from the [Releases](https://github.com/vish-1109/Bemudex/releases) page and run:
```bash
chmod +x Bemudex-x86_64.AppImage
./Bemudex-x86_64.AppImage
```

---

## 🛠️ Manual Installation (Build from Source)

If you prefer to run the application directly via Python:

### Requirements
*   **Python 3.8+**
*   **Node.js & npm** (for compiling the frontend)
*   **FFmpeg** (Required for media conversions and tagging)

### Build Instructions

**1. Clone the repository**
```bash
git clone https://github.com/vish-1109/Bemudex.git
cd Bemudex
```

**2. Install FFmpeg**
*   **Debian/Ubuntu:** `sudo apt install ffmpeg`
*   **Fedora:** `sudo dnf install ffmpeg`
*   **Arch Linux:** `sudo pacman -S ffmpeg`

**3. Build the frontend**
```bash
cd frontend
npm install
npm run build
cd ..
```

**4. Setup Python environment & run**
```bash
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows
pip install -r requirements.txt
python app.py
```

---

## 📄 License

This project is licensed under the **GNU General Public License v3 (GPL-3.0)** — see the [LICENSE](LICENSE) file for details.
