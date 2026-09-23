import os
import sys
import json
import threading

from core.logger import logger
from core.constants import CONFIG_FILE

config_lock = threading.Lock()


def get_default_download_folder():
    try:
        if sys.platform == "win32":
            import winreg
            sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                return winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[0]
        else:
            downloads = os.path.join(os.path.expanduser("~"), "Downloads")
            if os.path.exists(downloads):
                return downloads
    except Exception:
        pass
    return os.path.expanduser("~")


def load_config():
    with config_lock:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    content = f.read().strip()
                    if not content:
                        try:
                            with open(CONFIG_FILE, "w") as fw:
                                json.dump({}, fw)
                        except Exception:
                            pass
                        return {}
                    return json.loads(content)
            except Exception as e:
                logger.error(f"Failed to load config (file may be corrupted): {e}")
                try:
                    backup_path = CONFIG_FILE + ".bak"
                    if os.path.exists(backup_path):
                        try:
                            os.remove(backup_path)
                        except Exception:
                            pass
                    if os.path.exists(CONFIG_FILE):
                        os.rename(CONFIG_FILE, backup_path)
                        logger.warning(f"Corrupted config backed up to {backup_path}. Recreating defaults.")
                    with open(CONFIG_FILE, "w") as fw:
                        json.dump({}, fw)
                except Exception as ex:
                    logger.error(f"Failed to backup/recreate config file: {ex}")
        return {}


def save_config(config):
    with config_lock:
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")


def load_last_folder():
    try:
        config = load_config()
        folder = config.get("last_folder", "")
        if folder and os.path.exists(folder):
            return folder
    except Exception as e:
        logger.error(f"Error loading last folder: {e}")
    return get_default_download_folder()


def save_last_folder(folder):
    try:
        config = load_config()
        config["last_folder"] = folder
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving last folder: {e}")


def load_theme():
    try:
        config = load_config()
        return config.get("theme", "dark")
    except Exception as e:
        logger.error(f"Error loading theme from config: {e}")
    return "dark"


def save_theme(theme_name):
    try:
        config = load_config()
        config["theme"] = theme_name
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving theme to config: {e}")


def load_audio_format():
    try:
        config = load_config()
        fmt = config.get("audio_format", "mp3")
        if fmt in ["mp3", "m4a", "flac", "wav", "aac"]:
            return fmt
    except Exception as e:
        logger.error(f"Error loading audio format: {e}")
    return "mp3"


def save_audio_format(audio_fmt):
    try:
        config = load_config()
        config["audio_format"] = audio_fmt
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving audio format: {e}")


def load_ffmpeg_path():
    try:
        config = load_config()
        return config.get("ffmpeg_path", "")
    except Exception as e:
        logger.error(f"Error loading ffmpeg path: {e}")
    return ""


def save_ffmpeg_path(path):
    try:
        config = load_config()
        if path:
            config["ffmpeg_path"] = path
        else:
            config.pop("ffmpeg_path", None)
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving ffmpeg path: {e}")


def load_auto_close_panel() -> bool:
    try:
        config = load_config()
        return bool(config.get("auto_close_panel", False))
    except Exception as e:
        logger.error(f"Error loading auto_close_panel from config: {e}")
    return False


def save_auto_close_panel(enabled: bool):
    try:
        config = load_config()
        config["auto_close_panel"] = bool(enabled)
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving auto_close_panel to config: {e}")


def load_ui_scale() -> int:
    try:
        config = load_config()
        val = int(config.get("ui_scale", 100))
        if val in [90, 100, 110, 125, 150, 175]:
            return val
    except Exception as e:
        logger.error(f"Error loading ui_scale: {e}")
    return 100


def save_ui_scale(scale: int):
    try:
        config = load_config()
        config["ui_scale"] = int(scale)
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving ui_scale: {e}")


def load_check_updates_on_launch() -> bool:
    try:
        config = load_config()
        return bool(config.get("check_updates_on_launch", True))
    except Exception as e:
        logger.error(f"Error loading check_updates_on_launch: {e}")
    return True


def save_check_updates_on_launch(enabled: bool):
    try:
        config = load_config()
        config["check_updates_on_launch"] = bool(enabled)
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving check_updates_on_launch: {e}")
