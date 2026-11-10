#!/bin/bash
set -e

echo "📦 Setting up Ubuntu 22.04 build environment with Python 3.11 (glibc 2.35)..."
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends software-properties-common ca-certificates curl gnupg gpg-agent > /dev/null
add-apt-repository -y ppa:deadsnakes/ppa > /dev/null
apt-get update -qq

DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    libpython3.11 \
    libpython3.11-dev \
    binutils \
    file \
    ffmpeg \
    libgl1 \
    libegl1 \
    libxkbcommon0 \
    libdbus-1-3 \
    libfontconfig1 \
    libglib2.0-0 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xinerama0 \
    libxcb-xfixes0 > /dev/null

echo "🐍 Setting up Python 3.11 virtual environment..."
python3.11 -m venv /opt/build_venv
/opt/build_venv/bin/pip install --no-cache-dir --quiet --upgrade pip
/opt/build_venv/bin/pip install --no-cache-dir --quiet -r requirements.txt pyinstaller

echo "🔨 Compiling Bemudex with PyInstaller in Ubuntu 22.04 (glibc 2.35)..."
/opt/build_venv/bin/pyinstaller --noconfirm Bemudex.spec

echo "📂 Creating AppDir structure..."
rm -rf build/AppDir
mkdir -p build/AppDir/usr/bin
mkdir -p build/AppDir/usr/share/applications
mkdir -p build/AppDir/usr/share/pixmaps
mkdir -p build/AppDir/usr/share/metainfo

cp -r dist/Bemudex/* build/AppDir/usr/bin/
cp packaging/linux/org.bemudex.Bemudex.desktop build/AppDir/usr/share/applications/
cp assets/bemudex_256.png build/AppDir/usr/share/pixmaps/org.bemudex.Bemudex.png

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

cp packaging/linux/org.bemudex.Bemudex.metainfo.xml build/AppDir/usr/share/metainfo/

ln -sf usr/share/applications/org.bemudex.Bemudex.desktop build/AppDir/org.bemudex.Bemudex.desktop
ln -sf usr/share/icons/hicolor/256x256/apps/org.bemudex.Bemudex.png build/AppDir/org.bemudex.Bemudex.png
ln -sf usr/share/icons/hicolor/256x256/apps/org.bemudex.Bemudex.png build/AppDir/.DirIcon
if [ -f "build/AppDir/usr/share/icons/hicolor/scalable/apps/org.bemudex.Bemudex.svg" ]; then
    ln -sf usr/share/icons/hicolor/scalable/apps/org.bemudex.Bemudex.svg build/AppDir/org.bemudex.Bemudex.svg
fi

cp packaging/linux/AppRun build/AppDir/AppRun
chmod +x build/AppDir/AppRun

APPIMAGE_TOOL="appimagetool"
if ! command -v appimagetool &> /dev/null; then
    if [ ! -f "build/appimagetool" ]; then
        echo "⬇️ Downloading appimagetool..."
        mkdir -p build
        curl -s -L -o build/appimagetool https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
        chmod +x build/appimagetool
    fi
    APPIMAGE_TOOL="./build/appimagetool"
fi

echo "📦 Packaging AppImage..."
mkdir -p dist
rm -f dist/Bemudex-x86_64.AppImage
export ARCH=x86_64
export APPIMAGE_EXTRACT_AND_RUN=1

RUNTIME_OPT=""
if [ -f "build/runtime-x86_64" ]; then
    RUNTIME_OPT="--runtime-file build/runtime-x86_64"
fi

$APPIMAGE_TOOL $RUNTIME_OPT build/AppDir dist/Bemudex-x86_64.AppImage

if [ -n "$HOST_UID" ] && [ -n "$HOST_GID" ]; then
    chown -R "$HOST_UID:$HOST_GID" dist build 2>/dev/null || true
fi

echo "🎉 AppImage built successfully inside Ubuntu 22.04 LTS!"
