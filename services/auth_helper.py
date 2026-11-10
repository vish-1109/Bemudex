import re

_BOT_AUTH_REGEX = re.compile(
    r"\b(bot|bots|recaptcha|captcha|429)\b"
    r"|sign in to confirm"
    r"|sign in to view"
    r"|sign in if you"
    r"|login required"
    r"|private video"
    r"|this video requires payment"
    r"|use --cookies"
    r"|cookies-from-browser"
    r"|enable browser cookies"
    r"|cookies in settings"
    r"|too many requests",
    re.IGNORECASE
)


def is_bot_or_auth_error(err_msg: str) -> bool:
    """
    Detects if an error message from yt-dlp indicates YouTube bot-check,
    sign-in requirement, age-gate, or 429 rate limit.
    """
    if not err_msg:
        return False
    return bool(_BOT_AUTH_REGEX.search(str(err_msg)))
