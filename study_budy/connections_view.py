"""Connections screen for Twitch, OBS, and preview-mode state."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from .icons import icon
from .storage import TaskRepository
from .theme import Theme


class ConnectionsView(QWidget):
    def __init__(self, repository: TaskRepository, on_refresh) -> None:
        super().__init__()
        self.repository = repository
        self.on_refresh = on_refresh
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(Theme.SECTION_SPACING)
        title = QLabel("Connections")
        title.setObjectName("H1")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("Card")
        box = QVBoxLayout(card)
        box.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        self.status = QLabel()
        self.status.setWordWrap(True)
        box.addWidget(self.status)
        form = QGridLayout()
        self.account_name = QLineEdit()
        self.account_name.setReadOnly(True)
        self.channel_name = QLineEdit()
        self.chat_status = QLineEdit()
        self.chat_status.setReadOnly(True)
        form.addWidget(QLabel("Connected account"), 0, 0)
        form.addWidget(self.account_name, 0, 1)
        form.addWidget(QLabel("Connected channel"), 1, 0)
        form.addWidget(self.channel_name, 1, 1)
        form.addWidget(QLabel("Chat status"), 2, 0)
        form.addWidget(self.chat_status, 2, 1)
        box.addLayout(form)

        buttons = QHBoxLayout()
        for label, callback, primary in (
            ("Connect Streamer Account", self.connect_streamer, True),
            ("Connect Bot Account", self.connect_bot, False),
            ("Disconnect", self.disconnect, False),
            ("Reconnect", self.reconnect, False),
            ("Test Connection", self.test_connection, False),
        ):
            button = QPushButton(label)
            if primary:
                button.setObjectName("PrimaryButton")
            button.clicked.connect(callback)
            buttons.addWidget(button)
        box.addLayout(buttons)
        layout.addWidget(card)

        note = QLabel(
            "Preview Mode uses the development bot display name killer_queens_jester. "
            "Real Twitch OAuth is still the next integration step; no passwords or credentials are stored here."
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        self.refresh()

    def refresh(self) -> None:
        preview_mode = bool(self.repository.get_setting("development_bot", False))
        channel = self.repository.get_setting("twitch_channel", "")
        bot = self.repository.get_setting("preview_bot_name", "killer_queens_jester")
        self.account_name.setText(bot if preview_mode else "Not connected")
        self.channel_name.setText(channel)
        self.chat_status.setText("Preview Mode" if preview_mode else "Disconnected")
        self.status.setText(
            "Preview Mode is enabled. Dashboard status cards may show simulated Twitch readiness."
            if preview_mode
            else "Twitch is not connected. Use OAuth when real integration is implemented."
        )

    def connect_streamer(self) -> None:
        self.repository.set_setting("twitch_channel", self.channel_name.text().strip().lstrip("#"))
        self.refresh()
        self.on_refresh()

    def connect_bot(self) -> None:
        self.repository.set_setting("development_bot", True)
        self.repository.set_setting("preview_bot_name", "killer_queens_jester")
        self.refresh()
        self.on_refresh()

    def disconnect(self) -> None:
        self.repository.set_setting("development_bot", False)
        self.refresh()
        self.on_refresh()

    def reconnect(self) -> None:
        self.refresh()
        self.on_refresh()

    def test_connection(self) -> None:
        self.repository.add_task("killer_queens_jester", "Preview test task from Twitch chat")
        self.refresh()
        self.on_refresh()
