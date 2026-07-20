import os
import sys
import json
import platform
import subprocess
import shutil
import urllib.request
import urllib.error
import re


from core.logger import logger
from core.version import VERSION, BUILD, RELEASE_CHANNEL
from core.constants import (
    YT_DLP_PYPI_URL,
    WRITE_TEST_FILE,
    CONFIG_FILE,
    YT_DLP_ENGINE_PARENT_DIR,
    YT_DLP_ENGINE_DIR,
    YT_DLP_ENGINE_BACKUP_DIR,
    YT_DLP_ENGINE_STAGE_DIR
)
from services.config_manager import load_config, save_config


def normalize_version(ver_str):
    try:
        parts = []
        for p in str(ver_str).strip().split('.'):
            digits = re.match(r'^\d+', p)
            if digits:
                parts.append(int(digits.group(0)))
            else:
                parts.append(p)
        return tuple(parts)
    except Exception:
        return (ver_str,)

class DependencyManager:
    def __init__(self):
        self.ffmpeg_cache = None

    def versions(self):
        ytdlp_ver = "Unknown"
        try:
            import yt_dlp
            ytdlp_ver = yt_dlp.version.__version__
        except Exception as e:
            logger.error(f"Failed to get yt-dlp version: {e}")

        return {
            "bemudex": {
                "version": VERSION,
                "build": BUILD,
                "release_channel": RELEASE_CHANNEL
            },
            "ytdlp": {
                "version": ytdlp_ver
            }
        }

    def detect(self, force_recheck=False):
        if not force_recheck and self.ffmpeg_cache is not None:
            return self.ffmpeg_cache

        # 1. Check custom path in config first
        config = load_config()
        custom_path = config.get("ffmpeg_path", "")
        if custom_path and os.path.exists(custom_path):
            ver = self._probe_ffmpeg(custom_path)
            if ver:
                self.ffmpeg_cache = {"installed": True, "version": ver, "path": custom_path}
                return self.ffmpeg_cache
            else:
                logger.warning(f"Custom FFmpeg path in config is invalid: {custom_path}")

        # 2. Check bundled check (similar to downloader.py get_ffmpeg_path)
        if getattr(sys, 'frozen', False):
            binary = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
            bundled_path = os.path.join(sys._MEIPASS, binary)
            if os.path.exists(bundled_path):
                ver = self._probe_ffmpeg(bundled_path)
                if ver:
                    self.ffmpeg_cache = {"installed": True, "version": ver, "path": bundled_path}
                    return self.ffmpeg_cache

        # 3. Check system PATH
        system_ffmpeg = shutil.which('ffmpeg')
        if system_ffmpeg:
            ver = self._probe_ffmpeg(system_ffmpeg)
            if ver:
                self.ffmpeg_cache = {"installed": True, "version": ver, "path": system_ffmpeg}
                return self.ffmpeg_cache

        self.ffmpeg_cache = {"installed": False, "version": None, "path": None}
        return self.ffmpeg_cache

    def _probe_ffmpeg(self, path):
        try:
            res = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                match = re.search(r'ffmpeg version\s+([^\s,]+)', res.stdout)
                if match:
                    return match.group(1)
                first_line = res.stdout.split('\n')[0]
                return first_line.strip()
        except Exception as e:
            logger.error(f"Probing FFmpeg failed at {path}: {e}")
        return None

    def check(self):
        logger.info("Checking for yt-dlp updates...")
        try:
            # We treat this request directly as the connectivity check
            req = urllib.request.Request(
                YT_DLP_PYPI_URL,
                headers={"User-Agent": f"Bemudex/{VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                latest_version = data["info"]["version"]

            installed_version = self.versions()["ytdlp"]["version"]
            installed_norm = normalize_version(installed_version)
            latest_norm = normalize_version(latest_version)
            update_available = installed_norm < latest_norm
            logger.info(f"yt-dlp version check: installed={installed_version} ({installed_norm}), latest={latest_version} ({latest_norm}), update_available={update_available}")
            return {
                "status": "success",
                "installed": installed_version,
                "latest": latest_version,
                "update_available": update_available
            }
        except urllib.error.URLError as e:
            logger.warning(f"yt-dlp update check unreachable (URLError): {e}")
            return {
                "status": "error",
                "message": "Update server could not be reached. Please check your internet connection."
            }
        except Exception as e:
            logger.error(f"yt-dlp update check failed: {e}")
            return {
                "status": "error",
                "message": f"Unable to check for updates: {str(e)}"
            }

    def update(self):
        logger.info("Starting yt-dlp update process...")
        try:
            import yt_dlp
            current_version = yt_dlp.version.__version__
        except Exception as e:
            logger.error(f"Could not check currently loaded yt-dlp version: {e}")
            current_version = "Unknown"

        latest_version = None
        wheel_url = None
        try:
            req = urllib.request.Request(
                YT_DLP_PYPI_URL,
                headers={"User-Agent": f"Bemudex/{VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                latest_version = data["info"]["version"]
                for item in data.get("urls", []):
                    if item.get("packagetype") == "bdist_wheel":
                        wheel_url = item.get("url")
                        break
        except Exception as e:
            logger.error(f"Failed to fetch PyPI metadata during update: {e}")
            return {
                "status": "error",
                "message": f"Failed to check for updates: could not reach update server ({str(e)})"
            }

        if not latest_version:
            return {
                "status": "error",
                "message": "Failed to resolve latest yt-dlp version from PyPI metadata."
            }

        # Compare currently active version against latest version
        if current_version != "Unknown":
            if normalize_version(current_version) >= normalize_version(latest_version):
                logger.info(f"yt-dlp is already up to date (current={current_version}, latest={latest_version})")
                return {
                    "status": "up_to_date",
                    "message": f"yt-dlp is already up to date (version {current_version}).",
                    "version": current_version
                }

        if not wheel_url:
            return {
                "status": "error",
                "message": "No wheel package distribution found on PyPI for the latest version."
            }

        import zipfile
        import io

        try:
            logger.info(f"Downloading yt-dlp wheel version {latest_version} from {wheel_url}...")
            req_wheel = urllib.request.Request(
                wheel_url,
                headers={"User-Agent": f"Bemudex/{VERSION}"}
            )
            with urllib.request.urlopen(req_wheel, timeout=30) as res:
                wheel_data = res.read()
        except Exception as e:
            logger.error(f"Failed to download wheel: {e}")
            return {
                "status": "error",
                "message": f"Failed to download package updates: {str(e)}"
            }

        try:
            logger.info("Extracting yt-dlp package into staging folder...")
            with zipfile.ZipFile(io.BytesIO(wheel_data)) as z:
                if os.path.exists(YT_DLP_ENGINE_STAGE_DIR):
                    shutil.rmtree(YT_DLP_ENGINE_STAGE_DIR)
                os.makedirs(YT_DLP_ENGINE_STAGE_DIR)
                
                members_to_extract = [m for m in z.namelist() if m.startswith('yt_dlp/')]
                if not members_to_extract:
                    raise Exception("Missing 'yt_dlp' folder inside PyPI wheel package.")
                    
                z.extractall(path=YT_DLP_ENGINE_STAGE_DIR, members=members_to_extract)
                
                staged_pkg_dir = os.path.join(YT_DLP_ENGINE_STAGE_DIR, "yt_dlp")
                if not os.path.exists(staged_pkg_dir):
                    raise Exception("Failed to locate extracted 'yt_dlp' folder in staging.")
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            if os.path.exists(YT_DLP_ENGINE_STAGE_DIR):
                try:
                    shutil.rmtree(YT_DLP_ENGINE_STAGE_DIR)
                except Exception:
                    pass
            return {
                "status": "error",
                "message": f"Extraction of update package failed: {str(e)}"
            }

        logger.info("Verifying staged yt-dlp engine in-process...")
        try:
            # Save currently loaded modules associated with yt_dlp
            saved_modules = {k: v for k, v in list(sys.modules.items()) if k == 'yt_dlp' or k.startswith('yt_dlp.')}
            
            # Temporarily remove them from sys.modules
            for k in saved_modules:
                sys.modules.pop(k, None)
                
            # Add the staging parent directory to sys.path at position 0
            sys.path.insert(0, YT_DLP_ENGINE_STAGE_DIR)
            
            try:
                import yt_dlp
                verified_version = yt_dlp.version.__version__
                logger.info(f"In-process verification passed: imported yt-dlp version {verified_version} successfully.")
            finally:
                # Clean up sys.path
                if YT_DLP_ENGINE_STAGE_DIR in sys.path:
                    sys.path.remove(YT_DLP_ENGINE_STAGE_DIR)
                
                # Clean up any newly loaded staging modules from sys.modules
                for k in list(sys.modules.keys()):
                    if k == 'yt_dlp' or k.startswith('yt_dlp.'):
                        sys.modules.pop(k, None)
                
                # Restore the original cached modules
                sys.modules.update(saved_modules)
        except Exception as e:
            logger.error(f"Staged yt-dlp validation failed: {e}")
            if os.path.exists(YT_DLP_ENGINE_STAGE_DIR):
                try:
                    shutil.rmtree(YT_DLP_ENGINE_STAGE_DIR)
                except Exception:
                    pass
            return {
                "status": "error",
                "message": f"Validation of the downloaded package failed: {str(e)}"
            }

        try:
            if os.path.exists(YT_DLP_ENGINE_DIR):
                if os.path.exists(YT_DLP_ENGINE_BACKUP_DIR):
                    shutil.rmtree(YT_DLP_ENGINE_BACKUP_DIR)
                shutil.move(YT_DLP_ENGINE_DIR, YT_DLP_ENGINE_BACKUP_DIR)
                logger.info("Existing user engine moved to backup.")

            os.makedirs(YT_DLP_ENGINE_PARENT_DIR, exist_ok=True)
            shutil.move(staged_pkg_dir, YT_DLP_ENGINE_DIR)
            logger.info(f"Updated engine installed successfully at {YT_DLP_ENGINE_DIR}")

            if os.path.exists(YT_DLP_ENGINE_STAGE_DIR):
                shutil.rmtree(YT_DLP_ENGINE_STAGE_DIR)
                
            return {
                "status": "success",
                "message": f"yt-dlp has been updated to version {latest_version}. Please restart Bemudex to apply the update.",
                "version": latest_version
            }
        except Exception as e:
            logger.error(f"Installation/Swap failed: {e}")
            if os.path.exists(YT_DLP_ENGINE_BACKUP_DIR) and not os.path.exists(YT_DLP_ENGINE_DIR):
                try:
                    shutil.copytree(YT_DLP_ENGINE_BACKUP_DIR, YT_DLP_ENGINE_DIR)
                    logger.info("Restored current engine from backup after failed swap.")
                except Exception as ex:
                    logger.error(f"Failed to restore backup engine: {ex}")
            return {
                "status": "error",
                "message": f"Failed to install package update: {str(e)}"
            }

    def reset(self):
        logger.info("Resetting dependency configuration...")
        config = load_config()
        if "ffmpeg_path" in config:
            del config["ffmpeg_path"]
            save_config(config)
            logger.info("Custom FFmpeg path removed from configuration.")
        else:
            logger.info("No custom FFmpeg path was configured.")
        
        # Clean up user-installed yt-dlp override engine folder as part of the reset
        if os.path.exists(YT_DLP_ENGINE_PARENT_DIR):
            try:
                shutil.rmtree(YT_DLP_ENGINE_PARENT_DIR)
                logger.info("User-installed yt-dlp engine override removed.")
            except Exception as e:
                logger.error(f"Failed to remove user-installed engine on reset: {e}")

        # Re-run detection
        detection = self.detect(force_recheck=True)
        logger.info(f"Re-run detection results: {detection}")
        return detection

    def diagnostics(self, downloads_folder, current_theme="dark"):
        logger.info("Generating diagnostics report...")
        
        # Check folder write permission
        folder_writable = False
        folder_writable_reason = "Writable"
        if downloads_folder and os.path.exists(downloads_folder):
            temp_file = os.path.join(downloads_folder, WRITE_TEST_FILE)
            try:
                with open(temp_file, "w") as f:
                    f.write("test")
                folder_writable = True
            except Exception as e:
                folder_writable_reason = f"Read-Only / Denied: {str(e)}"
                logger.warning(f"Download folder {downloads_folder} is not writable: {e}")
            finally:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
        else:
            folder_writable_reason = "Directory does not exist"
            logger.warning(f"Download folder {downloads_folder} does not exist.")

        # Internet check (PyPI reachability status)
        internet_status = "Connected"
        try:
            req = urllib.request.Request(
                YT_DLP_PYPI_URL,
                headers={"User-Agent": f"Bemudex/{VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=2) as response:
                pass
        except Exception as e:
            internet_status = f"Disconnected / Unreachable ({str(e)})"

        ffmpeg_info = self.detect()
        ytdlp_ver = self.versions()["ytdlp"]["version"]

        return {
            "bemudex_version": VERSION,
            "build_number": BUILD,
            "release_channel": RELEASE_CHANNEL,
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python_version": sys.version.split()[0],
            "downloads_folder": downloads_folder or "Not Configured",
            "folder_writable": folder_writable,
            "folder_writable_status": folder_writable_reason,
            "ytdlp_version": ytdlp_ver,
            "ffmpeg_version": ffmpeg_info.get("version") or "Not Installed",
            "ffmpeg_path": ffmpeg_info.get("path") or "None",
            "config_file_location": CONFIG_FILE,
            "current_theme": current_theme,
            "backend_status": "running",
            "internet_status": internet_status
        }
