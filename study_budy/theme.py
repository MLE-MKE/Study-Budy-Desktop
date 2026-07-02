"""Shared visual theme for the Study Budy desktop UI."""

from __future__ import annotations

APPLICATION_THEME_KEY = "application_theme"
APPLICATION_THEME_OPTIONS = ("Dark", "Light", "Pastel Pink")


# ---- APPLICATION COLOR THEMES ----
# This section stores the colors used by each desktop application theme.
THEMES = {
    "Dark": {
        "BACKGROUND": "#0f1318",
        "BACKGROUND_ALT": "#12171d",
        "SIDEBAR": "#0b1016",
        "PANEL": "#171c23",
        "PANEL_ALT": "#1b2028",
        "INPUT": "#11161d",
        "BORDER": "#303743",
        "BORDER_SOFT": "#242b35",
        "TEXT": "#f6f3fb",
        "TEXT_MUTED": "#b7b0c3",
        "TEXT_DIM": "#8c8697",
        "PURPLE": "#7b2ff2",
        "PURPLE_DARK": "#4f19aa",
        "PURPLE_SOFT": "#2b164f",
        "GREEN": "#24d45c",
        "GREEN_DARK": "#087f2b",
        "RED": "#ff3131",
        "BLUE": "#2f80ff",
        "WARNING": "#ffd84f",
        "MENU": "#12161b",
        "HERO_END": "#111821",
        "BUTTON_BORDER": "#3a424e",
        "BUTTON_HOVER": "#242033",
        "DANGER_BG": "#32171b",
        "DANGER_BORDER": "#66313b",
        "TREE_ALT": "#151a21",
        "SCROLL_HANDLE": "#3a4350",
        "OFFLINE_BG": "#36171a",
    },
    "Light": {
        "BACKGROUND": "#f4f6fb",
        "BACKGROUND_ALT": "#ffffff",
        "SIDEBAR": "#eef1f7",
        "PANEL": "#ffffff",
        "PANEL_ALT": "#e8edf5",
        "INPUT": "#ffffff",
        "BORDER": "#cbd3df",
        "BORDER_SOFT": "#dce2eb",
        "TEXT": "#1d2430",
        "TEXT_MUTED": "#536070",
        "TEXT_DIM": "#6f7a89",
        "PURPLE": "#6d3fd9",
        "PURPLE_DARK": "#4d2ca8",
        "PURPLE_SOFT": "#eee8ff",
        "GREEN": "#15803d",
        "GREEN_DARK": "#166534",
        "RED": "#dc2626",
        "BLUE": "#2563eb",
        "WARNING": "#b7791f",
        "MENU": "#ffffff",
        "HERO_END": "#edf2fa",
        "BUTTON_BORDER": "#b9c3d2",
        "BUTTON_HOVER": "#dde5f2",
        "DANGER_BG": "#fff1f2",
        "DANGER_BORDER": "#f1a7ae",
        "TREE_ALT": "#f0f3f8",
        "SCROLL_HANDLE": "#a9b4c4",
        "OFFLINE_BG": "#fff1f2",
    },
    # ---- PASTEL PINK THEME ----
    # This theme gives my application a soft pink appearance while keeping everything readable.
    # peepeepoo poo, professional software can still be pink
    "Pastel Pink": {
        "BACKGROUND": "#fff1f6",
        "BACKGROUND_ALT": "#fff7fa",
        "SIDEBAR": "#f8dce8",
        "PANEL": "#fff8fb",
        "PANEL_ALT": "#f3d7e3",
        "INPUT": "#fffafd",
        "BORDER": "#d9a5b8",
        "BORDER_SOFT": "#e8c4d1",
        "TEXT": "#2b1d27",
        "TEXT_MUTED": "#67515e",
        "TEXT_DIM": "#806b77",
        "PURPLE": "#c45f87",
        "PURPLE_DARK": "#9d4168",
        "PURPLE_SOFT": "#f8d9e6",
        "GREEN": "#15803d",
        "GREEN_DARK": "#166534",
        "RED": "#c81e4a",
        "BLUE": "#2563eb",
        "WARNING": "#a16207",
        "MENU": "#fff8fb",
        "HERO_END": "#ffe6ef",
        "BUTTON_BORDER": "#cc98ac",
        "BUTTON_HOVER": "#ebc2d1",
        "DANGER_BG": "#ffe8ef",
        "DANGER_BORDER": "#d9829c",
        "TREE_ALT": "#fdebf2",
        "SCROLL_HANDLE": "#c98fa5",
        "OFFLINE_BG": "#ffe5ec",
    },
}


