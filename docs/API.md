# Bemudex PyWebView API Reference

All methods are exposed via `window.pywebview.api` in the frontend. They correspond directly to public methods on the `Api` class in `app.py`.

---

## Callbacks (Backend → Frontend)

These JavaScript functions are called by the backend. They must be defined on `window` before any download starts.

| Callback | Signature | Description |
|---|---|---|
| `window.onProgress` | `(data: object)` | Progress update for a single download item |
| `window.onPlaylistMetadata` | `(items: object[])` | Initial playlist queue metadata |
| `window.onMetadata` | `(data: object)` | Full video/playlist metadata after fetch |
| `window.onDownloadFinished` | `(files: string[], total: number, cancelled: boolean)` | Download session completed |
| `window.onLog` | `(message: string)` | Human-readable log message |

### `onProgress` payload

```json
{
  "id": "video_id",
  "title": "Video Title",
  "percent": 42.5,
  "speed": "3.2 MB/s",
  "eta": "1:23",
  "sizeInfo": "42.5 MB / 100.0 MB",
  "status": "downloading | converting | finished | failed",
  "format": "video | audio",
  "quality": "1080 | 720 | best | ...",
  "thumbnail": "https://...",
  "filePath": "/path/to/file.mp4"
}
```

### `onMetadata` payload

```json
{
  "title": "Video Title",
  "channel": "Channel Name",
  "duration": 266,
  "duration_str": "4:26",
  "view_count": 1234567,
  "upload_date": "3 weeks ago",
  "thumbnail": "https://...",
  "is_live": false,
  "is_playlist": false,
  "playlist_count": 0,
  "resolutions": [2160, 1080, 720, 480],
  "has_hdr": false,
  "has_av1": true,
  "has_vp9": true,
  "has_chapters": false,
  "resolution_sizes": { "1080": "≈150 MB", "best": "≈150 MB" },
  "fps": 60,
  "filesize_approx": null
}
```

On error:
```json
{ "error": "Error message string" }
```

---

## API Methods (Frontend → Backend)

### `load_last_folder()`
Returns the last used download folder, or the system default Downloads directory.

**Returns:** `string`

---

### `browse_folder()`
Opens a native folder picker dialog.

**Returns:** `string | null` — selected folder path, or `null` if cancelled.

---

### `open_folder(path: string)`
Opens the folder containing `path` in the system file manager.

**Returns:** `void`

---

### `check_ffmpeg()`
Checks whether FFmpeg is available.

**Returns:** `boolean`

---

### `get_dependency_status()`
Returns full dependency status for the status panel.

**Returns:**
```json
{
  "bemudex": { "version": "v2.0.0", "build": "2026.06.11", "release_channel": "stable" },
  "ytdlp": { "version": "2024.x.x", "status": "unknown" },
  "ffmpeg": { "installed": true, "version": "6.0", "path": "/usr/bin/ffmpeg" },
  "folder_writable": true,
  "status": "ready | attention_required | error"
}
```

---

### `check_ytdlp_updates()`
Checks PyPI for the latest yt-dlp version.

**Returns:**
```json
{
  "status": "success | error",
  "installed": "2024.x.x",
  "latest": "2024.y.y",
  "update_available": true,
  "message": "Error string (on error only)"
}
```

---

### `update_ytdlp()`
Upgrades yt-dlp and reloads the module.

**Returns:**
```json
{ "status": "success | error", "message": "...", "version": "2024.y.y" }
```

---

### `locate_ffmpeg()`
Opens a file picker for the user to locate an FFmpeg binary and validates it.

**Returns:**
```json
{ "status": "success | cancelled | error", "path": "/path/to/ffmpeg", "version": "6.0" }
```

---

### `detect_ffmpeg_api()`
Returns the currently detected FFmpeg info.

**Returns:**
```json
{ "installed": true, "version": "6.0", "path": "/usr/bin/ffmpeg" }
```

---

### `reset_dependency_config()`
Removes the custom FFmpeg path from config and re-runs detection.

**Returns:** Same shape as `get_dependency_status()`.

---

### `get_diagnostics(current_theme?: string)`
Returns a full system diagnostics report.

**Returns:**
```json
{
  "bemudex_version": "v2.0.0",
  "build_number": "2026.06.11",
  "release_channel": "stable",
  "os": "Linux",
  "os_release": "5.15.0",
  "architecture": "x86_64",
  "python_version": "3.11.0",
  "downloads_folder": "/home/user/Downloads",
  "folder_writable": true,
  "folder_writable_status": "Writable",
  "ytdlp_version": "2024.x.x",
  "ffmpeg_version": "6.0",
  "ffmpeg_path": "/usr/bin/ffmpeg",
  "config_file_location": "/home/user/.bemudex_config.json",
  "current_theme": "dark",
  "backend_status": "running",
  "internet_status": "Connected"
}
```

---

### `fetch_metadata(url: string)`
Starts a background metadata extraction. Result is delivered via `window.onMetadata`.

**Returns:** `void`

---

### `start_download(url, folder, download_type, quality, options?)`
Starts a download. Progress is delivered via `window.onProgress`, `window.onPlaylistMetadata`, and `window.onDownloadFinished`.

| Parameter | Type | Description |
|---|---|---|
| `url` | `string` | Video or playlist URL |
| `folder` | `string` | Destination folder path |
| `download_type` | `"video" \| "audio"` | Output format category |
| `quality` | `string` | e.g. `"1080"`, `"720"`, `"best"` |
| `options` | `object?` | See below |

**Options object:**
```json
{
  "audioFormat": "mp3 | m4a | aac | flac | wav | opus",
  "title": "Custom title string",
  "artist": "Custom artist string",
  "embedThumbnail": true,
  "embedTags": true,
  "embedChapters": true,
  "customCover": "data:image/jpeg;base64,...",
  "ratelimit": 0
}
```

**Returns:** `void`

---

### `cancel_download()`
Signals the active download to stop.

**Returns:** `void`

---

### `is_downloading()`
Returns whether a download is currently in progress.

**Returns:** `boolean`

---

### `check_overwrite(folder, title, download_type, audio_format?)`
Checks whether the output file already exists.

**Returns:**
```json
{ "exists": true, "path": "/path/to/file.mp4" }
```

---

### `get_history()`
Returns the current download history (cached in memory).

**Returns:** Array of history items.

---

### `clear_history()`
Clears and persists an empty history.

**Returns:** `boolean`

---

### `remove_history_item(file_path: string)`
Removes one entry from history by file path.

**Returns:** `boolean`

---

### `play_file(file_path: string)`
Opens a file with the system default player.

**Returns:** `boolean`

---

### `get_clipboard_text()`
Returns current clipboard text content.

**Returns:** `string`

---

### `copy_to_clipboard(text: string)`
Writes text to the clipboard.

**Returns:** `boolean`

---

### `get_disk_usage(folder: string)`
Returns disk usage statistics for the given folder's volume.

**Returns:**
```json
{
  "total": 500000000000,
  "used": 200000000000,
  "free": 300000000000,
  "free_str": "279.4 GB",
  "total_str": "465 GB"
}
```
