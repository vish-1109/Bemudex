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
