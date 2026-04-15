<div align="center">

# 🎧 Bemudex

![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-blue)
![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**A clean, simple desktop application to download YouTube videos, playlists, and YouTube Music playlists as MP3s in the highest quality available.**

[⬇️ Download Latest Release](https://github.com/vish-1109/Bemudex/releases)

</div>

---

## ✨ Features

| Feature | Description |
|:---|:---|
| **Versatile Downloads** | Download single videos, entire YouTube playlists, or YouTube Music playlists. |
| **Smart Ordering** | Playlist downloads are automatically numbered in order (01, 02, 03...). |
| **Customizable Quality** | Select your preferred MP3 bitrate (128, 192, or 320 kbps). |
| **Modern UI** | Clean, dark user interface with a live activity log to track progress. |
| **User Control** | Cancel downloads in progress and open your download folder with a single click. |

---

## 📦 Download & Install

### 💻 Windows (10 / 11)

| Step | Action |
|:---:|:---|
| **1** | Download `Bemudex-Setup.exe` from the [Releases](https://github.com/vish-1109/Bemudex/releases) page. |
| **2** | Double-click the installer. |
| **3** | Follow the setup wizard. |
| **4** | Launch from the Start Menu or Desktop shortcut. |

> ✅ **No Python or FFmpeg required** – everything is bundled.  
> *The installer automatically installs the Visual C++ Runtime if missing.*

---

### 🐧 Linux Package Installers (Recommended)

Download the latest `.deb` or `.rpm` package from the [Releases](https://github.com/vish-1109/Bemudex/releases) page.

**Debian / Ubuntu / Linux Mint (.deb)**
```bash
sudo apt install ./bemudex_*.deb
```

**Fedora / RHEL / openSUSE (.rpm)**
```bash
sudo dnf install ./bemudex-*.rpm
```
(You can also simply double-click the downloaded package to install it via your system's software center, then find Bemudex in your app menu.)


**🛠️ Manual Installation (Build from Source)**
If you prefer to run the application directly via Python, follow these steps:

Requirements:
Python 3.7+
FFmpeg (Required for MP3 conversion)

**1. Clone the repository**
```bash
git clone [https://github.com/vish-1109/Bemudex.git](https://github.com/vish-1109/Bemudex.git)
cd Bemudex
```

**2. Install FFmpeg**
*Debian / Ubuntu*
```bash
sudo apt install ffmpeg -y
```

*Fedora*
```bash
sudo dnf install ffmpeg -y
```

*Arch Linux*
```bash
sudo pacman -S ffmpeg
```

**3. Install Python dependencies**
```bash
pip install -r requirements.txt
```

**4. Run the app**
```bash
python app.py
```

## 💻 Usage

1. **Paste** a YouTube video, playlist, or YouTube Music playlist URL into the URL field.
2. **Select** your destination download folder.
3. **Choose** your preferred MP3 quality (128 / 192 / 320 kbps).
4. **Click Download** and watch the live activity log!

## 📌 Notes

- **Metadata:** Downloaded files are saved using the original video titles.
- **FFmpeg:** If you are building from source and FFmpeg is not installed (or not added to your system's PATH), the MP3
  conversion step will fail. The Windows installer handles this automatically.

## 📄 License

This project is licensed under the **MIT License** — free to use, modify, and distribute. See the `LICENSE` file for more details.
