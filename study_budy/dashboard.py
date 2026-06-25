"""Dashboard layout closely matching the approved dark reference."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .appearance_panel import AppearancePanel
from .icons import LOGO_PATH, icon
from .overlay_preview import OverlayPreview
from .server import OverlayServer
from .status_card import StatusCard
from .storage import TaskRepository
from .theme import Theme


class DashboardView(QWidget):
    def __init__(self, repository: TaskRepository, overlay_server: OverlayServer, callbacks: dict[str, callable]) -> None:
        super().__init__()
        self.repository = repository
        self.overlay_server = overlay_server
        self.callbacks = callbacks

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 18, 12, 18)
        root.setSpacing(Theme.SECTION_SPACING)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        main_wrap = QWidget()
        self.main = QVBoxLayout(main_wrap)
        self.main.setSpacing(Theme.SECTION_SPACING)
        self.main.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(main_wrap)
        root.addWidget(scroll, 1)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setFixedWidth(Theme.RIGHT_PANEL_WIDTH)
        right = QWidget()
        self.right_column = QVBoxLayout(right)
        self.right_column.setContentsMargins(0, 0, 0, 0)
        self.right_column.setSpacing(Theme.SECTION_SPACING)
        right_scroll.setWidget(right)
        root.addWidget(right_scroll)

        self._build_main()
        self._build_right()

    def _build_main(self) -> None:
        header = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("H1")
        header.addWidget(title)
        header.addStretch(1)
        self.live_badge = QLabel()
        header.addWidget(self.live_badge)
        settings = QPushButton("Settings")
        settings.setIcon(icon("settings"))
        settings.clicked.connect(self.callbacks["appearance"])
        header.addWidget(settings)
        help_button = QPushButton("Help")
        help_button.setIcon(icon("help"))
        help_button.clicked.connect(self.callbacks["help"])
        header.addWidget(help_button)
        self.main.addLayout(header)

        card_grid = QGridLayout()
        card_grid.setHorizontalSpacing(Theme.SECTION_SPACING)
        self.twitch_card = StatusCard("Twitch", "twitch")
        self.obs_card = StatusCard("OBS", "obs")
        self.overlay_card = StatusCard("Overlay Server", "server")
        self.session_card = StatusCard("Session Status", "session")
        for index, card in enumerate((self.twitch_card, self.obs_card, self.overlay_card, self.session_card)):
            row, column = divmod(index, 2)
            card_grid.addWidget(card, row, column)
            card_grid.setColumnStretch(column, 1)
        self.main.addLayout(card_grid)

        url_card = self._card()
        url_box = QVBoxLayout(url_card)
        url_box.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title = QLabel("Overlay URL")
        title.setObjectName("H2")
        url_box.addWidget(title)
        row = QVBoxLayout()
        row.setSpacing(8)
        self.overlay_url = QLineEdit()
        self.overlay_url.setReadOnly(True)
        row.addWidget(self.overlay_url)
        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        for label, icon_name, callback, primary in (
            ("Copy URL", "copy", self.callbacks["copy_url"], True),
            ("Preview Overlay", "preview", self.callbacks["preview"], False),
            ("Refresh", "refresh", self.callbacks["restart"], False),
        ):
            button = QPushButton(label)
            button.setIcon(icon(icon_name))
            if primary:
                button.setObjectName("PrimaryButton")
            button.clicked.connect(callback)
            button_row.addWidget(button)
        row.addLayout(button_row)
        url_box.addLayout(row)
        self.main.addWidget(url_card)

        two_cards = QVBoxLayout()
        two_cards.setSpacing(Theme.SECTION_SPACING)
        two_cards.addWidget(self._obs_steps_card(), 1)
        two_cards.addWidget(self._controls_card(), 1)
        self.main.addLayout(two_cards)

        self.stats_card = self._stats_card()
        self.main.addWidget(self.stats_card)
        self.main.addWidget(self._viewer_window_card())
        self.main.addStretch(1)

    def _build_right(self) -> None:
        self.preview = OverlayPreview(self.repository, compact=True)
        self.right_column.addWidget(self.preview, 1)
        self.appearance = AppearancePanel(self.repository, self.callbacks["appearance_saved"])
        self.right_column.addWidget(self.appearance)

    def _obs_steps_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title = QLabel("OBS Setup (Quick Steps)")
        title.setObjectName("H2")
        layout.addWidget(title)
        for number, text in enumerate(("Add Browser Source", "Paste overlay URL", "Set width and height", "Position on scene"), start=1):
            row = QHBoxLayout()
            circle = QLabel(str(number))
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setFixedSize(24, 24)
            circle.setStyleSheet(f"background:{Theme.PURPLE}; border-radius:12px; font-weight:900;")
            label = QLabel(text)
            label.setWordWrap(True)
            row.addWidget(circle)
            row.addWidget(label, 1)
            layout.addLayout(row)
        layout.addStretch(1)
        return card

    def _controls_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title = QLabel("Controls")
        title.setObjectName("H2")
        layout.addWidget(title)
        row = QHBoxLayout()
        row.setSpacing(12)
        for label, icon_name, callback, danger in (
            ("Start", "start", self.callbacks["start"], False),
            ("Stop", "stop", self.callbacks["stop"], True),
            ("Restart", "refresh", self.callbacks["restart"], False),
        ):
            button = QPushButton(label)
            button.setIcon(icon(icon_name))
            button.setIconSize(QSize(22, 22))
            button.clicked.connect(callback)
            if danger:
                button.setObjectName("DangerButton")
            row.addWidget(button, 1)
        layout.addLayout(row)
        layout.addStretch(1)
        return card

    def _stats_card(self) -> QFrame:
        card = self._card()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        self.completed_number = QLabel("0")
        self.completed_number.setStyleSheet("font-size: 26px; font-weight: 900;")
        self.sessions_number = QLabel("0")
        self.sessions_number.setStyleSheet("font-size: 26px; font-weight: 900;")
        layout.addLayout(self._stat_item(self.completed_number, "Total Tasks Completed To Date", "Across all viewers"))
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet(f"background:{Theme.BORDER};")
        layout.addWidget(divider)
        layout.addLayout(self._stat_item(self.sessions_number, "Total Streaming Sessions", "Since first launch"))
        return card

    @staticmethod
    def _stat_item(number: QLabel, title: str, subtitle: str) -> QVBoxLayout:
        box = QVBoxLayout()
        label = QLabel(title)
        label.setObjectName("Muted")
        sub = QLabel(subtitle)
        sub.setObjectName("SmallNote")
        box.addWidget(number)
        box.addWidget(label)
        box.addWidget(sub)
        return box

    def _viewer_window_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("HeroCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(icon("window").pixmap(74, 74))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        text = QVBoxLayout()
        heading = QLabel("Viewer Task Window")
        heading.setObjectName("H2")
        body = QLabel("Open viewer task lists in a separate window.")
        body.setObjectName("H2")
        description = QLabel("Viewers can see their personalized tasks, submit completions, and track progress in real time.")
        description.setObjectName("Muted")
        description.setWordWrap(True)
        text.addWidget(heading)
        text.addWidget(body)
        text.addWidget(description)
        buttons = QHBoxLayout()
        open_button = QPushButton("Open Task Window")
        open_button.setObjectName("PrimaryButton")
        open_button.setIcon(icon("window"))
        open_button.clicked.connect(self.callbacks["task_window"])
        manage_button = QPushButton("Manage Viewer Lists")
        manage_button.setIcon(icon("list"))
        manage_button.clicked.connect(self.callbacks["task_window"])
        buttons.addWidget(open_button)
        buttons.addWidget(manage_button)
        text.addLayout(buttons)
        note = QLabel("ⓘ  You can also open this window from the Tasks menu.")
        note.setObjectName("SmallNote")
        text.addWidget(note)
        layout.addLayout(text)
        return card

    @staticmethod
    def _card() -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        return card

    def refresh(self) -> None:
        is_live = self.overlay_server.running
        self.live_badge.setText("●  LIVE" if is_live else "●  OFFLINE")
        self.live_badge.setObjectName("LiveBadge" if is_live else "OfflineBadge")
        self.live_badge.style().unpolish(self.live_badge)
        self.live_badge.style().polish(self.live_badge)
        self.overlay_url.setText(self.overlay_server.url)
        preview_mode = bool(self.repository.get_setting("development_bot", False))
        self.twitch_card.set_status("Preview Mode" if preview_mode else "Not Connected", preview_mode)
        self.obs_card.set_status("Not Connected", False)
        self.overlay_card.set_status("Live" if is_live else "Offline", is_live)
        self.session_card.set_status("Live" if is_live else "Offline", is_live)
        self.completed_number.setText(str(self.repository.lifetime_completed()))
        self.sessions_number.setText(str(self.repository.total_sessions()))
        self.preview.refresh()
        self.appearance.load()
