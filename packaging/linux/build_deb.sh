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

echo "📂 Creating Debian package directory structure..."
rm -rf build/debian
mkdir -p build/debian/DEBIAN
mkdir -p build/debian/usr/bin
mkdir -p build/debian/usr/share/applications
mkdir -p build/debian/usr/share/pixmaps
mkdir -p build/debian/usr/share/icons/hicolor/256x256/apps
mkdir -p build/debian/usr/share/metainfo
mkdir -p build/debian/usr/share/doc/bemudex

# Copy control template and postrm script
cp packaging/linux/control build/debian/DEBIAN/control
cp packaging/linux/postrm build/debian/DEBIAN/postrm
chmod 755 build/debian/DEBIAN/postrm

# Copy the entire collection built by PyInstaller
cp -r dist/Bemudex/* build/debian/usr/bin/

# We need a small launcher script at /usr/bin/bemudex that calls /usr/bin/Bemudex
cat << 'EOF' > build/debian/usr/bin/bemudex
#!/bin/sh
exec "/usr/bin/Bemudex" "$@"
EOF
chmod +x build/debian/usr/bin/bemudex

# Copy desktop and icon assets
cp packaging/linux/org.bemudex.Bemudex.desktop build/debian/usr/share/applications/
cp assets/bemudex_256.png build/debian/usr/share/pixmaps/org.bemudex.Bemudex.png
cp assets/bemudex_256.png build/debian/usr/share/icons/hicolor/256x256/apps/org.bemudex.Bemudex.png

# Copy AppStream metainfo
cp packaging/linux/org.bemudex.Bemudex.metainfo.xml build/debian/usr/share/metainfo/

# Copy copyright metadata
cp packaging/linux/copyright build/debian/usr/share/doc/bemudex/

echo "⚖️ Calculating Installed-Size..."
# Calculate size of the files to be installed (under usr) in kilobytes
INSTALLED_SIZE=$(du -sk build/debian/usr | cut -f1)
echo "Installed-Size: $INSTALLED_SIZE" >> build/debian/DEBIAN/control
echo "Computed Installed-Size: ${INSTALLED_SIZE} KB"

echo "🔒 Setting standard permissions..."
# Ensure directories have 755
find build/debian -type d -exec chmod 755 {} +
# Ensure desktop files, icons, metadata, and doc files have 644
find build/debian/usr/share -type f -exec chmod 644 {} +
# Ensure DEBIAN control files have 644, postrm has 755
chmod 644 build/debian/DEBIAN/control
chmod 755 build/debian/DEBIAN/postrm

echo "🔨 Building Debian package..."
mkdir -p dist
dpkg-deb --root-owner-group --build build/debian dist/bemudex_2.0.2_amd64.deb

echo "🎉 Debian package built at dist/bemudex_2.0.2_amd64.deb"
