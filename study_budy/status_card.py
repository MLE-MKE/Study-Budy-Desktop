"""Reusable dashboard status card."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from .icons import icon
from .theme import Theme


class StatusCard(QFrame):
    def __init__(self, title: str, icon_name: str, good: bool = False) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.setMinimumHeight(78)
        self.setSizePolicy(self.sizePolicy().Policy.Expanding, self.sizePolicy().Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        layout.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(icon(icon_name).pixmap(QSize(28, 28)))
        icon_label.setFixedSize(34, 34)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        text_box = QVBoxLayout()
        text_box.setSpacing(3)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("H2")
        self.title_label.setWordWrap(True)
        self.value_label = QLabel("Offline")
        self.value_label.setObjectName("StatusGood" if good else "StatusBad")
        self.value_label.setWordWrap(True)
        text_box.addWidget(self.title_label)
        text_box.addWidget(self.value_label)
        layout.addLayout(text_box, 1)

        self.indicator = QLabel("●")
        self.indicator.setStyleSheet(f"color: {Theme.GREEN if good else Theme.RED}; font-size: 22px;")
        layout.addWidget(self.indicator)

    def set_status(self, status: str, good: bool) -> None:
        self.value_label.setText(status)
        self.value_label.setObjectName("StatusGood" if good else "StatusBad")
        self.value_label.style().unpolish(self.value_label)
        self.value_label.style().polish(self.value_label)
        self.indicator.setStyleSheet(f"color: {Theme.GREEN if good else Theme.RED}; font-size: 22px;")
