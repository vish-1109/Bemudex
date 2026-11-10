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


def get_default_video_folder() -> str:
    base = get_default_download_folder()
    return os.path.join(base, "Bemudex", "Videos")


def get_default_audio_folder() -> str:
    base = get_default_download_folder()
    return os.path.join(base, "Bemudex", "Audio")


def load_video_folder() -> str:
    try:
        config = load_config()
        folder = config.get("video_folder", "")
        if folder:
            return folder
    except Exception as e:
        logger.error(f"Error loading video folder: {e}")
    return get_default_video_folder()


def save_video_folder(folder: str):
    try:
        config = load_config()
        config["video_folder"] = folder
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving video folder: {e}")


def load_audio_folder() -> str:
    try:
        config = load_config()
        folder = config.get("audio_folder", "")
        if folder:
            return folder
    except Exception as e:
        logger.error(f"Error loading audio folder: {e}")
    return get_default_audio_folder()


def save_audio_folder(folder: str):
    try:
        config = load_config()
        config["audio_folder"] = folder
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving audio folder: {e}")


def load_last_folder():
    return load_video_folder()


def save_last_folder(folder):
    save_video_folder(folder)


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


def load_cookies_source() -> str:
    try:
        config = load_config()
        src = config.get("cookies_source", "none")
        if src in ["none", "firefox", "chrome", "brave", "chromium", "edge", "file"]:
            return src
    except Exception as e:
        logger.error(f"Error loading cookies_source: {e}")
    return "none"


def save_cookies_source(source: str):
    try:
        config = load_config()
        config["cookies_source"] = str(source)
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving cookies_source: {e}")


def load_cookies_file() -> str:
    try:
        config = load_config()
        return str(config.get("cookies_file", ""))
    except Exception as e:
        logger.error(f"Error loading cookies_file: {e}")
    return ""


def save_cookies_file(file_path: str):
    try:
        config = load_config()
        config["cookies_file"] = str(file_path)
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving cookies_file: {e}")


def load_crop_artwork() -> bool:
    try:
        config = load_config()
        return bool(config.get("crop_artwork", True))
    except Exception as e:
        logger.error(f"Error loading crop_artwork: {e}")
    return True


def save_crop_artwork(enabled: bool):
    try:
        config = load_config()
        config["crop_artwork"] = bool(enabled)
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving crop_artwork: {e}")


def load_sponsorblock_enabled() -> bool:
    try:
        config = load_config()
        return bool(config.get("sponsorblock_enabled", False))
    except Exception as e:
        logger.error(f"Error loading sponsorblock_enabled: {e}")
    return False


def save_sponsorblock_enabled(enabled: bool):
    try:
        config = load_config()
        config["sponsorblock_enabled"] = bool(enabled)
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving sponsorblock_enabled: {e}")


def load_compatibility_mode() -> bool:
    try:
        config = load_config()
        return bool(config.get("compatibility_mode", False))
    except Exception as e:
        logger.error(f"Error loading compatibility_mode: {e}")
    return False


def save_compatibility_mode(enabled: bool):
    try:
        config = load_config()
        config["compatibility_mode"] = bool(enabled)
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving compatibility_mode: {e}")


def load_subtitle_languages() -> str:
    try:
        config = load_config()
        return str(config.get("subtitle_languages", "en, en-US, en-GB"))
    except Exception as e:
        logger.error(f"Error loading subtitle_languages: {e}")
    return "en, en-US, en-GB"


def save_subtitle_languages(langs: str):
    try:
        config = load_config()
        config["subtitle_languages"] = str(langs).strip()
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving subtitle_languages: {e}")


def load_auto_subtitles() -> bool:
    try:
        config = load_config()
        return bool(config.get("auto_subtitles", True))
    except Exception as e:
        logger.error(f"Error loading auto_subtitles: {e}")
    return True


def save_auto_subtitles(enabled: bool):
    try:
        config = load_config()
        config["auto_subtitles"] = bool(enabled)
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving auto_subtitles: {e}")


def load_engine_channel() -> str:
    try:
        config = load_config()
        ch = config.get("engine_channel", "nightly")
        if ch in ["stable", "nightly"]:
            return ch
    except Exception as e:
        logger.error(f"Error loading engine_channel: {e}")
    return "nightly"


def save_engine_channel(channel: str):
    try:
        config = load_config()
        config["engine_channel"] = str(channel).lower()
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving engine_channel: {e}")


def load_desktop_notifications() -> bool:
    try:
        config = load_config()
        return bool(config.get("desktop_notifications", True))
    except Exception as e:
        logger.error(f"Error loading desktop_notifications: {e}")
        return True


def save_desktop_notifications(enabled: bool):
    try:
        config = load_config()
        config["desktop_notifications"] = bool(enabled)
        save_config(config)
    except Exception as e:
        logger.error(f"Error saving desktop_notifications: {e}")







