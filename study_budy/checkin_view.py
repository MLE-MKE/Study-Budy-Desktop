"""Desktop Check-In overlay control page."""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .checkin import CheckInService
from .icons import icon
from .server import OverlayServer
from .storage import TaskRepository
from .theme import Theme


class CheckInView(QWidget):
    def __init__(self, repository: TaskRepository, overlay_server: OverlayServer, callbacks: dict[str, callable]) -> None:
        super().__init__()
        self.repository = repository
        self.overlay_server = overlay_server
        self.callbacks = callbacks
        self.service = CheckInService(repository)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(Theme.SECTION_SPACING)
        title = QLabel("Check In")
        title.setObjectName("H1")
        root.addWidget(title)

        top = QHBoxLayout()
        top.addWidget(self._status_card(), 1)
        top.addWidget(self._preview_card(), 1)
        root.addLayout(top)

        middle = QHBoxLayout()
        middle.addWidget(self._viewer_card(), 2)
        middle.addWidget(self._obs_card(), 1)
        root.addLayout(middle, 1)
        self.refresh()

    def _card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        return card

    def _status_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        layout.addWidget(QLabel("<b>Overlay status</b>"))
        grid = QGridLayout()
        self.overlay_status = QLabel()
        self.chat_status = QLabel("Preview Mode / Twitch not connected")
        self.session_status = QLabel()
        self.active_count = QLabel()
        for row, (label, widget) in enumerate(
            (
                ("Check-In overlay", self.overlay_status),
                ("Twitch chat", self.chat_status),
                ("Session", self.session_status),
                ("Checked-in viewers", self.active_count),
            )
        ):
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(widget, row, 1)
        layout.addLayout(grid)
        self.url = QLineEdit()
        self.url.setReadOnly(True)
        layout.addWidget(QLabel("Check-In overlay URL"))
        layout.addWidget(self.url)
        buttons = QGridLayout()
        for index, (label, callback, primary) in enumerate(
            (
                ("Copy URL", self.copy_url, True),
                ("Preview Overlay", self.preview_overlay, False),
                ("Refresh", self.refresh, False),
                ("Start", self.callbacks["start"], False),
                ("Stop", self.callbacks["stop"], False),
                ("Restart", self.callbacks["restart"], False),
            )
        ):
            button = QPushButton(label)
            if primary:
                button.setObjectName("PrimaryButton")
            button.clicked.connect(callback)
            buttons.addWidget(button, index // 3, index % 3)
        layout.addLayout(buttons)
        return card

    def _viewer_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        layout.addWidget(QLabel("<b>Current checked-in viewers</b>"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Display name", "Shape", "Color", "Check-in time", "State", ""])
        self.tree.setColumnWidth(0, 170)
        self.tree.setColumnWidth(1, 90)
        self.tree.setColumnWidth(2, 95)
        self.tree.setColumnWidth(3, 150)
        layout.addWidget(self.tree, 1)
        buttons = QGridLayout()
        for index, (label, callback) in enumerate(
            (
                ("Clear all check-ins", self.clear_all),
                ("Reset positions", self.refresh),
                ("Preview Mode: Simulate check-in", self.simulate_checkin),
                ("Preview Mode: Simulate task added", self.simulate_task_added),
                ("Preview Mode: Simulate task completed", self.simulate_task_completed),
                ("Preview Mode: Simulate leave", self.simulate_leave),
            )
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            buttons.addWidget(button, index // 2, index % 2)
        layout.addLayout(buttons)
        return card

    def _obs_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        layout.addWidget(QLabel("<b>OBS setup</b>"))
        instructions = QTextBrowser()
        instructions.setHtml(
            """
            <ol>
              <li>Open OBS or Streamlabs Desktop.</li>
              <li>Add a new Browser Source.</li>
              <li>Paste the Check-In overlay URL.</li>
              <li>Set the background to transparent.</li>
              <li>Use 1280 x 720 or your scene size.</li>
              <li>Position it separately from the task-list overlay.</li>
            </ol>
            """
        )
        layout.addWidget(instructions)
        return card

    def _preview_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        layout.addWidget(QLabel("<b>Simulated live preview</b>"))
        self.preview = QTextBrowser()
        layout.addWidget(self.preview, 1)
        return card

    def refresh(self) -> None:
        active = self.service.active_checkins()
        self.overlay_status.setText("Live" if self.overlay_server.running else "Offline")
        self.session_status.setText("Live" if self.overlay_server.running else "Offline")
        self.active_count.setText(str(len(active)))
        self.url.setText(self.overlay_server.checkin_url)
        self.tree.clear()
        for viewer in active:
            item = QTreeWidgetItem(
                [
                    viewer["display_name"],
                    viewer["shape"],
                    viewer["color"],
                    (viewer["last_checkin_at"] or "")[:19],
                    viewer["state"],
                    "Remove",
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, viewer["user_id"])
            self.tree.addTopLevelItem(item)
        self.preview.setHtml(self._preview_html(active))

    def _preview_html(self, active: list[dict]) -> str:
        if not active:
            active = [
                {"display_name": "Killer_Queen55", "shape": "octagon", "color": "#facc15", "is_streamer": True},
                {"display_name": "Alex", "shape": "circle", "color": "#8b5cf6", "is_streamer": False},
                {"display_name": "Jamie", "shape": "triangle", "color": "#22d3ee", "is_streamer": False},
                {"display_name": "FlowFox", "shape": "square", "color": "#f97316", "is_streamer": False},
            ]
        html = "<style>.row{display:flex;gap:10px;flex-wrap:wrap}.a{text-align:center;margin:8px}.s{width:52px;height:52px;margin:auto;border:3px solid #1b0b45}.circle{border-radius:50%}.square{border-radius:8px}.octagon{clip-path:polygon(30% 0,70% 0,100% 30%,100% 70%,70% 100%,30% 100%,0 70%,0 30%)}.triangle{width:0;height:0;border-left:26px solid transparent;border-right:26px solid transparent;border-bottom:52px solid var(--c);background:transparent!important}</style><div class='row'>"
        for viewer in active:
            html += f"<div class='a'><div>{viewer['display_name'][:18]}</div><div class='s {viewer['shape']}' style='background:{viewer['color']};--c:{viewer['color']}'></div><small>{viewer['shape']}</small></div>"
        return html + "</div>"

    def copy_url(self) -> None:
        QApplication.clipboard().setText(self.overlay_server.checkin_url)

    def preview_overlay(self) -> None:
        if not self.overlay_server.running:
            self.callbacks["start"]()
        webbrowser.open(self.overlay_server.checkin_url)

    def clear_all(self) -> None:
        self.service.clear_active()
        self.refresh()

    def simulate_checkin(self) -> None:
        count = len(self.service.all_users()) + 1
        self.service.checkin(f"preview-{count}", f"PreviewViewer{count}")
        self.refresh()

    def simulate_task_added(self) -> None:
        active = self.service.active_checkins()
        if active:
            viewer = active[-1]
            self.service.emit_event("task_added", viewer["user_id"], viewer["display_name"], {})
        self.refresh()

    def simulate_task_completed(self) -> None:
        active = self.service.active_checkins()
        if active:
            viewer = active[-1]
            self.service.emit_event("task_completed", viewer["user_id"], viewer["display_name"], {})
        self.refresh()

    def simulate_leave(self) -> None:
        active = self.service.active_checkins()
        if active:
            viewer = active[-1]
            self.service.leave(viewer["user_id"], viewer["display_name"])
        self.refresh()
