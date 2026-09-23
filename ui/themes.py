"""Theme definitions for Bemudex 3.0 Native Qt.

Migrated from existing Bemudex themes:
- Onyx Dark (Pitch Black)
- Minimal Light
- Creole Matcha (Creole Brown & Yellow Green)
- Lavender Tonic (Champion Blue & Lavender)
- Masterpiece Red (Velvet Red & Dirty White)
- Imperial Blue (Cobalt & White)
"""

from dataclasses import dataclass
from PyQt6.QtGui import QPalette, QColor


@dataclass(frozen=True)
class Theme:
    id: str
    name: str
    description: str

    # Backgrounds
    bg_primary: str
    bg_sidebar: str
    bg_card: str
    bg_card_hover: str
    bg_input: str
    bg_input_focus: str
    bg_panel: str
    bg_elevated: str

    # Text
    text_primary: str
    text_secondary: str
    text_muted: str

    # Accent
    accent: str
    accent_hover: str
    accent_text: str
    accent_subtle: str
    accent_active_bg: str

    # Borders
    border: str
    border_subtle: str
    border_focus: str
    border_active: str

    # Badges & Buttons
    badge_bg: str
    badge_text: str
    btn_secondary_bg: str
    btn_secondary_hover: str
    btn_secondary_text: str

    # Progress & Scrollbars
    progress_bg: str
    progress_chunk: str
    scrollbar_thumb: str
    scrollbar_hover: str

    # Status
    success: str = "#10b981"
    success_bg: str = "rgba(16, 185, 129, 0.12)"
    warning: str = "#f59e0b"
    warning_bg: str = "rgba(245, 158, 11, 0.12)"
    error: str = "#ef4444"
    error_bg: str = "rgba(239, 68, 68, 0.12)"

    is_dark: bool = True


