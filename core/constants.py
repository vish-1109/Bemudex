import os

# Configuration and history file locations
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".bemudex_config.json")
HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".bemudex_history.json")

# PyPI endpoint for yt-dlp version checks and connectivity checks
YT_DLP_PYPI_URL = "https://pypi.org/pypi/yt-dlp/json"

# Sentinel file names written to folders for testing write permissions / temp use
WRITE_TEST_FILE = ".bemudex_write_test"
CUSTOM_COVER_PREFIX = ".bemudex_custom_cover_"

# History limits
HISTORY_LIMIT = 100
HISTORY_DEBOUNCE_DELAY = 0.5  # seconds

# Self-updating yt-dlp engine directories
YT_DLP_ENGINE_PARENT_DIR = os.path.join(os.path.expanduser("~"), ".bemudex", "engine")
YT_DLP_ENGINE_DIR = os.path.join(YT_DLP_ENGINE_PARENT_DIR, "yt_dlp")
YT_DLP_ENGINE_BACKUP_DIR = os.path.join(YT_DLP_ENGINE_PARENT_DIR, "yt_dlp_backup")
YT_DLP_ENGINE_STAGE_DIR = os.path.join(YT_DLP_ENGINE_PARENT_DIR, "temp_stage")

