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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 18, 12, 16)
        layout.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(QPixmap(str(LOGO_PATH)).scaled(92, 92, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        brand = QLabel("STUDY BUDY\nDESKTOP")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setStyleSheet("font-weight: 900; font-size: 17px; letter-spacing: 2px;")
        layout.addWidget(brand)
        layout.addSpacing(18)

        rows = [
            ("Dashboard", "dashboard"),
            ("Tasks", "tasks"),
            ("Connections", "connections"),
            ("Appearance", "appearance"),
            ("Check In", "check"),
            ("Help", "help"),
        ]
        for index, (label, icon_name) in enumerate(rows):
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setIcon(icon(icon_name))
            button.setIconSize(QSize(24, 24))
            page = 5 if label == "Help" else index
            button.setProperty("pageIndex", page)
            button.clicked.connect(lambda checked=False, page=page: self.navigate.emit(page))
            layout.addWidget(button)
            self.buttons.append(button)

        layout.addStretch(1)
        version = QLabel("v1.2.0")
        version.setObjectName("SmallNote")
        layout.addWidget(version)
        self.system_status = QLabel("●  All Systems Operational")
        self.system_status.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        layout.addWidget(self.system_status)
        self.set_active(0)

    def set_active(self, index: int) -> None:
        for button in self.buttons:
            button.setProperty("active", button.property("pageIndex") == index and button.isEnabled())
            button.style().unpolish(button)
            button.style().polish(button)

    def set_system_status(self, label: str, good: bool) -> None:
        color = Theme.GREEN if good else Theme.RED
        self.system_status.setText(f"●  {label}")
        self.system_status.setStyleSheet(f"color: {color};")