def normalize_application_theme(value: object) -> str:
    return str(value) if value in APPLICATION_THEME_OPTIONS else "Dark"


class Theme:
    BACKGROUND = "#0f1318"
    BACKGROUND_ALT = "#12171d"
    SIDEBAR = "#0b1016"
    PANEL = "#171c23"
    PANEL_ALT = "#1b2028"
    INPUT = "#11161d"
    BORDER = "#303743"
    BORDER_SOFT = "#242b35"
    TEXT = "#f6f3fb"
    TEXT_MUTED = "#b7b0c3"
    TEXT_DIM = "#8c8697"
    PURPLE = "#7b2ff2"
    PURPLE_DARK = "#4f19aa"
    PURPLE_SOFT = "#2b164f"
    GREEN = "#24d45c"
    GREEN_DARK = "#087f2b"
    RED = "#ff3131"
    BLUE = "#2f80ff"
    WARNING = "#ffd84f"

    RADIUS = 10
    CARD_PADDING = 12
    SECTION_SPACING = 10
    BUTTON_HEIGHT = 36
    SIDEBAR_WIDTH = 180
    SIDEBAR_WIDTH_MEDIUM = 145
    SIDEBAR_WIDTH_COMPACT = 96
    RIGHT_PANEL_WIDTH = 300
    RIGHT_PANEL_MIN_WIDTH = 285
    WIDE_BREAKPOINT = 1150
    MEDIUM_BREAKPOINT = 850
    PAGE_RESPONSIVE_BREAKPOINT = 860
    MIN_WINDOW_WIDTH = 760
    MIN_WINDOW_HEIGHT = 620
    DEFAULT_WINDOW_WIDTH = 980
    DEFAULT_WINDOW_HEIGHT = 760
    FONT_STACK = "'Poppins', 'Segoe UI', 'Comic Neue', sans-serif"
    CURRENT = "Dark"

    @classmethod
    def apply(cls, theme_name: object) -> str:
        selected = normalize_application_theme(theme_name)
        for key, value in THEMES[selected].items():
            setattr(cls, key, value)
        cls.CURRENT = selected
        return selected


