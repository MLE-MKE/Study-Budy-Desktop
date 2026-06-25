"""Shared visual theme for the Study Budy desktop UI."""

from __future__ import annotations


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
        background: #12161b;
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
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {Theme.PANEL}, stop:1 #111821);
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
        background: #36171a;
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
        border: 1px solid #3a424e;
        border-radius: 8px;
        padding: 0 16px;
        color: {Theme.TEXT};
        font-weight: 700;
    }}
    QPushButton:hover {{
        border-color: {Theme.PURPLE};
        background: #242033;
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
        background: #32171b;
        border-color: #66313b;
    }}
    QLineEdit, QComboBox, QSpinBox, QTreeWidget, QTextBrowser {{
        background: {Theme.INPUT};
        border: 1px solid #343c48;
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
        alternate-background-color: #151a21;
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
        background: #3a4350;
        border-radius: 5px;
        min-height: 42px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    """
