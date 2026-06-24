#!/bin/bash
set -e

# Go to repository root
CDPATH= cd "$(dirname "$0")/../.."

echo "📦 Building Vite frontend..."
cd frontend
npm run build
cd ..

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
mkdir -p build/AppDir/usr/share/icons/hicolor/256x256/apps
mkdir -p build/AppDir/usr/share/metainfo

# Copy the entire collection built by PyInstaller to AppDir's usr/bin/
cp -r dist/Bemudex/* build/AppDir/usr/bin/

# Copy desktop and icon assets
cp packaging/linux/org.bemudex.Bemudex.desktop build/AppDir/usr/share/applications/
cp assets/bemudex_256.png build/AppDir/usr/share/icons/hicolor/256x256/apps/org.bemudex.Bemudex.png

# Copy AppStream metainfo
cp packaging/linux/org.bemudex.Bemudex.metainfo.xml build/AppDir/usr/share/metainfo/

# Symlink desktop file and icon to the AppDir root (required by AppImage specification)
ln -sf usr/share/applications/org.bemudex.Bemudex.desktop build/AppDir/org.bemudex.Bemudex.desktop
ln -sf usr/share/icons/hicolor/256x256/apps/org.bemudex.Bemudex.png build/AppDir/org.bemudex.Bemudex.png

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
export ARCH=x86_64
$APPIMAGE_TOOL build/AppDir dist/Bemudex-x86_64.AppImage

echo "🎉 AppImage built successfully at dist/Bemudex-x86_64.AppImage"
