# Contributing to Bemudex

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |
| yt-dlp | latest |
| FFmpeg | 4.0+ |
| PyQt6 | latest |

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourname/Bemudex.git
cd Bemudex
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install frontend dependencies

```bash
npm install --prefix frontend
```

---

## Running in Development Mode

Start the Vite dev server in one terminal:

```bash
npm run dev --prefix frontend
```

Start the Python backend in another terminal:

```bash
python app.py
```

The backend auto-detects `http://localhost:5173` and loads the dev server instead of the production build.

---

## Running Tests

```bash
# Compile every Python file (catches syntax and import errors)
python -m compileall .

# Lint the frontend
npm run lint --prefix frontend
```

---

## Building for Production

```bash
# Build the frontend bundle
npm run build --prefix frontend

# Run the app against the production build
python app.py
```

---

## Packaging (Windows)

```bash
# Install PyInstaller
pip install pyinstaller

# Build using the spec file
pyinstaller Bemudex.spec
```

The packaged executable will be in `dist/Bemudex/`.

---

## Project Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for a complete description of modules, responsibilities, and the data flow from URL paste to completed download.

---

## Code Style

- Python: follow PEP 8. Use 4-space indentation.
- Imports: always use absolute imports (e.g. `from core.logger import logger`).
- Dependency direction: `app.py → services/ → core/`. Never import upward.
- No premature abstractions. If a function is only used in one place, keep it there.
- Preserve existing behavior when refactoring. This project prioritizes stability over novelty.

---

## Making Changes

1. Create a feature branch: `git checkout -b feature/my-change`
2. Make your changes incrementally. Verify `python -m compileall .` after each significant change.
3. Run `npm run lint --prefix frontend` and fix any warnings.
4. Commit with a clear message describing what changed and why.
5. Open a pull request against `main`.

---

## Version Bumping

Version is defined in **one place only**: `core/version.py`.

```python
VERSION = "v2.0.0"
BUILD = "2026.06.11"
RELEASE_CHANNEL = "stable"
```

The frontend reads this via `window.pywebview.api.get_dependency_status()`. Do not hardcode the version string anywhere else.
