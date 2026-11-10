import os
import sys
import shutil
import subprocess
from core.logger import logger
from services.config_manager import load_desktop_notifications

_tray_instance = None


def register_tray_instance(tray):
    global _tray_instance
    _tray_instance = tray


def send_desktop_notification(title: str, message: str, app_name: str = "Bemudex") -> bool:
    """
    Sends a native OS desktop notification if enabled in preferences.
    Uses notify-send on Linux or QSystemTrayIcon fallback.
    """
    if not load_desktop_notifications():
        return False

    # 1. On Linux, prefer notify-send (works reliably on Wayland/GNOME/KDE even without tray)
    if sys.platform.startswith("linux") and shutil.which("notify-send"):
        try:
            icon_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "256x256", "org.bemudex.Bemudex.png")
            )
            icon_arg = ["-i", icon_path] if os.path.exists(icon_path) else []
            cmd = ["notify-send", f"--app-name={app_name}"] + icon_arg + [title, message]
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            logger.warning(f"notify-send failed: {e}")

    # 2. QSystemTrayIcon fallback (Windows, macOS, or Linux if notify-send is absent)
    try:
        from PyQt6.QtWidgets import QSystemTrayIcon, QApplication
        from PyQt6.QtGui import QIcon
        if not _tray_instance and QApplication.instance() and QSystemTrayIcon.isSystemTrayAvailable():
            icon_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "256x256", "org.bemudex.Bemudex.png")
            )
            tray = QSystemTrayIcon(QIcon(icon_path) if os.path.exists(icon_path) else QIcon(), QApplication.instance())
            tray.show()
            register_tray_instance(tray)
        if _tray_instance:
            _tray_instance.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 4000)
            return True
    except Exception as e:
        logger.warning(f"QSystemTrayIcon notification failed: {e}")

    return False
