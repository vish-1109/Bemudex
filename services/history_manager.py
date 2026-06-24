import os
import json

from core.constants import HISTORY_FILE


from core.logger import logger

def get_file_size_str(filepath):
    try:
        size_bytes = os.path.getsize(filepath)
        if size_bytes > 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes > 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes} B"
    except Exception:
        return "Unknown size"


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load history from {HISTORY_FILE}: {e}")
    return []


def save_history(history):
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f)
    except Exception as e:
        logger.error(f"Failed to save history to {HISTORY_FILE}: {e}")

