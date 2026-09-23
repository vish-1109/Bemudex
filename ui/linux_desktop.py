import os
import shutil
import subprocess
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from core.logger import logger


def open_url_in_browser(url: str) -> bool:
    """Opens a web URL in the system default web browser."""
    if not url:
        return False
    try:
        if QDesktopServices.openUrl(QUrl(url)):
            return True
    except Exception as e:
        logger.warning(f"QDesktopServices.openUrl failed for web URL {url}: {e}")

    try:
        import webbrowser
        return webbrowser.open(url)
    except Exception as e:
        logger.error(f"webbrowser.open failed for web URL {url}: {e}")

    try:
        subprocess.Popen(["xdg-open", url])
        return True
    except Exception as e:
        logger.error(f"xdg-open failed for web URL {url}: {e}")
        return False


def open_file_in_default_app(file_path: str) -> bool:
    """Opens a media file in the system default application on Linux."""
    if not file_path:
        return False
    if file_path.startswith(("http://", "https://")):
        return open_url_in_browser(file_path)
    if not os.path.exists(file_path):
        logger.warning(f"Cannot open file, path does not exist: {file_path}")
        return False
    abs_path = os.path.abspath(file_path)
    try:
        if QDesktopServices.openUrl(QUrl.fromLocalFile(abs_path)):
            return True
    except Exception as e:
        logger.warning(f"QDesktopServices.openUrl failed for {abs_path}: {e}")

    try:
        subprocess.Popen(["xdg-open", abs_path])
        return True
    except Exception as e:
        logger.error(f"xdg-open failed for {abs_path}: {e}")
        return False


def show_file_in_file_manager(file_path: str) -> bool:
    """Reveals the directory containing the file in the default Linux file manager, highlighting the file if possible."""
    if not file_path:
        return False
    abs_path = os.path.abspath(file_path)

    is_file = os.path.isfile(abs_path)
    target_dir = os.path.dirname(abs_path) if is_file else abs_path

    if not os.path.exists(target_dir):
        logger.warning(f"Cannot reveal directory, path does not exist: {target_dir}")
        return False

    # 1. Directly invoke installed file manager to avoid hijacked inode/directory associations
    if shutil.which("nautilus"):
        try:
            cmd = ["nautilus", "--select", abs_path] if is_file else ["nautilus", target_dir]
            subprocess.Popen(cmd)
            return True
        except Exception as e:
            logger.debug(f"Failed to launch nautilus: {e}")

    if shutil.which("dolphin"):
        try:
            cmd = ["dolphin", "--select", abs_path] if is_file else ["dolphin", target_dir]
            subprocess.Popen(cmd)
            return True
        except Exception as e:
            logger.debug(f"Failed to launch dolphin: {e}")

    if shutil.which("nemo"):
        try:
            cmd = ["nemo", "--no-desktop", abs_path] if is_file else ["nemo", target_dir]
            subprocess.Popen(cmd)
            return True
        except Exception as e:
            logger.debug(f"Failed to launch nemo: {e}")

    if shutil.which("thunar"):
        try:
            subprocess.Popen(["thunar", target_dir])
            return True
        except Exception as e:
            logger.debug(f"Failed to launch thunar: {e}")

    for fm in ["pcmanfm", "pcmanfm-qt", "caja", "io.elementary.files"]:
        if shutil.which(fm):
            try:
                subprocess.Popen([fm, target_dir])
                return True
            except Exception as e:
                logger.debug(f"Failed to launch {fm}: {e}")

    # 2. Fallback: xdg-open on directory
    try:
        subprocess.Popen(["xdg-open", target_dir])
        return True
    except Exception as e:
        logger.error(f"xdg-open failed for directory {target_dir}: {e}")
        return False
