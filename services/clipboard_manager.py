import sys
import subprocess

from core.logger import logger


def get_clipboard_text():
    try:
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard:
            text = clipboard.text()
            if isinstance(text, str):
                return text.strip()
    except Exception as e:
        logger.error(f"PyQt6 native clipboard reading failed: {e}")

    root = None
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        if isinstance(text, str):
            return text.strip()
    except Exception:
        pass
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass

    try:
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                startupinfo=startupinfo,
                timeout=1
            )
            return res.stdout.strip()
        elif sys.platform == "darwin":
            res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=1)
            return res.stdout.strip()
        else:
            for tool in [["xclip", "-selection", "clipboard", "-o"], ["xsel", "-o", "-b"]]:
                try:
                    res = subprocess.run(tool, capture_output=True, text=True, timeout=1)
                    if res.returncode == 0:
                        return res.stdout.strip()
                except Exception:
                    continue
    except Exception:
        pass
    return ""


def read_clipboard():
    try:
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard:
            return clipboard.text()
    except Exception as e:
        logger.error(f"Clipboard reading error: {e}")
    return ""


def copy_to_clipboard(text):
    logger.info("copy_to_clipboard called")
    try:
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(str(text))
            logger.info("Text copied to clipboard via PyQt6.")
            return True
    except Exception as e:
        logger.error(f"Failed to copy to clipboard via PyQt6: {e}")
    return False
