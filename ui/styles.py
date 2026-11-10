import re
from ui.themes import Theme, get_theme


def get_stylesheet(theme_or_id: str | Theme = "dark", scale: float = 1.0) -> str:
    """Generates the full application Qt stylesheet for the specified theme and UI scale."""
    if isinstance(theme_or_id, Theme):
        t = theme_or_id
    else:
        t = get_theme(theme_or_id)

    css = f"""
* {{
    font-family: Ubuntu, "Segoe UI", sans-serif;
    outline: none;
}}

QMainWindow, QWidget#centralWidget, QStackedWidget#pageStack {{
    background-color: {t.bg_primary};
    color: {t.text_primary};
}}

QScrollArea, QScrollArea > QWidget, QScrollArea QWidget#qt_scrollarea_viewport, QWidget#centerScrollWidget, QWidget#scrollContent, QWidget#centerWidget {{
    background-color: {t.bg_primary};
    background: {t.bg_primary};
    border: none;
}}

/* ── Sidebar ── */
QFrame#sidebarFrame {{
    background-color: {t.bg_sidebar};
    border-right: 1px solid {t.border};
}}

QLabel#sidebarAppName {{
    font-size: 15px;
    font-weight: 700;
    color: {t.text_primary};
    letter-spacing: -0.3px;
}}

QPushButton.sidebar-btn {{
    background-color: transparent;
    color: {t.text_secondary};
    font-size: 13.5px;
    font-weight: 500;
    border: none;
    border-radius: 8px;
    padding: 9px 12px;
    text-align: left;
}}

QPushButton.sidebar-btn:hover {{
    background-color: {t.accent_subtle};
    color: {t.text_primary};
}}

QPushButton.sidebar-btn.active {{
    background-color: {t.accent_active_bg};
    color: {t.text_primary};
    font-weight: 600;
    border-left: 3px solid {t.accent};
    border-top-left-radius: 2px;
    border-bottom-left-radius: 2px;
}}

QPushButton.sidebar-btn-collapsed {{
    background-color: transparent;
    color: {t.text_secondary};
    border: none;
    border-radius: 8px;
    padding: 0px;
    text-align: center;
    min-width: 42px;
    max-width: 42px;
    min-height: 40px;
    max-height: 40px;
}}

QPushButton.sidebar-btn-collapsed:hover {{
    background-color: {t.accent_subtle};
    color: {t.text_primary};
}}

QPushButton.sidebar-btn-collapsed.active {{
    background-color: {t.accent_active_bg};
    color: {t.text_primary};
    border-left: 3px solid {t.accent};
    border-top-left-radius: 2px;
    border-bottom-left-radius: 2px;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}}

QPushButton.sidebar-btn:disabled {{
    color: {t.text_muted};
}}

QPushButton#btnSidebarCollapse {{
    background: transparent;
    color: {t.text_secondary};
    border: none;
    font-size: 11px;
}}

QPushButton#btnSidebarCollapse:hover {{
    color: {t.text_primary};
    background: {t.accent_subtle};
    border-radius: 4px;
}}

QLabel#lblComingSoon {{
    font-size: 10px;
    font-weight: 700;
    color: {t.text_muted};
    padding-left: 10px;
}}

QLabel#sidebarBadge {{
    background: transparent;
    color: {t.badge_text};
    font-size: 11.5px;
    font-weight: 600;
    padding: 0 4px;
}}

QFrame#sidebarFooter {{
    border-top: 1px solid {t.border_subtle};
    padding-top: 14px;
}}

QLabel#sidebarStorageLabel {{
    font-size: 10.5px;
    font-weight: 700;
    color: {t.text_muted};
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}

QProgressBar#sidebarStorageBar {{
    background-color: {t.bg_input};
    border: none;
    border-radius: 3px;
    max-height: 5px;
    min-height: 5px;
}}

QProgressBar#sidebarStorageBar::chunk {{
    background-color: {t.accent};
    border-radius: 3px;
}}

QLabel#engineStatusText {{
    font-size: 11.5px;
    color: {t.text_muted};
    line-height: 1.4;
}}

QLabel#engineStatusDot {{
    background-color: {t.success};
    border-radius: 4px;
    min-width: 7px;
    max-width: 7px;
    min-height: 7px;
    max-height: 7px;
}}

QPushButton#btnUpdateEngine {{
    background-color: transparent;
    color: {t.text_secondary};
    border: 1px solid {t.border};
    border-radius: 7px;
    font-size: 11.5px;
    font-weight: 500;
    padding: 0 10px;
    min-height: 34px;
    max-height: 34px;
}}

QPushButton#btnUpdateEngine:hover {{
    background-color: {t.accent_subtle};
    color: {t.text_primary};
    border-color: {t.border_focus};
}}

QPushButton#btnUpdateEngine:disabled {{
    color: {t.text_muted};
}}

QPushButton#btnUpdateEngine[status="update_available"] {{
    background-color: {t.accent};
    color: {t.accent_text};
    border: 1px solid {t.accent};
    font-weight: 600;
}}

QPushButton#btnUpdateEngine[status="update_available"]:hover {{
    background-color: {t.accent_hover};
    border-color: {t.accent_hover};
}}

QPushButton#btnUpdateEngine[status="update_available"]:disabled {{
    background-color: {t.accent};
    color: {t.accent_text};
}}

/* ── Center Content ── */
QWidget#centerWidget {{
    background-color: {t.bg_primary};
}}

QLabel#greetingTitle {{
    font-size: 21px;
    font-weight: 700;
    color: {t.text_primary};
    letter-spacing: -0.4px;
}}

QLabel#greetingSubtitle {{
    font-size: 13px;
    color: {t.text_secondary};
}}

/* ── URL Input Hero ── */
QFrame#urlBarFrame {{
    background-color: {t.bg_input};
    border: 1px solid {t.border};
    border-radius: 12px;
    padding: 4px 8px;
}}

QFrame#urlBarFrame:focus-within {{
    border: 1px solid {t.border_focus};
    background-color: {t.bg_input_focus};
}}

QLineEdit#urlInput {{
    background: transparent;
    border: none;
    color: {t.text_primary};
    font-size: 13.5px;
    padding: 6px;
}}

QLineEdit#urlInput::placeholder {{
    color: {t.text_muted};
}}

QPushButton#btnFetch, QPushButton#btnPaste {{
    background-color: {t.accent};
    color: {t.accent_text};
    font-size: 12.5px;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 6px 14px;
}}

QPushButton#btnFetch:hover, QPushButton#btnPaste:hover {{
    background-color: {t.accent_hover};
}}

QPushButton#btnFetch:disabled {{
    background-color: {t.btn_secondary_bg};
    color: {t.text_muted};
}}

QPushButton#btnClearUrl {{
    background: transparent;
    color: {t.text_muted};
    border: none;
    font-size: 13px;
    padding: 4px 6px;
    border-radius: 4px;
}}

QPushButton#btnClearUrl:hover {{
    color: {t.text_primary};
    background: {t.accent_subtle};
}}

QLabel#urlHintText {{
    font-size: 11.5px;
    color: {t.text_muted};
}}

QLabel#urlHintKbd {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 4px;
    padding: 1px 5px;
    font-size: 10.5px;
    font-weight: 600;
    color: {t.text_secondary};
}}

/* ── Cards & Frames ── */
QFrame.card-frame {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 12px;
}}

/* ── Metadata Preview ── */
QFrame#metaThumbContainer {{
    background-color: {t.bg_input};
    border: 1px solid {t.border};
    border-radius: 8px;
}}

QLabel#metaThumb {{
    background-color: {t.bg_input};
    border-radius: 8px;
}}

QLabel#durationBadge {{
    background-color: rgba(0, 0, 0, 0.80);
    color: #ffffff;
    font-size: 11px;
    font-weight: 700;
    border-radius: 4px;
    padding: 2px 6px;
    letter-spacing: 0.2px;
}}

QLabel#metaTitle {{
    font-size: 15.5px;
    font-weight: 700;
    color: {t.text_primary};
    letter-spacing: -0.2px;
}}

QLabel#metaChannel {{
    font-size: 13.5px;
    font-weight: 500;
    color: {t.text_secondary};
}}

QLabel#metaStats {{
    font-size: 12px;
    font-weight: 400;
    color: {t.text_muted};
}}

/* ── Skeleton Loading ── */
QFrame#skeletonThumb {{
    background-color: {t.bg_card_hover};
    border-radius: 8px;
}}

QFrame.skeleton-bar {{
    background-color: {t.bg_card_hover};
    border-radius: 4px;
}}

QLabel.badge-pill, QFrame.badge-pill {{
    background-color: {t.accent_subtle};
    border: 1px solid {t.border};
    color: {t.text_secondary};
    font-size: 11px;
    font-weight: 600;
    border-radius: 6px;
    padding: 2.5px 8px;
    letter-spacing: 0.2px;
}}

QLabel.badge-pill-accent, QFrame.badge-pill-accent {{
    background-color: {t.accent_active_bg};
    border: 1px solid {t.border_focus};
    color: {t.text_primary};
    font-size: 11px;
    font-weight: 700;
    border-radius: 6px;
    padding: 2.5px 8px;
    letter-spacing: 0.2px;
}}

/* ── Format Switcher Tabs (Segmented Container) ── */
QFrame#formatTabsContainer {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 10px;
    padding: 3px;
}}

QPushButton.format-tab {{
    background: transparent;
    border: none;
    color: {t.text_secondary};
    font-size: 13.5px;
    font-weight: 600;
    border-radius: 6px;
    padding: 7px 18px;
}}

QPushButton.format-tab:hover:!checked {{
    color: {t.text_primary};
    background-color: {t.bg_card_hover};
}}

QPushButton.format-tab.active {{
    background-color: {t.accent_subtle};
    color: {t.text_primary};
    font-weight: 600;
}}

/* ── Section Labels ── */
QLabel.workspace-section-label {{
    font-size: 12.5px;
    font-weight: 600;
    color: {t.text_secondary};
    letter-spacing: 0.4px;
    text-transform: uppercase;
}}

/* ── Quality Cards ── */
QFrame.quality-card {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 10px;
}}

QFrame.quality-card:hover {{
    border-color: {t.border_focus};
    background-color: {t.bg_card_hover};
}}

QFrame.quality-card[active="true"] {{
    border: 1.5px solid {t.accent};
    background-color: {t.accent_active_bg};
}}

QLabel#qualityCardVal {{
    font-size: 14px;
    font-weight: 700;
    color: {t.text_primary};
    letter-spacing: -0.2px;
}}

QLabel#qualityCardSub {{
    font-size: 10px;
    font-weight: 500;
    color: {t.text_secondary};
}}

QLabel#qualityCardSize {{
    font-size: 10px;
    font-weight: 500;
    color: {t.text_muted};
}}

QLabel#qualityPopularBadge {{
    background-color: {t.accent};
    color: {t.accent_text};
    font-size: 8.5px;
    font-weight: 800;
    border-radius: 8px;
    padding: 1.5px 6px;
    letter-spacing: 0.4px;
    text-transform: uppercase;
}}

/* ── Audio Workspace Elements ── */
QFrame#audioCoverContainer {{
    background-color: {t.bg_input};
    border: 1px solid {t.border};
    border-radius: 10px;
}}

QLabel#audioCoverArt {{
    border-radius: 10px;
}}

QLabel#audioCoverBadge {{
    background-color: rgba(0, 0, 0, 0.75);
    color: #ffffff;
    font-size: 8px;
    font-weight: 700;
    border-radius: 4px;
    padding: 2px 4px;
    letter-spacing: 0.8px;
}}

QLabel#audioTagLabel {{
    font-size: 10.5px;
    font-weight: 600;
    color: {t.text_secondary};
    letter-spacing: 0.4px;
    text-transform: uppercase;
}}

QLineEdit#audioTagInput {{
    background-color: {t.bg_input};
    border: 1px solid {t.border};
    color: {t.text_primary};
    font-size: 13px;
    border-radius: 6px;
    padding: 6px 11px;
}}

QLineEdit#audioTagInput:focus {{
    border: 1px solid {t.border_focus};
    background-color: {t.bg_input_focus};
}}

QFrame#audioTogglesContainer, QFrame#videoTogglesContainer {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 10px;
}}

QLabel#audioToggleLabel, QLabel#videoToggleLabel {{
    font-size: 12.5px;
    font-weight: 500;
    color: {t.text_secondary};
}}

QLabel#videoToggleSublabel {{
    font-size: 11px;
    color: {t.text_muted};
}}

QLabel#audioToggleLabelDisabled {{
    font-size: 12.5px;
    font-weight: 500;
    color: {t.text_muted};
}}

QFrame#audioToggleDivider {{
    background-color: {t.border};
    border: none;
}}

/* ── Feature Cards ── */
QFrame.feature-card {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 10px;
}}

QFrame.feature-card:hover {{
    border-color: {t.border_focus};
    background-color: {t.bg_card_hover};
}}

QFrame#featureCardIconBadge {{
    background-color: {t.accent_subtle};
    border: 1px solid {t.border};
    border-radius: 6px;
}}

QLabel#featureCardTitle {{
    font-size: 12.5px;
    font-weight: 700;
    color: {t.text_primary};
}}

QLabel#featureCardDesc {{
    font-size: 11px;
    color: {t.text_muted};
    line-height: 1.45;
}}

/* ── Destination Folder Box ── */
QFrame#folderFrame {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 4px 8px;
}}

QLabel#folderPathLabel {{
    color: {t.text_secondary};
    font-size: 12.5px;
}}

QPushButton#btnBrowse {{
    background-color: {t.btn_secondary_bg};
    border: 1px solid {t.border};
    color: {t.btn_secondary_text};
    font-size: 12px;
    font-weight: 600;
    border-radius: 6px;
    padding: 6px 14px;
}}

QPushButton#btnBrowse:hover {{
    background-color: {t.btn_secondary_hover};
    color: {t.text_primary};
}}

/* ── Primary Action Bar ── */
QPushButton#btnDownload {{
    background-color: {t.accent};
    color: {t.accent_text};
    font-size: 14px;
    font-weight: 700;
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
}}

QPushButton#btnDownload:hover {{
    background-color: {t.accent_hover};
}}

QPushButton#btnDownload:disabled {{
    background-color: {t.bg_elevated};
    color: {t.text_muted};
}}

QPushButton#btnCancel {{
    background-color: {t.btn_secondary_bg};
    border: 1px solid {t.border};
    color: {t.btn_secondary_text};
    font-size: 13.5px;
    font-weight: 500;
    border-radius: 10px;
    padding: 12px 20px;
}}

QPushButton#btnCancel:hover {{
    background-color: {t.btn_secondary_hover};
    color: {t.text_primary};
}}

QPushButton#btnCancel:disabled {{
    background-color: transparent;
    border-color: transparent;
    color: {t.text_muted};
}}

/* ── Right Downloads Panel ── */
QFrame#downloadsPanel {{
    background-color: {t.bg_panel};
    border-left: 1px solid {t.border};
}}

QLabel#panelTitle {{
    font-size: 13.5px;
    font-weight: 700;
    color: {t.text_primary};
}}

QLabel#panelCountPill {{
    background-color: {t.badge_bg};
    color: {t.badge_text};
    font-size: 11px;
    font-weight: 600;
    border-radius: 8px;
    padding: 2px 7px;
}}

QPushButton#btnClearCompleted {{
    background: transparent;
    color: {t.text_muted};
    border: none;
    font-size: 11px;
}}

QPushButton#btnClearCompleted:hover {{
    color: {t.text_primary};
    background: {t.accent_subtle};
    border-radius: 4px;
}}

QLabel#panelSectionHeader {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: {t.text_muted};
    padding-top: 4px;
    padding-bottom: 2px;
}}

/* ── Scroll Area ── */
QScrollArea#downloadsScrollArea, QScrollArea#historyScrollArea, QScrollArea#settingsScrollArea {{
    background: transparent;
    border: none;
}}

QWidget#scrollContent {{
    background: transparent;
}}

QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {t.scrollbar_thumb};
    min-height: 20px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical:hover {{
    background: {t.scrollbar_hover};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* ── Download Card ── */
QFrame#downloadCard {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 10px;
}}

QFrame#downloadCard[status="downloading"] {{
    background-color: {t.bg_card_hover};
    border: 1px solid {t.border_focus};
}}

QFrame#downloadCard[status="finished"] {{
    background-color: {t.bg_card};
    border: 1px solid {t.border_subtle};
}}

QFrame#downloadCard[status="failed"] {{
    background-color: {t.error_bg};
    border: 1px solid {t.error};
}}

QFrame#downloadCard[status="cancelled"] {{
    background-color: {t.bg_card};
    border: 1px solid {t.border_subtle};
}}

QLabel#cardThumbnail {{
    background-color: {t.bg_input};
    color: {t.text_muted};
    border-radius: 4px;
    font-size: 14px;
}}

QLabel#cardTitle {{
    font-size: 12.5px;
    font-weight: 600;
    color: {t.text_primary};
}}

QLabel#cardMeta {{
    font-size: 11px;
    color: {t.text_secondary};
    font-weight: 500;
}}

QLabel#cardBadge {{
    font-size: 10px;
    font-weight: 600;
    color: {t.badge_text};
    background-color: {t.badge_bg};
    border-radius: 4px;
    padding: 1px 5px;
}}

QLabel#cardBadge[status="downloading"] {{
    color: {t.accent};
    background-color: {t.accent_active_bg};
}}

QLabel#cardBadge[status="finished"] {{
    color: {t.success};
    background-color: {t.success_bg};
}}

QLabel#cardBadge[status="failed"] {{
    color: {t.error};
    background-color: {t.error_bg};
}}

QLabel#cardBadge[status="cancelled"] {{
    color: {t.text_muted};
    background-color: {t.badge_bg};
}}

QPushButton#btnCardCancel {{
    background: transparent;
    color: {t.text_muted};
    border: none;
    font-size: 11px;
}}

QPushButton#btnCardCancel:hover {{
    color: {t.text_primary};
    background: {t.accent_subtle};
    border-radius: 4px;
}}

QProgressBar#downloadProgress {{
    background-color: {t.progress_bg};
    border: none;
    border-radius: 3px;
    min-height: 5px;
    max-height: 5px;
    text-align: center;
}}

QProgressBar#downloadProgress::chunk {{
    background-color: {t.progress_chunk};
    border-radius: 2px;
}}

/* QCheckBox acting as a Toggle Switch */
QCheckBox {{
    color: {t.text_secondary};
    font-size: 14px;
    spacing: 12px;
}}
QCheckBox::indicator {{
    width: 36px;
    height: 20px;
    border-radius: 10px;
    background-color: {t.bg_input};
    border: 1px solid {t.border};
}}
QCheckBox::indicator:checked {{
    background-color: {t.accent};
    border: 1px solid {t.accent};
}}
QCheckBox::indicator:disabled {{
    background-color: {t.bg_panel};
}}

QLabel#cardStats {{
    font-size: 11px;
    color: {t.text_secondary};
}}

QPushButton#btnCardAction {{
    background-color: {t.btn_secondary_bg};
    border: 1px solid {t.border};
    color: {t.btn_secondary_text};
    font-size: 11px;
    font-weight: 500;
    border-radius: 5px;
    padding: 4px 10px;
}}

QPushButton#btnCardAction:hover {{
    background-color: {t.btn_secondary_hover};
    color: {t.text_primary};
    border-color: {t.border_focus};
}}

QPushButton#btnCardRetry {{
    background-color: {t.accent};
    border: none;
    color: {t.accent_text};
    font-size: 11px;
    font-weight: 600;
    border-radius: 5px;
    padding: 4px 12px;
}}

QPushButton#btnCardRetry:hover {{
    background-color: {t.accent_hover};
}}

/* ── Status Feedback Notice ── */
QLabel#statusNotice {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 8px;
    color: {t.text_secondary};
    font-size: 12px;
    padding: 8px 12px;
}}

/* ── Bot-Check / Auth Helper Banner ── */
QFrame#botHelperCard {{
    background-color: rgba(234, 179, 8, 0.09);
    border: 1px solid rgba(234, 179, 8, 0.32);
    border-radius: 9px;
}}

QLabel#botHelperTitle {{
    font-size: 13px;
    font-weight: 700;
    color: #facc15;
}}

QLabel#botHelperDesc {{
    font-size: 11.5px;
    color: {t.text_secondary};
}}

QPushButton#btnBotHelperAction {{
    background-color: #eab308;
    color: #0b0f17;
    font-size: 12px;
    font-weight: 700;
    border-radius: 6px;
    padding: 7px 14px;
    border: none;
}}

QPushButton#btnBotHelperAction:hover {{
    background-color: #facc15;
}}

/* ── History View ── */
QPushButton#btnClearHistory {{
    background-color: {t.btn_secondary_bg};
    border: 1px solid {t.border};
    color: {t.text_secondary};
    font-size: 12px;
    font-weight: 500;
    border-radius: 7px;
    padding: 6px 14px;
}}

QPushButton#btnClearHistory:hover {{
    color: {t.error};
    background-color: {t.error_bg};
    border-color: {t.error};
}}

QPushButton#btnClearHistory:disabled {{
    background-color: transparent;
    border-color: transparent;
    color: {t.text_muted};
}}

QLineEdit#historySearchInput {{
    background-color: {t.bg_input};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 8px 14px;
    color: {t.text_primary};
    font-size: 13px;
}}

QLineEdit#historySearchInput:focus {{
    border: 1px solid {t.border_focus};
    background-color: {t.bg_input_focus};
}}

QPushButton#btnClearSearch {{
    background: transparent;
    color: {t.text_muted};
    border: none;
    font-size: 12px;
}}

QPushButton#btnClearSearch:hover {{
    color: {t.text_primary};
    background: {t.accent_subtle};
    border-radius: 4px;
}}

QPushButton.filter-chip {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    color: {t.text_secondary};
    font-size: 12px;
    font-weight: 500;
    border-radius: 7px;
    padding: 6px 14px;
}}

QPushButton.filter-chip:hover {{
    background-color: {t.bg_card_hover};
    color: {t.text_primary};
    border-color: {t.border_focus};
}}

QPushButton.filter-chip.active {{
    background-color: {t.accent};
    color: {t.accent_text};
    font-weight: 700;
    border: 1px solid {t.accent};
}}

QLabel#historyDateHeader {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: {t.text_muted};
    text-transform: uppercase;
    padding-top: 8px;
    padding-bottom: 2px;
}}

QLabel#historyEmptyState {{
    font-size: 13.5px;
    color: {t.text_muted};
    padding: 40px 0;
}}

/* ── History Item Card ── */
QFrame#historyItemCard {{
    background-color: {t.bg_card};
    border: 1px solid {t.border_subtle};
    border-radius: 12px;
}}

QFrame#historyItemCard:hover {{
    background-color: {t.bg_card_hover};
    border-color: {t.border_focus};
}}

QLabel#historyIcon {{
    background-color: {t.bg_input};
    border-radius: 10px;
    color: {t.text_secondary};
    font-size: 22px;
}}

QLabel#historyTitle {{
    font-size: 14px;
    font-weight: 600;
    color: {t.text_primary};
    line-height: 1.4;
}}

QLabel#historyTimestamp {{
    font-size: 12px;
    color: {t.text_muted};
}}

QLabel#missingFileNotice {{
    font-size: 11.5px;
    font-weight: 500;
    color: {t.warning};
    background-color: {t.warning_bg};
    border: 1px solid {t.warning}44;
    border-radius: 6px;
    padding: 4px 10px;
}}

QPushButton#btnHistoryAction {{
    background-color: {t.btn_secondary_bg};
    border: 1px solid {t.border};
    color: {t.btn_secondary_text};
    font-size: 12.5px;
    font-weight: 500;
    border-radius: 7px;
    padding: 0 16px;
    min-height: 34px;
    max-height: 34px;
}}

QPushButton#btnHistoryAction:hover {{
    background-color: {t.btn_secondary_hover};
    color: {t.text_primary};
    border-color: {t.border_focus};
}}

QPushButton#btnHistoryAction:disabled {{
    background-color: transparent;
    border-color: transparent;
    color: {t.text_muted};
}}

QPushButton#btnHistoryDelete {{
    background: transparent;
    color: {t.text_muted};
    border: none;
    font-size: 13px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    border-radius: 6px;
}}

QPushButton#btnHistoryDelete:hover {{
    color: {t.error};
    background: {t.error_bg};
}}

/* ── Settings View ── */
QFrame#settingsCard {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 12px;
}}

QLabel#settingsSectionTitle {{
    font-size: 11px;
    font-weight: 700;
    color: {t.text_muted};
    letter-spacing: 0.9px;
    text-transform: uppercase;
}}

QLabel#settingsItemTitle {{
    font-size: 14px;
    font-weight: 600;
    color: {t.text_primary};
    line-height: 1.4;
}}

QLabel#settingsItemDesc {{
    font-size: 12.5px;
    color: {t.text_secondary};
    line-height: 1.5;
}}

QLabel#settingsMetaVal {{
    font-size: 13px;
    font-weight: 500;
    color: {t.text_primary};
}}

QLineEdit#settingsPathInput {{
    background-color: {t.bg_input};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 0 14px;
    color: {t.text_primary};
    font-size: 13px;
    min-height: 38px;
    max-height: 38px;
}}

QLineEdit#settingsPathInput:focus {{
    border: 1px solid {t.border_focus};
    background-color: {t.bg_input_focus};
}}

QComboBox#settingsComboBox {{
    background-color: {t.bg_input};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 0 12px;
    color: {t.text_primary};
    font-size: 13px;
    min-height: 38px;
    max-height: 38px;
    min-width: 160px;
}}

QComboBox#settingsComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

QComboBox#settingsComboBox QAbstractItemView {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 8px;
    selection-background-color: {t.accent_active_bg};
    selection-color: {t.text_primary};
    color: {t.text_primary};
    padding: 4px;
}}

QPushButton#btnSettingsAction {{
    background-color: {t.btn_secondary_bg};
    border: 1px solid {t.border};
    color: {t.btn_secondary_text};
    font-size: 12.5px;
    font-weight: 500;
    border-radius: 8px;
    padding: 0 18px;
    min-height: 36px;
    max-height: 36px;
}}

QPushButton#btnSettingsAction:hover {{
    background-color: {t.btn_secondary_hover};
    color: {t.text_primary};
    border-color: {t.border_focus};
}}

QPushButton#btnSettingsAction:disabled {{
    background-color: transparent;
    border-color: transparent;
    color: {t.text_muted};
}}

QPushButton#btnSettingsPrimary {{
    background-color: {t.accent};
    color: {t.accent_text};
    font-size: 12.5px;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 0 20px;
    min-height: 36px;
    max-height: 36px;
}}

QPushButton#btnSettingsPrimary:hover {{
    background-color: {t.accent_hover};
}}

QPushButton#btnSettingsPrimary:disabled {{
    background-color: {t.btn_secondary_bg};
    color: {t.text_muted};
}}

QPushButton#btnSettingsWarning {{
    background-color: {t.warning_bg};
    border: 1px solid {t.warning}55;
    color: {t.warning};
    font-size: 12.5px;
    font-weight: 600;
    border-radius: 8px;
    padding: 0 18px;
    min-height: 36px;
    max-height: 36px;
}}

QPushButton#btnSettingsWarning:hover {{
    background-color: {t.warning}26;
    border-color: {t.warning};
    color: {t.warning};
}}

QPushButton#btnSettingsWarning:disabled {{
    background-color: transparent;
    border-color: transparent;
    color: {t.text_muted};
}}

QLabel#settingsNotice {{
    background-color: {t.bg_input};
    border: 1px solid {t.border_subtle};
    border-radius: 8px;
    color: {t.text_secondary};
    font-size: 12.5px;
    padding: 12px 16px;
    line-height: 1.4;
}}

QFrame#settingsDivider {{
    background-color: {t.border_subtle};
    max-height: 1px;
    min-height: 1px;
}}

QSplitter#contentSplitter::handle:horizontal {{
    background-color: {t.border};
    width: 1px;
}}

QSplitter#contentSplitter::handle:horizontal:hover {{
    background-color: {t.accent};
}}

/* ── System Health Summary ── */
QFrame#healthSummaryFrame {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-left: 3.5px solid #10b981;
    border-radius: 10px;
}}

QFrame#healthSummaryFrame[status="warning"] {{
    border-left: 3.5px solid #f59e0b;
}}

QFrame#healthSummaryFrame[status="danger"] {{
    border-left: 3.5px solid #ef4444;
}}

QLabel#healthSummaryHeader {{
    font-size: 11px;
    font-weight: 700;
    color: {t.text_muted};
    letter-spacing: 0.6px;
}}

QLabel#healthBadgeLabel {{
    font-size: 13px;
    font-weight: 500;
    color: {t.text_primary};
}}

QLabel#healthStatusMsg {{
    font-size: 13px;
    font-weight: 700;
    color: #10b981;
}}

/* ── Playlist Loading Info Banner ── */
QFrame#playlistLoadingCard {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 12px;
}}

QLabel#playlistLoadingTitle {{
    font-size: 14px;
    font-weight: 700;
    color: {t.text_primary};
}}

QLabel#playlistLoadingSub {{
    font-size: 13px;
    font-weight: 400;
    color: {t.text_secondary};
}}

QLabel#playlistLoadingWait {{
    font-size: 12px;
    font-weight: 600;
    color: {t.text_muted};
}}
"""

    if scale != 1.0:
        css = re.sub(
            r'(font-size:\s*)(\d+(?:\.\d+)?)px',
            lambda m: f"{m.group(1)}{max(8, int(round(float(m.group(2)) * scale)))}px",
            css
        )
    return css

DARK_STYLESHEET = get_stylesheet("dark")