def app_stylesheet() -> str:
    """Return the app-wide stylesheet with all colors centralized here."""

    return f"""
    QMainWindow, QWidget {{
        background: {Theme.BACKGROUND};
        color: {Theme.TEXT};
        font-family: {Theme.FONT_STACK};
        font-size: 12px;
    }}
    QMenuBar {{
        background: {Theme.MENU};
        border-bottom: 1px solid {Theme.BORDER_SOFT};
        padding: 3px 8px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 6px 12px;
        border-radius: 5px;
    }}
    QMenuBar::item:selected {{
        background: {Theme.PANEL_ALT};
    }}
    QMenu {{
        background: {Theme.PANEL};
        border: 1px solid {Theme.BORDER};
        padding: 5px;
    }}
    QMenu::item {{
        padding: 7px 26px 7px 18px;
        border-radius: 5px;
    }}
    QMenu::item:selected {{
        background: {Theme.PURPLE_DARK};
    }}
    QFrame#Sidebar {{
        background: {Theme.SIDEBAR};
        border-right: 1px solid {Theme.BORDER_SOFT};
    }}
    QLabel {{
        background: transparent;
    }}
    QFrame#Card, QFrame#PanelCard {{
        background: {Theme.PANEL};
        border: 1px solid {Theme.BORDER};
        border-radius: {Theme.RADIUS}px;
    }}
    QFrame#HeroCard {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {Theme.PANEL}, stop:1 {Theme.HERO_END});
        border: 1px solid {Theme.PURPLE};
        border-radius: {Theme.RADIUS}px;
    }}
    QLabel#H1 {{
        font-size: 26px;
        font-weight: 800;
    }}
    QLabel#H2 {{
        font-size: 14px;
        font-weight: 800;
    }}
    QLabel#Muted, QLabel#SmallNote {{
        color: {Theme.TEXT_MUTED};
    }}
    QLabel#SmallNote {{
        font-size: 11px;
    }}
    QLabel#StatusGood {{
        color: {Theme.GREEN};
        font-weight: 800;
    }}
    QLabel#StatusBad {{
        color: {Theme.RED};
        font-weight: 800;
    }}
    QLabel#LiveBadge {{
        background: {Theme.GREEN_DARK};
        border: 1px solid {Theme.GREEN};
        border-radius: 8px;
        color: white;
        font-weight: 900;
        padding: 7px 14px;
        letter-spacing: 1px;
    }}
    QLabel#OfflineBadge {{
        background: {Theme.OFFLINE_BG};
        border: 1px solid {Theme.RED};
        border-radius: 8px;
        color: white;
        font-weight: 900;
        padding: 7px 14px;
        letter-spacing: 1px;
    }}
    QPushButton {{
        min-height: {Theme.BUTTON_HEIGHT}px;
        min-width: 84px;
        background: {Theme.PANEL_ALT};
        border: 1px solid {Theme.BUTTON_BORDER};
        border-radius: 8px;
        padding: 0 16px;
        color: {Theme.TEXT};
        font-weight: 700;
    }}
    QPushButton:hover {{
        border-color: {Theme.PURPLE};
        background: {Theme.BUTTON_HOVER};
    }}
    QPushButton:pressed {{
        background: {Theme.PURPLE_DARK};
    }}
    QPushButton#PrimaryButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {Theme.PURPLE}, stop:1 {Theme.PURPLE_DARK});
        border-color: {Theme.PURPLE};
    }}
    QPushButton#NavButton {{
        background: transparent;
        border: 0;
        border-radius: 8px;
        min-height: 46px;
        padding: 0 14px;
        text-align: left;
    }}
    QPushButton#NavButton[active="true"] {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {Theme.PURPLE}, stop:1 {Theme.PURPLE_DARK});
    }}
    QPushButton#DangerButton {{
        background: {Theme.DANGER_BG};
        border-color: {Theme.DANGER_BORDER};
    }}
    /* ---- TASK WINDOW ACTION BUTTONS ---- */
    /* This section keeps my longer Task window button labels from getting chopped off. */
    QPushButton#TaskActionButton {{
        width: auto;
        min-width: 220px;
        max-width: 100%;
        padding: 10px 18px;
        text-align: center;
        box-sizing: border-box;
    }}
    QLineEdit, QComboBox, QSpinBox, QTreeWidget, QTextBrowser {{
        background: {Theme.INPUT};
        border: 1px solid {Theme.BUTTON_BORDER};
        border-radius: 7px;
        padding: 8px;
        color: {Theme.TEXT};
        selection-background-color: {Theme.PURPLE};
    }}
    QComboBox {{
        min-height: 34px;
    }}
    QCheckBox {{
        spacing: 8px;
    }}
    QTabWidget::pane {{
        border: 1px solid {Theme.BORDER};
        border-radius: {Theme.RADIUS}px;
        top: -1px;
        background: {Theme.BACKGROUND};
    }}
    QTabBar::tab {{
        background: {Theme.PANEL};
        color: {Theme.TEXT_MUTED};
        border: 1px solid {Theme.BORDER};
        border-bottom-color: {Theme.BORDER};
        padding: 9px 18px;
        min-width: 86px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }}
    QTabBar::tab:selected {{
        background: {Theme.PURPLE_DARK};
        color: {Theme.TEXT};
        border-color: {Theme.PURPLE};
    }}
    QTabBar::tab:hover {{
        color: {Theme.TEXT};
        border-color: {Theme.PURPLE};
    }}
    QTreeWidget {{
        alternate-background-color: {Theme.TREE_ALT};
    }}
    QTreeWidget::item {{
        min-height: 28px;
    }}
    QTreeWidget::item:selected {{
        background: {Theme.PURPLE_DARK};
    }}
    QScrollArea {{
        border: 0;
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: {Theme.BACKGROUND};
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {Theme.SCROLL_HANDLE};
        border-radius: 5px;
        min-height: 42px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    """
