import os
import logging
from logging.handlers import RotatingFileHandler
import urllib.parse

# Setup directory and path
LOG_DIR = os.path.join(os.path.expanduser("~"), ".bemudex", "logs")
try:
    os.makedirs(LOG_DIR, exist_ok=True)
except Exception:
    pass

LOG_FILE = os.path.join(LOG_DIR, "bemudex.log")

# Setup logger instance
logger = logging.getLogger("bemudex")
logger.setLevel(logging.INFO)

# Prevent duplicate handlers if re-imported
if not logger.handlers:
    # Formatter
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Rotating File Handler (1MB limit, 3 backups)
    try:
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1024*1024, backupCount=3, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to initialize file logger: {e}")

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def sanitize_url(url_str):
    if not url_str:
        return ""
    try:
        parsed = urllib.parse.urlparse(str(url_str))
        if parsed.scheme and parsed.netloc:
            # Scrub query parameters and fragments
            return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    except Exception:
        pass
    return "[URL Sanitized]"

def sanitize_msg(msg):
    if not isinstance(msg, str):
        return str(msg)
    words = msg.split()
    sanitized_words = []
    for w in words:
        if w.startswith("http://") or w.startswith("https://"):
            # Strip trailing punctuation
            clean_url = w.rstrip(',.()[]{}'  )
            suffix = w[len(clean_url):]
            sanitized_words.append(sanitize_url(clean_url) + suffix)
        else:
            sanitized_words.append(w)
    return " ".join(sanitized_words)

def make_sanitized_wrapper(original_func):
    def wrapper(msg, *args, **kwargs):
        return original_func(sanitize_msg(msg), *args, **kwargs)
    return wrapper

logger.info = make_sanitized_wrapper(logger.info)
logger.warning = make_sanitized_wrapper(logger.warning)
logger.error = make_sanitized_wrapper(logger.error)
logger.exception = make_sanitized_wrapper(logger.exception)
