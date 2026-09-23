# Bemudex Architecture

## Overview

Bemudex 3.0 is a desktop media downloader built with a native PyQt6 interface on Linux, powered by yt-dlp and FFmpeg. Application components communicate through Qt signals and slots across UI views, background `QThread` workers, and service modules.

---

## Directory Structure

```
Bemudex/
│
├── main.py                  # Native Qt application bootstrap, window initialization, themes
│
├── ui/                      # PyQt6 UI components and views
│   ├── main_window.py       # Main application window, navigation, queue coordination
│   ├── home_view.py         # Primary download view, URL bar, media options
│   ├── history_view.py      # Download history view with file actions
│   ├── settings_view.py     # Settings and diagnostics view
│   ├── audio_options.py     # Audio format, bitrate, and metadata tagging options
│   ├── downloads_panel.py   # Sliding right panel with active/queued downloads
│   ├── download_card.py     # Individual download card with progress, speed, ETA
│   ├── themes.py            # Color palette and theme definitions (Onyx Dark, etc.)
│   └── styles.py            # Global stylesheet generator
│
├── workers/                 # Background QThread workers
│   ├── download_worker.py   # Manages download execution and emits progress signals
│   ├── metadata_worker.py   # Asynchronously fetches media/playlist info
│   └── engine_worker.py     # Performs yt-dlp engine updates and version checks
│
├── services/                # Business logic services
│   ├── config_manager.py    # Config file read/write; download folder and theme management
│   ├── history_manager.py   # Download history load/save; file size formatting
│   ├── clipboard_manager.py # Linux clipboard read/write
│   ├── dependency_manager.py# FFmpeg detection; yt-dlp version check and update
│   └── downloader.py        # Download engine: yt-dlp invocation, progress hooks, postprocessors
│
├── core/                    # Application-wide utilities
│   ├── constants.py         # Shared constants: file paths, limits, URLs
│   ├── logger.py            # Rotating file logger + URL sanitization helpers
│   └── version.py           # Single source of truth for VERSION, BUILD, RELEASE_CHANNEL
│
├── assets/                  # Application icons and bundled fonts
│   └── fonts/               # Bundled Ubuntu TrueType fonts
│
├── docs/                    # Project documentation
│   ├── ARCHITECTURE.md      # This file
│   ├── API.md               # Historical PyWebView API reference (v2.x)
│   └── CONTRIBUTING.md      # Developer setup and contribution guide
│
├── packaging/               # Linux packaging scripts and templates
│   └── linux/               # AppImage and Debian package builders
│
├── requirements.txt         # Python dependencies
└── Bemudex.spec             # PyInstaller build specification
```

---

## Dependency Direction

Dependencies flow downward:

```
main.py
    ↓
ui/  ──→  workers/
             ↓
         services/
             ↓
           core/
```

- `core/` never imports from `services/`, `workers/`, or `ui/`.
- `services/` may import from `core/` but never from `workers/` or `ui/`.
- `workers/` may import from `services/` and `core/`.
- `ui/` coordinates `workers/`, `services/`, and `core/`.
- `main.py` bootstraps the QApplication, registers bundled fonts, applies stylesheet, and instantiates `MainWindow`.

---

## Module Responsibilities

### `main.py`
- Instantiates `QApplication`, configures desktop environment metadata, registers bundled fonts.
- Loads theme and UI scaling settings, applies global stylesheets.
- Instantiates and displays `MainWindow`.

### `ui/`
- Implements the complete native desktop interface via PyQt6 widgets and custom components.
- `MainWindow`: Coordinates sidebar navigation, title bar actions, and global download worker dispatching.
- `HomeView`: Manages the primary search/URL input, video format selections, and audio tagging controls.
- `DownloadsPanel` & `DownloadCard`: Displays active concurrent downloads, speed, ETA, progress bars, and retry buttons.
- `HistoryView`: Provides interactive list of past downloads with playback and directory reveal shortcuts.
- `SettingsView`: Manages download destinations, theme selection, rate limiting, and system diagnostics.

### `workers/`
- `DownloadWorker`: Executes downloads via `downloader.start_download`, emitting real-time signals for speed, progress, completion, and error states.
- `MetadataWorker`: Extracts video and playlist metadata in the background to keep the UI fully responsive.
- `EngineCheckWorker` / `EngineUpdateWorker` / `EngineRollbackWorker`: Checks PyPI for upstream yt-dlp updates, handles atomic wheel downloads and replacements, and provides automatic rollback protection.

### `core/`
- `constants.py`: Shared file paths (`CONFIG_FILE`, `HISTORY_FILE`), limits (`HISTORY_LIMIT`), and URLs (`YT_DLP_PYPI_URL`).
- `logger.py`: Rotating file logger (`~/.bemudex/logs/bemudex.log`) with URL and message sanitization.
- `version.py`: Single source of truth for `VERSION`, `BUILD`, and `RELEASE_CHANNEL`.

### `services/`
- `config_manager.py`: Thread-safe JSON configuration management with corruption backup and recovery.
- `history_manager.py`: Thread-safe JSON history persistence and formatted disk-size utilities.
- `clipboard_manager.py`: Linux clipboard monitoring for automatic media link detection.
- `dependency_manager.py`: FFmpeg validation and standalone yt-dlp engine updater.
- `downloader.py`: Multi-threaded download execution using yt-dlp, subtitle extraction, audio conversion, and ID3/thumbnail embedding.

---

## Data Flow: URL → Completed Download

```
User enters URL in HomeView
        ↓
HomeView initiates MetadataWorker (QThread)
        ↓
metadata_ready signal emitted → HomeView renders video info & audio tags
        ↓
User clicks "Download Now"
        ↓
MainWindow receives download_requested signal → validates path / file overwrite
        ↓
DownloadWorker (QThread) started
    → calls services/downloader.py: start_download()
    → progress hooks emit progress_updated signal (live speed, percent, ETA)
    → DownloadsPanel updates track download card in real time
    → item completed → file saved to history via services/history_manager
    → download_finished signal emitted
```

---

## Threading Model

- The main thread runs the Qt event loop (`QApplication.exec()`).
- Background tasks (`DownloadWorker`, `MetadataWorker`, `EngineWorker`) subclass `QThread`.
- Thread-to-UI communication is mediated entirely via Qt Signals (`pyqtSignal`) and Slots (`pyqtSlot`).
- Config file writes are serialized via `config_lock` in `services/config_manager.py`.
- History writes are serialized via `history_lock` in `services/history_manager.py`.

---

## Historical Architecture (v2.x)

In Bemudex 2.x, the application used a hybrid architecture combining PyWebView with a React/Vite single-page application communicating via a `window.pywebview.api` JavaScript bridge. In Bemudex 3.0, this stack was completely replaced with a native PyQt6 interface to achieve faster startup, lower memory consumption, and seamless Linux desktop integration.
