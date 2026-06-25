"""Dashboard layout closely matching the approved dark reference."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QBoxLayout,
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
        self.stack_right = False
        self.central_compact = False
        self.lower_stack = False
        self.right_in_main = False

        self.root = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self.root.setContentsMargins(12, 16, 12, 16)
        self.root.setSpacing(Theme.SECTION_SPACING)

        self.main_scroll = QScrollArea()
        self.main_scroll.setWidgetResizable(True)
        self.main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        main_wrap = QWidget()
        self.main = QVBoxLayout(main_wrap)
        self.main.setSpacing(Theme.SECTION_SPACING)
        self.main.setContentsMargins(0, 0, 0, 0)
        self.main_scroll.setWidget(main_wrap)
        self.root.addWidget(self.main_scroll, 1)

        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.right_scroll.setMinimumWidth(Theme.RIGHT_PANEL_MIN_WIDTH)
        self.right_scroll.setFixedWidth(Theme.RIGHT_PANEL_WIDTH)
        right = QWidget()
        self.right_column = QVBoxLayout(right)
        self.right_column.setContentsMargins(0, 0, 0, 0)
        self.right_column.setSpacing(Theme.SECTION_SPACING)
        self.right_scroll.setWidget(right)
        self.root.addWidget(self.right_scroll)

        self._build_main()
        self._build_right()
        self.apply_responsive_layout(False, False, False)

    def _build_main(self) -> None:
        self.header_grid = QGridLayout()
        self.header_grid.setHorizontalSpacing(8)
        self.header_grid.setVerticalSpacing(8)
        self.title = QLabel("Dashboard")
        self.title.setObjectName("H1")
        self.live_badge = QLabel()
        self.settings_button = QPushButton("Settings")
        self.settings_button.setIcon(icon("settings"))
        self.settings_button.clicked.connect(self.callbacks["appearance"])
        self.help_button = QPushButton("Help")
        self.help_button.setIcon(icon("help"))
        self.help_button.clicked.connect(self.callbacks["help"])
        self.main.addLayout(self.header_grid)

        self.card_grid = QGridLayout()
        self.card_grid.setHorizontalSpacing(Theme.SECTION_SPACING)
        self.card_grid.setVerticalSpacing(Theme.SECTION_SPACING)
        self.twitch_card = StatusCard("Twitch", "twitch")
        self.obs_card = StatusCard("OBS", "obs")
        self.overlay_card = StatusCard("Overlay Server", "server")
        self.session_card = StatusCard("Session Status", "session")
        self.status_cards = [self.twitch_card, self.obs_card, self.overlay_card, self.session_card]
        self.main.addLayout(self.card_grid)

        url_card = self._card()
        url_box = QVBoxLayout(url_card)
        url_box.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title = QLabel("Overlay URL")
        title.setObjectName("H2")
        url_box.addWidget(title)
        self.url_grid = QGridLayout()
        self.url_grid.setHorizontalSpacing(8)
        self.url_grid.setVerticalSpacing(8)
        self.overlay_url = QLineEdit()
        self.overlay_url.setReadOnly(True)
        self.url_buttons: list[QPushButton] = []
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
            self.url_buttons.append(button)
        url_box.addLayout(self.url_grid)
        self.main.addWidget(url_card)

        self.two_cards = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.two_cards.setSpacing(Theme.SECTION_SPACING)
        self.two_cards.addWidget(self._obs_steps_card(), 1)
        self.two_cards.addWidget(self._controls_card(), 1)
        self.main.addLayout(self.two_cards)

        self.stats_card = self._stats_card()
        self.main.addWidget(self.stats_card)
        self.task_window_button = QPushButton("Open Task Window")
        self.task_window_button.setObjectName("PrimaryButton")
        self.task_window_button.setIcon(icon("window"))
        self.task_window_button.clicked.connect(self.callbacks["task_window"])
        task_button_row = QHBoxLayout()
        task_button_row.addStretch(1)
        task_button_row.addWidget(self.task_window_button)
        self.main.addLayout(task_button_row)
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
            button.setMinimumWidth(72)
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
        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(22)
        logo = QLabel()
        logo.setPixmap(icon("window").pixmap(92, 92))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        text = QVBoxLayout()
        heading = QLabel("Viewer Task Window")
        heading.setObjectName("H1")
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
        layout.addLayout(text, 1)
        return card

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        window_width = self.window().width() if self.window() else self.width()
        stack_right = window_width < Theme.WIDE_BREAKPOINT
        central_width = self.main_scroll.viewport().width()
        central_compact = window_width < Theme.WIDE_BREAKPOINT or central_width < 760
        lower_stack = window_width < Theme.WIDE_BREAKPOINT or central_width < 760
        self.apply_responsive_layout(stack_right, central_compact, lower_stack)

    def apply_responsive_layout(self, stack_right: bool, central_compact: bool, lower_stack: bool) -> None:
        if (
            stack_right == self.stack_right
            and central_compact == self.central_compact
            and lower_stack == self.lower_stack
            and self.card_grid.count()
        ):
            return
        self.stack_right = stack_right
        self.central_compact = central_compact
        self.lower_stack = lower_stack
        self.root.setDirection(QBoxLayout.Direction.TopToBottom if stack_right else QBoxLayout.Direction.LeftToRight)
        window_width = self.window().width() if self.window() else self.width()
        if stack_right and not self.right_in_main:
            self.root.removeWidget(self.right_scroll)
            self.main.insertWidget(max(0, self.main.count() - 1), self.right_scroll)
            self.right_in_main = True
        elif not stack_right and self.right_in_main:
            self.main.removeWidget(self.right_scroll)
            self.root.addWidget(self.right_scroll)
            self.right_in_main = False
        if window_width < Theme.MEDIUM_BREAKPOINT:
            self.root.setContentsMargins(8, 10, 8, 10)
            self.main.setSpacing(8)
            self.task_window_button.setMinimumWidth(0)
        elif stack_right:
            self.root.setContentsMargins(10, 12, 10, 12)
            self.main.setSpacing(Theme.SECTION_SPACING)
            self.task_window_button.setMinimumWidth(160)
        else:
            self.root.setContentsMargins(12, 16, 12, 16)
            self.main.setSpacing(Theme.SECTION_SPACING)
            self.task_window_button.setMinimumWidth(170)
        if stack_right:
            self.right_scroll.setMinimumWidth(0)
            self.right_scroll.setMaximumWidth(16777215)
            self.right_scroll.setMinimumHeight(520)
        else:
            self.right_scroll.setMinimumWidth(Theme.RIGHT_PANEL_MIN_WIDTH)
            self.right_scroll.setFixedWidth(Theme.RIGHT_PANEL_WIDTH)
            self.right_scroll.setMaximumWidth(Theme.RIGHT_PANEL_WIDTH)
            self.right_scroll.setMinimumHeight(0)
        self.two_cards.setDirection(QBoxLayout.Direction.TopToBottom if lower_stack else QBoxLayout.Direction.LeftToRight)
        self._layout_header(window_width < Theme.MEDIUM_BREAKPOINT)
        self._layout_url(central_compact)
        while self.card_grid.count():
            item = self.card_grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        columns = 2 if central_compact else 4
        for index, card in enumerate(self.status_cards):
            row, column = divmod(index, columns)
            self.card_grid.addWidget(card, row, column)
        for column in range(4):
            self.card_grid.setColumnStretch(column, 1 if column < columns else 0)

    def _layout_header(self, compact: bool) -> None:
        while self.header_grid.count():
            item = self.header_grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        for column in range(4):
            self.header_grid.setColumnStretch(column, 0)
        if compact:
            self.header_grid.addWidget(self.title, 0, 0)
            self.header_grid.addWidget(self.live_badge, 0, 1, alignment=Qt.AlignmentFlag.AlignRight)
            self.header_grid.addWidget(self.settings_button, 1, 0)
            self.header_grid.addWidget(self.help_button, 1, 1)
            self.header_grid.setColumnStretch(0, 1)
            self.header_grid.setColumnStretch(1, 1)
        else:
            self.header_grid.addWidget(self.title, 0, 0)
            self.header_grid.addWidget(self.live_badge, 0, 1, alignment=Qt.AlignmentFlag.AlignRight)
            self.header_grid.addWidget(self.settings_button, 0, 2)
            self.header_grid.addWidget(self.help_button, 0, 3)
            self.header_grid.setColumnStretch(0, 1)

    def _layout_url(self, central_compact: bool) -> None:
        while self.url_grid.count():
            self.url_grid.takeAt(0)
        if central_compact:
            for column in range(4):
                self.url_grid.setColumnStretch(column, 0)
            self.url_grid.addWidget(self.overlay_url, 0, 0, 1, 3)
            for column, button in enumerate(self.url_buttons):
                self.url_grid.addWidget(button, 1, column)
                self.url_grid.setColumnStretch(column, 1)
        else:
            for column in range(4):
                self.url_grid.setColumnStretch(column, 0)
            self.url_grid.addWidget(self.overlay_url, 0, 0)
            for column, button in enumerate(self.url_buttons, start=1):
                self.url_grid.addWidget(button, 0, column)
            self.url_grid.setColumnStretch(0, 1)

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