THEMES = {
    "dark": Theme(
        id="dark",
        name="Onyx Dark",
        description="Pitch Black monochrome modern theme",
        bg_primary="#050505",
        bg_sidebar="#0a0a0a",
        bg_card="#0e0e0e",
        bg_card_hover="#141414",
        bg_input="#0f0f0f",
        bg_input_focus="#161616",
        bg_panel="#080808",
        bg_elevated="#181818",
        text_primary="#f5f5f5",
        text_secondary="#aaaaaa",
        text_muted="#666666",
        accent="#ffffff",
        accent_hover="#e5e5e5",
        accent_text="#050505",
        accent_subtle="rgba(255, 255, 255, 0.08)",
        accent_active_bg="rgba(255, 255, 255, 0.08)",
        border="rgba(255, 255, 255, 0.07)",
        border_subtle="rgba(255, 255, 255, 0.04)",
        border_focus="rgba(255, 255, 255, 0.28)",
        border_active="rgba(255, 255, 255, 0.45)",
        badge_bg="rgba(255, 255, 255, 0.06)",
        badge_text="#cccccc",
        btn_secondary_bg="#161616",
        btn_secondary_hover="#222222",
        btn_secondary_text="#cccccc",
        progress_bg="rgba(255, 255, 255, 0.08)",
        progress_chunk="#ffffff",
        scrollbar_thumb="rgba(255, 255, 255, 0.15)",
        scrollbar_hover="rgba(255, 255, 255, 0.30)",
        is_dark=True,
    ),
    "light": Theme(
        id="light",
        name="Minimal Light",
        description="Clean, high-contrast light theme",
        bg_primary="#f8f8f9",
        bg_sidebar="#f0f0f2",
        bg_card="#ffffff",
        bg_card_hover="#f4f4f6",
        bg_input="#f0f0f3",
        bg_input_focus="#e4e4e7",
        bg_panel="#f2f2f5",
        bg_elevated="#ffffff",
        text_primary="#18181b",
        text_secondary="#52525b",
        text_muted="#888891",
        accent="#18181b",
        accent_hover="#27272a",
        accent_text="#ffffff",
        accent_subtle="rgba(0, 0, 0, 0.05)",
        accent_active_bg="rgba(0, 0, 0, 0.08)",
        border="rgba(0, 0, 0, 0.09)",
        border_subtle="rgba(0, 0, 0, 0.05)",
        border_focus="rgba(0, 0, 0, 0.28)",
        border_active="rgba(0, 0, 0, 0.45)",
        badge_bg="rgba(0, 0, 0, 0.06)",
        badge_text="#3f3f46",
        btn_secondary_bg="#e4e4e7",
        btn_secondary_hover="#d4d4d8",
        btn_secondary_text="#18181b",
        progress_bg="rgba(0, 0, 0, 0.08)",
        progress_chunk="#18181b",
        scrollbar_thumb="rgba(0, 0, 0, 0.18)",
        scrollbar_hover="rgba(0, 0, 0, 0.35)",
        is_dark=False,
    ),
    "creole-matcha": Theme(
        id="creole-matcha",
        name="Creole Matcha",
        description="Creole Brown & vibrant Yellow Green",
        bg_primary="#1F0E06",
        bg_sidebar="#160a04",
        bg_card="#291308",
        bg_card_hover="#351a0c",
        bg_input="#261207",
        bg_input_focus="#34190b",
        bg_panel="#1a0c05",
        bg_elevated="#30170a",
        text_primary="#f7f1e1",
        text_secondary="#c4b39d",
        text_muted="#8c7764",
        accent="#C6E385",
        accent_hover="#d5f299",
        accent_text="#1F0E06",
        accent_subtle="rgba(198, 227, 133, 0.10)",
        accent_active_bg="rgba(198, 227, 133, 0.12)",
        border="rgba(198, 227, 133, 0.12)",
        border_subtle="rgba(198, 227, 133, 0.06)",
        border_focus="rgba(198, 227, 133, 0.35)",
        border_active="rgba(198, 227, 133, 0.55)",
        badge_bg="rgba(198, 227, 133, 0.08)",
        badge_text="#c4b39d",
        btn_secondary_bg="#2e160a",
        btn_secondary_hover="#3d1e0e",
        btn_secondary_text="#e0d5c3",
        progress_bg="rgba(198, 227, 133, 0.12)",
        progress_chunk="#C6E385",
        scrollbar_thumb="rgba(198, 227, 133, 0.20)",
        scrollbar_hover="rgba(198, 227, 133, 0.40)",
        is_dark=True,
    ),
    "lavender-tonic": Theme(
        id="lavender-tonic",
        name="Lavender Tonic",
        description="Champion Blue & Lavender Tonic",
        bg_primary="#151130",
        bg_sidebar="#0f0c24",
        bg_card="#1e1945",
        bg_card_hover="#29225c",
        bg_input="#1a153c",
        bg_input_focus="#28215c",
        bg_panel="#110e28",
        bg_elevated="#251f54",
        text_primary="#f7f5ff",
        text_secondary="#c1b8eb",
        text_muted="#867cb5",
        accent="#C8BEFA",
        accent_hover="#ded6ff",
        accent_text="#151130",
        accent_subtle="rgba(200, 190, 250, 0.10)",
        accent_active_bg="rgba(200, 190, 250, 0.12)",
        border="rgba(200, 190, 250, 0.12)",
        border_subtle="rgba(200, 190, 250, 0.06)",
        border_focus="rgba(200, 190, 250, 0.35)",
        border_active="rgba(200, 190, 250, 0.55)",
        badge_bg="rgba(200, 190, 250, 0.08)",
        badge_text="#c1b8eb",
        btn_secondary_bg="#231d52",
        btn_secondary_hover="#30276d",
        btn_secondary_text="#e2dcff",
        progress_bg="rgba(200, 190, 250, 0.12)",
        progress_chunk="#C8BEFA",
        scrollbar_thumb="rgba(200, 190, 250, 0.20)",
        scrollbar_hover="rgba(200, 190, 250, 0.40)",
        is_dark=True,
    ),
    "masterpiece-red": Theme(
        id="masterpiece-red",
        name="Masterpiece Red",
        description="Velvet Red & Dirty White",
        bg_primary="#240d14",
        bg_sidebar="#1a080e",
        bg_card="#3d1622",
        bg_card_hover="#501d2c",
        bg_input="#33121c",
        bg_input_focus="#491a28",
        bg_panel="#1e0a10",
        bg_elevated="#4a1a29",
        text_primary="#EFE9E9",
        text_secondary="#c7b2b8",
        text_muted="#8c7078",
        accent="#EFE9E9",
        accent_hover="#ffffff",
        accent_text="#240d14",
        accent_subtle="rgba(239, 233, 233, 0.10)",
        accent_active_bg="rgba(239, 233, 233, 0.12)",
        border="rgba(239, 233, 233, 0.12)",
        border_subtle="rgba(239, 233, 233, 0.06)",
        border_focus="rgba(239, 233, 233, 0.35)",
        border_active="rgba(239, 233, 233, 0.55)",
        badge_bg="rgba(239, 233, 233, 0.08)",
        badge_text="#c7b2b8",
        btn_secondary_bg="#441826",
        btn_secondary_hover="#582032",
        btn_secondary_text="#ede3e6",
        progress_bg="rgba(239, 233, 233, 0.12)",
        progress_chunk="#EFE9E9",
        scrollbar_thumb="rgba(239, 233, 233, 0.20)",
        scrollbar_hover="rgba(239, 233, 233, 0.40)",
        is_dark=True,
    ),
    "imperial-blue": Theme(
        id="imperial-blue",
        name="Imperial Blue",
        description="Cobalt Blue & White Convolvulus",
        bg_primary="#06103b",
        bg_sidebar="#040a26",
        bg_card="#0a1d63",
        bg_card_hover="#0f2885",
        bg_input="#08174f",
        bg_input_focus="#0f2885",
        bg_panel="#050d30",
        bg_elevated="#0e257a",
        text_primary="#F5F2F3",
        text_secondary="#d1daf5",
        text_muted="#8ca0d9",
        accent="#F5F2F3",
        accent_hover="#ffffff",
        accent_text="#021F94",
        accent_subtle="rgba(245, 242, 243, 0.12)",
        accent_active_bg="rgba(245, 242, 243, 0.12)",
        border="rgba(245, 242, 243, 0.14)",
        border_subtle="rgba(245, 242, 243, 0.08)",
        border_focus="rgba(245, 242, 243, 0.35)",
        border_active="rgba(245, 242, 243, 0.60)",
        badge_bg="rgba(245, 242, 243, 0.08)",
        badge_text="#d1daf5",
        btn_secondary_bg="#0d2479",
        btn_secondary_hover="#12309e",
        btn_secondary_text="#eaeffa",
        progress_bg="rgba(245, 242, 243, 0.14)",
        progress_chunk="#F5F2F3",
        scrollbar_thumb="rgba(245, 242, 243, 0.22)",
        scrollbar_hover="rgba(245, 242, 243, 0.45)",
        is_dark=True,
    ),
}

