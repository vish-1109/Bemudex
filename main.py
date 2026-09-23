import os
import shutil
import sys

# Restore original library environment variables for child processes (like system FFmpeg)
# to prevent loader conflicts caused by PyInstaller or AppImage LD_LIBRARY_PATH overrides.
if getattr(sys, 'frozen', False):
    for var in ['LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH']:
        orig_var = var + '_ORIG'
        if orig_var in os.environ:
            os.environ[var] = os.environ[orig_var]
        else:
            os.environ.pop(var, None)

# Ensure JS runtimes (bun, deno) installed in user home are discoverable by yt-dlp
# for YouTube signature/n-parameter challenge solving.
_js_runtime_dirs = [
    os.path.join(os.path.expanduser('~'), '.bun', 'bin'),
    os.path.join(os.path.expanduser('~'), '.deno', 'bin'),
]
for _d in _js_runtime_dirs:
    if os.path.isdir(_d) and _d not in os.environ.get('PATH', ''):
        os.environ['PATH'] = _d + os.pathsep + os.environ.get('PATH', '')

from core.logger import logger
from core.version import VERSION
from core.constants import (
    YT_DLP_ENGINE_PARENT_DIR,
    YT_DLP_ENGINE_DIR,
    YT_DLP_ENGINE_BACKUP_DIR
)

# Startup verification & fallback logic for user-installed override engine
if os.path.exists(YT_DLP_ENGINE_DIR) and os.path.exists(os.path.join(YT_DLP_ENGINE_DIR, "__init__.py")):
    sys.path.insert(0, YT_DLP_ENGINE_PARENT_DIR)
    try:
        import yt_dlp
        _ = yt_dlp.version.__version__
        logger.info(f"Loaded override yt-dlp engine from user folder (version: {yt_dlp.version.__version__})")
    except Exception as e:
        logger.error(f"Failed to load user-installed yt-dlp engine: {e}")
        if YT_DLP_ENGINE_PARENT_DIR in sys.path:
            sys.path.remove(YT_DLP_ENGINE_PARENT_DIR)
        for key in list(sys.modules.keys()):
            if key == 'yt_dlp' or key.startswith('yt_dlp.'):
                try:
                    del sys.modules[key]
                except KeyError:
                    pass

        if os.path.exists(YT_DLP_ENGINE_BACKUP_DIR) and os.path.exists(os.path.join(YT_DLP_ENGINE_BACKUP_DIR, "__init__.py")):
            logger.info("Restoring override engine from backup folder...")
            try:
                if os.path.exists(YT_DLP_ENGINE_DIR):
                    shutil.rmtree(YT_DLP_ENGINE_DIR)
                shutil.copytree(YT_DLP_ENGINE_BACKUP_DIR, YT_DLP_ENGINE_DIR)
                sys.path.insert(0, YT_DLP_ENGINE_PARENT_DIR)
                import yt_dlp
                _ = yt_dlp.version.__version__
                logger.info(f"Successfully rolled back and loaded backup engine (version: {yt_dlp.version.__version__})")
            except Exception as ex:
                logger.error(f"Rollback to backup engine failed: {ex}")
                if YT_DLP_ENGINE_PARENT_DIR in sys.path:
                    sys.path.remove(YT_DLP_ENGINE_PARENT_DIR)
                for key in list(sys.modules.keys()):
                    if key == 'yt_dlp' or key.startswith('yt_dlp.'):
                        try:
                            del sys.modules[key]
                        except KeyError:
                            pass
        else:
            logger.info("No valid backup engine found to restore. Falling back to bundled copy.")
else:
    if os.path.exists(YT_DLP_ENGINE_BACKUP_DIR) and os.path.exists(os.path.join(YT_DLP_ENGINE_BACKUP_DIR, "__init__.py")):
        if os.path.exists(YT_DLP_ENGINE_DIR):
            logger.warning("User engine directory is corrupted (missing __init__.py). Restoring active engine from backup folder...")
        else:
            logger.info("User engine directory is missing. Restoring active engine from backup folder...")
        try:
            if os.path.exists(YT_DLP_ENGINE_DIR):
                shutil.rmtree(YT_DLP_ENGINE_DIR)
            shutil.copytree(YT_DLP_ENGINE_BACKUP_DIR, YT_DLP_ENGINE_DIR)
            sys.path.insert(0, YT_DLP_ENGINE_PARENT_DIR)
            import yt_dlp
            _ = yt_dlp.version.__version__
            logger.info(f"Successfully loaded restored backup engine (version: {yt_dlp.version.__version__})")
        except Exception as ex:
            logger.error(f"Failed to restore active engine from backup: {ex}")
            if YT_DLP_ENGINE_PARENT_DIR in sys.path:
                sys.path.remove(YT_DLP_ENGINE_PARENT_DIR)

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QFont, QIcon
from services.config_manager import load_theme, load_ui_scale
from ui.main_window import MainWindow
from ui.styles import get_stylesheet
from ui.themes import get_theme, create_theme_palette


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Bemudex")
    app.setApplicationVersion(VERSION)
    app.setDesktopFileName("org.bemudex.Bemudex")

    icon_path = os.path.join(os.path.dirname(__file__), "assets", "bemudex_256.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Register bundled Ubuntu fonts
    fonts_dir = os.path.join(os.path.dirname(__file__), "assets", "fonts")
    if os.path.exists(fonts_dir):
        for font_file in sorted(os.listdir(fonts_dir)):
            if font_file.endswith(".ttf"):
                QFontDatabase.addApplicationFont(os.path.join(fonts_dir, font_file))

    scale = load_ui_scale() / 100.0
    app.setFont(QFont("Ubuntu", max(7, int(round(10 * scale)))))

    theme = get_theme(load_theme())
    hints = app.styleHints()
    if hasattr(hints, "setColorScheme"):
        hints.setColorScheme(Qt.ColorScheme.Dark if theme.is_dark else Qt.ColorScheme.Light)
    app.setStyleSheet(get_stylesheet(theme, scale=scale))
    app.setPalette(create_theme_palette(theme))

    window = MainWindow()
    window.show()
    window.raise_()
    window.activateWindow()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
