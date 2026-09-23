#!/bin/bash
set -e

# Go to repository root
CDPATH= cd "$(dirname "$0")/../.."

echo "🔍 Validating venv dependencies against requirements.txt..."
if [ -d "venv" ]; then
    PYTHON_BIN="./venv/bin/python"
else
    PYTHON_BIN="python3"
fi
MISSING=0
while IFS= read -r pkg || [ -n "$pkg" ]; do
    [[ -z "$pkg" || "$pkg" == \#* ]] && continue
    pkg_clean=$(echo "$pkg" | sed 's/[>=<!].*//' | tr -d '[:space:]')
    if ! $PYTHON_BIN -c "import importlib.metadata; importlib.metadata.version('$pkg_clean')" 2>/dev/null; then
        echo "❌ Missing dependency: $pkg_clean"
        MISSING=1
    fi
done < requirements.txt
if [ "$MISSING" -eq 1 ]; then
    echo ""
    echo "🚨 Build aborted: one or more packages in requirements.txt are not installed in the venv."
    echo "   Run: ./venv/bin/pip install -r requirements.txt"
    exit 1
fi
echo "✅ All dependencies verified."

echo "🐍 Compiling PyInstaller backend..."
# Use venv python if available
if [ -d "venv" ]; then
    ./venv/bin/pyinstaller --noconfirm Bemudex.spec
else
    pyinstaller --noconfirm Bemudex.spec
fi

echo "📂 Creating AppDir structure..."
rm -rf build/AppDir
mkdir -p build/AppDir/usr/bin
mkdir -p build/AppDir/usr/share/applications
mkdir -p build/AppDir/usr/share/pixmaps
mkdir -p build/AppDir/usr/share/metainfo

# Copy the entire collection built by PyInstaller to AppDir's usr/bin/
cp -r dist/Bemudex/* build/AppDir/usr/bin/

# Copy desktop and icon assets
cp packaging/linux/org.bemudex.Bemudex.desktop build/AppDir/usr/share/applications/
cp assets/bemudex_256.png build/AppDir/usr/share/pixmaps/org.bemudex.Bemudex.png

# Copy complete hicolor icon resolution suite
for size_dir in assets/icons/*x*; do
    [ -d "$size_dir" ] || continue
    size=$(basename "$size_dir")
    mkdir -p "build/AppDir/usr/share/icons/hicolor/${size}/apps"
    cp "${size_dir}/org.bemudex.Bemudex.png" "build/AppDir/usr/share/icons/hicolor/${size}/apps/"
done

if [ -d "assets/icons/scalable" ]; then
    mkdir -p build/AppDir/usr/share/icons/hicolor/scalable/apps
    cp assets/icons/scalable/org.bemudex.Bemudex.svg build/AppDir/usr/share/icons/hicolor/scalable/apps/
fi

# Copy AppStream metainfo
cp packaging/linux/org.bemudex.Bemudex.metainfo.xml build/AppDir/usr/share/metainfo/

# Symlink desktop file and icon to the AppDir root (required by AppImage specification)
ln -sf usr/share/applications/org.bemudex.Bemudex.desktop build/AppDir/org.bemudex.Bemudex.desktop
ln -sf usr/share/icons/hicolor/256x256/apps/org.bemudex.Bemudex.png build/AppDir/org.bemudex.Bemudex.png
ln -sf usr/share/icons/hicolor/256x256/apps/org.bemudex.Bemudex.png build/AppDir/.DirIcon
if [ -f "build/AppDir/usr/share/icons/hicolor/scalable/apps/org.bemudex.Bemudex.svg" ]; then
    ln -sf usr/share/icons/hicolor/scalable/apps/org.bemudex.Bemudex.svg build/AppDir/org.bemudex.Bemudex.svg
fi

# Copy and prepare AppRun
cp packaging/linux/AppRun build/AppDir/AppRun
chmod +x build/AppDir/AppRun

echo "🔨 Locating appimagetool..."
APPIMAGE_TOOL="appimagetool"
if ! command -v appimagetool &> /dev/null; then
    echo "⚠️ appimagetool not found in PATH. Checking local cache..."
    if [ ! -f "build/appimagetool" ]; then
        echo "⬇️ Downloading appimagetool..."
        mkdir -p build
        curl -s -L -o build/appimagetool https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
        chmod +x build/appimagetool
    fi
    APPIMAGE_TOOL="./build/appimagetool"
fi

echo "🔨 Packaging AppImage..."
mkdir -p dist
rm -f dist/Bemudex-x86_64.AppImage
export ARCH=x86_64
export APPIMAGE_EXTRACT_AND_RUN=1

RUNTIME_OPT=""
if [ -f "build/runtime-x86_64" ]; then
    RUNTIME_OPT="--runtime-file build/runtime-x86_64"
fi

$APPIMAGE_TOOL $RUNTIME_OPT build/AppDir dist/Bemudex-x86_64.AppImage

echo "🎉 AppImage built successfully at dist/Bemudex-x86_64.AppImage"
