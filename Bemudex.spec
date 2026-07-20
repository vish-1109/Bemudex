# -*- mode: python ; coding: utf-8 -*-
import sys
import os

datas_list = [
    ('assets', 'assets'),
    ('core', 'core'),
    ('services', 'services'),
    ('frontend/dist', 'frontend/dist')
]

if sys.platform == 'win32' and os.path.exists('ffmpeg.exe'):
    datas_list.append(('ffmpeg.exe', '.'))

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas_list,
    hiddenimports=['mutagen', 'certifi'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Bemudex',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/favicon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Bemudex',
)