DEFAULT_THEME_ID = "dark"


def get_theme(theme_id: str) -> Theme:
    """Returns the Theme matching theme_id or falls back to DEFAULT_THEME_ID."""
    return THEMES.get(theme_id, THEMES[DEFAULT_THEME_ID])


def get_available_themes() -> list[tuple[str, str]]:
    """Returns a list of (theme_id, display_name) for UI selectors."""
    return [(t.id, t.name) for t in THEMES.values()]


def create_theme_palette(theme: Theme) -> QPalette:
    """Builds a QPalette aligned with the theme for native Qt widgets and dialogs."""
    palette = QPalette()

    # Window / Background
    window_color = QColor(theme.bg_primary)
    base_color = QColor(theme.bg_card)
    text_color = QColor(theme.text_primary)
    btn_color = QColor(theme.btn_secondary_bg)
    highlight_color = QColor(theme.accent)
    highlighted_text = QColor(theme.accent_text)

    palette.setColor(QPalette.ColorRole.Window, window_color)
    palette.setColor(QPalette.ColorRole.WindowText, text_color)
    palette.setColor(QPalette.ColorRole.Base, base_color)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme.bg_input))
    palette.setColor(QPalette.ColorRole.ToolTipBase, base_color)
    palette.setColor(QPalette.ColorRole.ToolTipText, text_color)
    palette.setColor(QPalette.ColorRole.Text, text_color)
    palette.setColor(QPalette.ColorRole.Button, btn_color)
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme.btn_secondary_text))
    palette.setColor(QPalette.ColorRole.Highlight, highlight_color)
    palette.setColor(QPalette.ColorRole.HighlightedText, highlighted_text)

    return palette
