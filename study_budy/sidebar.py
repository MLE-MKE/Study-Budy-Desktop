"""Left navigation sidebar for the Study Budy desktop app."""

from __future__ import annotations

from PySide6.QtCore import QSize, Signal, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from .icons import LOGO_PATH, icon
from .theme import Theme


class Sidebar(QFrame):
    navigate = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(Theme.SIDEBAR_WIDTH)
        self.buttons: list[QPushButton] = []
        self.nav_rows = [
            ("Dashboard", "Dash", "dashboard", 0),
            ("Tasks", "Tasks", "tasks", 1),
            ("Connections", "Conn", "connections", 2),
            ("Appearance", "Style", "appearance", 3),
            ("Check In", "Check", "check", 4),
            ("Help", "Help", "help", 5),
        ]

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 18, 12, 16)
        self.layout.setSpacing(10)

        self.logo = QLabel()
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.logo)

        self.brand = QLabel("STUDY BUDY\nDESKTOP")
        self.brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.brand)
        self.layout.addSpacing(18)

        for label, _short_label, icon_name, page in self.nav_rows:
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setIcon(icon(icon_name))
            button.setIconSize(QSize(24, 24))
            button.setProperty("pageIndex", page)
            button.setToolTip(label)
            button.clicked.connect(lambda checked=False, page=page: self.navigate.emit(page))
            self.layout.addWidget(button)
            self.buttons.append(button)

        self.layout.addStretch(1)
        self.version = QLabel("v1.2.0")
        self.version.setObjectName("SmallNote")
        self.layout.addWidget(self.version)
        self.system_status = QLabel("●  All Systems Operational")
        self.system_status.setWordWrap(True)
        self.system_status.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        self.layout.addWidget(self.system_status)
        self.set_active(0)
        self.apply_responsive_width(Theme.DEFAULT_WINDOW_WIDTH)

    def apply_responsive_width(self, window_width: int) -> None:
        compact = window_width < Theme.MEDIUM_BREAKPOINT
        medium = Theme.MEDIUM_BREAKPOINT <= window_width < Theme.WIDE_BREAKPOINT
        width = Theme.SIDEBAR_WIDTH_COMPACT if compact else Theme.SIDEBAR_WIDTH_MEDIUM if medium else Theme.SIDEBAR_WIDTH
        logo_size = 54 if compact else 72 if medium else 92
        icon_size = 22 if compact else 24
        horizontal_margin = 8 if compact else 10 if medium else 12

        self.setFixedWidth(width)
        self.layout.setContentsMargins(horizontal_margin, 14, horizontal_margin, 14)
        self.logo.setPixmap(
            QPixmap(str(LOGO_PATH)).scaled(
                logo_size,
                logo_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        if compact:
            self.brand.setText("STUDY\nBUDY")
            self.brand.setStyleSheet("font-weight: 900; font-size: 11px; letter-spacing: 1px;")
            nav_labels = [short for _full, short, _icon, _page in self.nav_rows]
        else:
            self.brand.setText("STUDY BUDY\nDESKTOP")
            self.brand.setStyleSheet(
                f"font-weight: 900; font-size: {13 if medium else 17}px; letter-spacing: {1 if medium else 2}px;"
            )
            nav_labels = [full for full, _short, _icon, _page in self.nav_rows]
        for button, text in zip(self.buttons, nav_labels, strict=True):
            button.setText(text)
            button.setIconSize(QSize(icon_size, icon_size))

    def set_active(self, index: int) -> None:
        for button in self.buttons:
            button.setProperty("active", button.property("pageIndex") == index and button.isEnabled())
            button.style().unpolish(button)
            button.style().polish(button)

    def set_system_status(self, label: str, good: bool) -> None:
        color = Theme.GREEN if good else Theme.RED
        self.system_status.setText(f"●  {label}")
        self.system_status.setStyleSheet(f"color: {color};")
