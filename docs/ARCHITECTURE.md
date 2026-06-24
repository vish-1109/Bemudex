# Bemudex Architecture

## Overview

Bemudex is a desktop media downloader built with a Python backend (PyWebView + yt-dlp) and a React/Vite frontend. The two sides communicate exclusively through `window.pywebview.api`, which exposes the `Api` class defined in `app.py`.

---

## Directory Structure

```
Bemudex/
│
├── app.py                   # Application bootstrap, dependency wiring, PyWebView API
│
├── core/                    # Application-wide utilities (no business logic)
│   ├── __init__.py
│   ├── constants.py         # Shared constants: file paths, limits, URLs
│   ├── logger.py            # Rotating file logger + URL sanitization helpers
│   └── version.py           # Single source of truth for VERSION, BUILD, RELEASE_CHANNEL
│
├── services/                # Business logic services
│   ├── __init__.py
│   ├── config_manager.py    # Config file read/write; download folder management
│   ├── history_manager.py   # Download history load/save; file size formatting
│   ├── clipboard_manager.py # Cross-platform clipboard read/write
│   ├── dependency_manager.py# FFmpeg detection; yt-dlp version check and update
│   └── downloader.py        # Download engine: yt-dlp invocation, progress hooks, postprocessors
│
├── frontend/                # React/Vite frontend (unchanged by this refactor)
│   └── src/
│
├── assets/                  # Application icons and static assets
│
├── docs/                    # Project documentation
│   ├── ARCHITECTURE.md      # This file
│   ├── API.md               # PyWebView API reference
│   └── CONTRIBUTING.md      # Developer setup and contribution guide
│
├── tests/                   # Test suite (future)
│
├── requirements.txt         # Python dependencies
├── Bemudex.spec             # PyInstaller build specification
└── Bemudex_Installer.iss    # Inno Setup installer script (Windows)
```

---

## Dependency Direction

Dependencies flow in one direction only:

```
app.py
    ↓
services/
    ↓
core/
```

- `core/` never imports from `services/` or `app.py`.
- `services/` may import from `core/` but never from `app.py`.
- `app.py` may import from both `core/` and `services/`.

---

## Module Responsibilities

### `app.py`
- Instantiates `Api`, `DependencyManager`, and the PyWebView window.
- Wires all service modules together.
- Exposes the full `window.pywebview.api` surface to the frontend.
- Handles application lifecycle: startup, window events, on-close history flush.
- Contains no standalone business logic beyond orchestration.

### `core/constants.py`
- Defines shared file paths (`CONFIG_FILE`, `HISTORY_FILE`), limits (`HISTORY_LIMIT`), and URLs (`YT_DLP_PYPI_URL`).
- Pure constants — no imports from other project modules.

### `core/logger.py`
- Sets up the rotating file logger (`~/.bemudex/logs/bemudex.log`).
- Provides `sanitize_url` and `sanitize_msg` for privacy-safe log output.
- The only permitted module-level side effect in the project (logger initialization).

### `core/version.py`
- Single source of truth: `VERSION`, `BUILD`, `RELEASE_CHANNEL`.

### `services/config_manager.py`
- Owns `config_lock` (threading.Lock).
- `load_config()` / `save_config(config)` — atomic JSON config file access with corruption recovery.
- `load_last_folder()` / `save_last_folder(folder)` — remembers the user's last download directory.
- `get_default_download_folder()` — platform-aware downloads directory detection.

### `services/history_manager.py`
- `load_history()` / `save_history(history)` — reads and writes the JSON history file.
- `get_file_size_str(filepath)` — human-readable file size formatting.
- Stateful caching (`history_cache`, `history_lock`, `save_timer`) lives on the `Api` instance in `app.py`.

### `services/clipboard_manager.py`
- `get_clipboard_text()` — multi-tier clipboard reader: PyQt6 → tkinter → platform CLI (xclip / pbpaste / PowerShell).
- `read_clipboard()` / `copy_to_clipboard(text)` — simple PyQt6-backed read/write.

### `services/dependency_manager.py`
- `DependencyManager` class:
  - `detect()` — finds FFmpeg (custom path → bundled → system PATH), caches result.
  - `_probe_ffmpeg(path)` — runs `ffmpeg -version` to validate an executable.
  - `check()` — queries PyPI for the latest yt-dlp version.
  - `update()` — upgrades yt-dlp via `yt_dlp -U` or pip, then reloads the module.
  - `reset()` — removes custom FFmpeg path from config, re-runs detection.
  - `diagnostics()` — collects full system health report for the UI diagnostics panel.
  - `versions()` — returns Bemudex and yt-dlp version info.

### `services/downloader.py`
- `get_ffmpeg_path()` — resolves FFmpeg binary: config file → bundled → system.
- `start_download(...)` — entry point for all downloads (video, audio, playlist).
  - Runs in a background thread.
  - Uses `hook` (download progress) and `post_hook` (postprocessor completion) for real-time UI updates.
  - Supports concurrent playlist downloads via `ThreadPoolExecutor(max_workers=2)`.
  - Cleans up temporary thumbnail, part, and test files in a `finally` block.

---

## Data Flow: URL → Completed Download

```
User pastes URL (frontend)
        ↓
window.pywebview.api.fetch_metadata(url)   [app.py → services/downloader.py (get_ffmpeg_path)]
        ↓
window.onMetadata(data)                    [JS callback, triggered from background thread]
        ↓
User selects format/quality and clicks Download
        ↓
window.pywebview.api.start_download(...)   [app.py]
        ↓
services/downloader.py: start_download()   [background thread]
    → yt-dlp.extract_info (flat, for playlist queue)
    → window.onPlaylistMetadata(items)     [JS callback]
    → yt-dlp.YoutubeDL.download()
        → hook() → window.onProgress(data) [JS callback, per chunk]
        → post_hook() → window.onProgress (finished per item)
    → on_done() → services/history_manager: load/save
               → window.onDownloadFinished(files, total, cancelled)
```

---

## Threading Model

- The main thread runs the PyWebView event loop.
- `start_download` spawns one daemon thread (`run()`), which may itself spawn `ThreadPoolExecutor` workers for playlists.
- `fetch_metadata` spawns one daemon thread (`_fetch()`).
- All `window.evaluate_js` calls are serialized through `self.js_lock` (threading.Lock on `Api`).
- History writes are debounced via `threading.Timer` (0.5 s delay) and protected by `self.history_lock`.
- Config file writes are protected by `config_lock` in `services/config_manager.py`.
