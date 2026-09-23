# Contributing to Bemudex

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10+ |
| yt-dlp | latest |
| FFmpeg | 4.0+ |
| PyQt6 | 6.5+ |

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/vish-1109/Bemudex.git
cd Bemudex
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## Running in Development Mode

Run the native Qt application directly:

```bash
python main.py
```

---

## Running Tests and Linting

```bash
# Compile every Python file (catches syntax and import errors)
python -m compileall main.py core services ui workers

# Run pyflakes linter
pyflakes main.py core services ui workers
```

---

## Packaging (Linux)

To build standalone Linux distribution packages (`.AppImage` and `.deb`):

```bash
# Build AppImage
./packaging/linux/build_appimage.sh

# Build Debian package
./packaging/linux/build_deb.sh
```

Packaged binaries will be located in `dist/`.

---

## Project Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for a complete description of modules, responsibilities, and the data flow from URL paste to completed download.

---

## Code Style

- Python: follow PEP 8. Use 4-space indentation.
- Imports: always use absolute imports (e.g. `from core.logger import logger`).
- Dependency direction: `ui/ → workers/ → services/ → core/`. Never import upward.
- No premature abstractions. If a function is only used in one place, keep it there.
- Preserve existing behavior when refactoring. This project prioritizes stability over novelty.

---

## Making Changes

1. Create a feature branch: `git checkout -b feature/my-change`
2. Make your changes incrementally. Verify `python -m compileall main.py core services ui workers` after each significant change.
3. Run `pyflakes main.py core services ui workers` and fix any warnings.
4. Commit with a clear message describing what changed and why.
5. Open a pull request against `main`.

---

## Version Bumping

Version is defined in **one place only**: `core/version.py`.

```python
VERSION = "v3.0.0"
BUILD = "2026.09.22"
RELEASE_CHANNEL = "stable"
```

The application reads this across `main.py`, `ui/`, and `services/`. Update `packaging/linux/control` and `packaging/linux/org.bemudex.Bemudex.metainfo.xml` when preparing a package release.
