"""Desktop Check-In overlay control page with feature-local tabs."""

from __future__ import annotations

import webbrowser
from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .checkin import CheckInService, DEFAULT_CHECKIN_APPEARANCE
from .server import OverlayServer
from .storage import TaskRepository
from .theme import Theme

DEFAULT_MESSAGE_LISTS = {
    "checkin": ["I'm here!", "Ready to study!", "Let's work!"],
    "leave": ["Heading out!", "Back later!", "Good luck everyone!"],
    "task_added_self": ["New goal!", "Task added!", "Time to focus!"],
    "task_added_group": ["You got this!", "Good plan!", "Let's go!", "One step at a time!"],
    "task_completed_self": ["I did it!", "Done and done!", "One more down!"],
    "task_completed_group": ["Good job!", "Nice work!", "Way to go!", "You crushed it!"],
}


class CheckInView(QWidget):
    def __init__(self, repository: TaskRepository, overlay_server: OverlayServer, callbacks: dict[str, callable]) -> None:
        super().__init__()
        self.repository = repository
        self.overlay_server = overlay_server
        self.callbacks = callbacks
        self.service = CheckInService(repository)
        self.appearance_fields: dict[str, QWidget] = {}
        self.message_fields: dict[str, QTextEdit] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(Theme.SECTION_SPACING)
        title = QLabel("Check In")
        title.setObjectName("H1")
        root.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._overview_tab(), "Overview")
        self.tabs.addTab(self._appearance_tab(), "Appearance")
        self.tabs.addTab(self._messages_tab(), "Messages")
        self.tabs.addTab(self._preview_tab(), "Preview")
        self.tabs.addTab(self._settings_tab(), "Settings")
        root.addWidget(self.tabs, 1)
        self.refresh()

    def _card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        return card

    def _overview_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setSpacing(Theme.SECTION_SPACING)
        top = QHBoxLayout()
        top.addWidget(self._status_card(), 1)
        top.addWidget(self._obs_card(), 1)
        root.addLayout(top)
        root.addWidget(self._viewer_card(), 1)
        return page

    def _status_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        layout.addWidget(QLabel("<b>Check-In Overlay</b>"))
        grid = QGridLayout()
        self.overlay_status = QLabel()
        self.chat_status = QLabel("Preview Mode / Twitch not connected")
        self.session_status = QLabel()
        self.active_count = QLabel()
        self.session_peak = QLabel()
        for row, (label, widget) in enumerate(
            (
                ("Overlay status", self.overlay_status),
                ("Twitch chat", self.chat_status),
                ("Session status", self.session_status),
                ("Checked-in viewers", self.active_count),
                ("Session peak", self.session_peak),
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
                ("Preview", self.preview_overlay, False),
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
        layout.addWidget(QLabel("<b>Current Check-Ins</b>"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Display name", "Shape", "Color", "Check-in time", "State"])
        self.tree.setColumnWidth(0, 170)
        self.tree.setColumnWidth(1, 90)
        self.tree.setColumnWidth(2, 95)
        self.tree.setColumnWidth(3, 150)
        layout.addWidget(self.tree, 1)
        buttons = QGridLayout()
        for index, (label, callback) in enumerate(
            (
                ("Clear all", self.clear_all),
                ("Remove selected", self.remove_selected),
                ("Reset positions", self.refresh),
                ("Preview Mode: Simulate Join", self.simulate_checkin),
                ("Preview Mode: Simulate Add Task", self.simulate_task_added),
                ("Preview Mode: Simulate Done", self.simulate_task_completed),
                ("Preview Mode: Simulate Leave", self.simulate_leave),
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
        layout.addWidget(instructions, 1)
        return card

    def _appearance_tab(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)
        root.setSpacing(Theme.SECTION_SPACING)
        root.addWidget(self._appearance_shapes_card(), 1)
        root.addWidget(self._appearance_names_card(), 1)
        root.addWidget(self._appearance_bubbles_card(), 1)
        return page

    def _appearance_shapes_card(self) -> QFrame:
        card = self._card()
        form = self._form(card, "Shapes")
        for key, label, default in (
            ("circle_color", "Circle color", "#8b5cf6"),
            ("triangle_color", "Triangle color", "#22d3ee"),
            ("square_color", "Square color", "#f97316"),
            ("octagon_color", "Octagon color", "#facc15"),
        ):
            self._line(form, key, label, default)
        self._spin(form, "viewer_shape_size", "Shape size", 24, 160, " px")
        self._spin(form, "outline_width", "Outline width", 0, 16, " px")
        self._line(form, "outline_color", "Outline color", "#1b0b45")
        self._button_row(form, "Save Appearance", self.save_appearance)
        return card

    def _appearance_names_card(self) -> QFrame:
        card = self._card()
        form = self._form(card, "Names")
        self._combo(form, "name_font", "Font", ["Comic Sans MS", "Comic Neue", "Segoe Print", "Segoe UI"])
        self._spin(form, "name_size", "Size", 8, 32, " px")
        self._line(form, "name_color", "Color", "#ffffff")
        self._check(form, "show_names", "Show names")
        self._check(form, "name_shadow", "Show outline/shadow")
        self._button_row(form, "Save Appearance", self.save_appearance)
        return card

    def _appearance_bubbles_card(self) -> QFrame:
        card = self._card()
        form = self._form(card, "Speech Bubbles")
        self._line(form, "bubble_color", "Bubble background", "#1f1830")
        self._spin(form, "bubble_opacity", "Bubble opacity", 0, 100, " %")
        self._line(form, "bubble_text_color", "Text color", "#ffffff")
        self._spin(form, "message_duration", "Duration", 1, 30, " sec")
        self._spin(form, "max_simultaneous_reactions", "Max reactions", 1, 20, "")
        self._button_row(form, "Save Appearance", self.save_appearance)
        return card

    def _messages_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setSpacing(Theme.SECTION_SPACING)
        grid = QGridLayout()
        names = [
            ("checkin", "Check-in messages"),
            ("task_added_self", "When Viewer Adds a Task (Self)"),
            ("task_added_group", "When Viewer Adds a Task (Group)"),
            ("task_completed_self", "When Viewer Completes a Task (Self)"),
            ("task_completed_group", "When Viewer Completes a Task (Group)"),
            ("leave", "Leave messages"),
        ]
        for index, (key, title) in enumerate(names):
            card = self._card()
            box = QVBoxLayout(card)
            box.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
            box.addWidget(QLabel(f"<b>{title}</b>"))
            edit = QTextEdit()
            edit.setPlaceholderText("One phrase per line")
            self.message_fields[key] = edit
            box.addWidget(edit)
            grid.addWidget(card, index // 2, index % 2)
        root.addLayout(grid, 1)
        buttons = QHBoxLayout()
        save = QPushButton("Save Messages")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self.save_messages)
        reset = QPushButton("Reset to Defaults")
        reset.clicked.connect(self.reset_messages)
        buttons.addStretch(1)
        buttons.addWidget(reset)
        buttons.addWidget(save)
        root.addLayout(buttons)
        return page

    def _preview_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setSpacing(Theme.SECTION_SPACING)
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        layout.addWidget(QLabel("<b>Live Preview (Preview Mode)</b>"))
        self.preview = QTextBrowser()
        layout.addWidget(self.preview, 1)
        buttons = QGridLayout()
        for index, (label, callback) in enumerate(
            (
                ("Add Random Viewer", self.simulate_checkin),
                ("Simulate Add Task", self.simulate_task_added),
                ("Simulate Done", self.simulate_task_completed),
                ("Simulate Leave", self.simulate_leave),
                ("Clear All", self.clear_all),
                ("Reset Positions", self.refresh),
            )
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            buttons.addWidget(button, index // 3, index % 3)
        layout.addLayout(buttons)
        root.addWidget(card, 1)
        return page

    def _settings_tab(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)
        root.setSpacing(Theme.SECTION_SPACING)
        root.addWidget(self._layout_settings_card(), 1)
        root.addWidget(self._animation_settings_card(), 1)
        root.addWidget(self._general_settings_card(), 1)
        return page

    def _layout_settings_card(self) -> QFrame:
        card = self._card()
        form = self._form(card, "Layout")
        self._combo(form, "arrangement_mode", "Arrangement", ["Around Streamer", "Grid", "Rows"])
        self._spin(form, "viewer_spacing", "Horizontal spacing", 10, 180, " px")
        self._spin(form, "vertical_spacing", "Vertical spacing", 10, 180, " px")
        self._spin(form, "max_visible_viewers", "Max visible viewers", 1, 100, "")
        self._button_row(form, "Save Settings", self.save_appearance)
        return card

    def _animation_settings_card(self) -> QFrame:
        card = self._card()
        form = self._form(card, "Animations")
        self._combo(form, "join_animation", "Entrance", ["Pop In", "Drop In", "Bounce In", "Fade and Scale"])
        self._combo(form, "idle_animation", "Idle", ["Gentle Bounce", "Floating", "None"])
        self._combo(form, "completion_animation", "Completion", ["Celebrate", "Jump", "Glow Pulse", "Spin Once"])
        self._combo(form, "leave_animation", "Leave", ["Portal Jump", "Fade Only"])
        self._spin(form, "animation_speed", "Animation speed", 25, 200, " %")
        self._check(form, "reduced_motion", "Reduced motion")
        self._button_row(form, "Save Settings", self.save_appearance)
        return card

    def _general_settings_card(self) -> QFrame:
        card = self._card()
        form = self._form(card, "General")
        self._check(form, "show_streamer", "Show streamer (Octagon)")
        self._check(form, "show_speech_bubbles", "Show speech bubbles")
        self._check(form, "enable_reactions", "Enable reactions")
        self._check(form, "restore_active_after_restart", "Restore active check-ins after restart")
        self._button_row(form, "Save Settings", self.save_appearance)
        return card

    def _form(self, card: QFrame, title: str) -> QFormLayout:
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        layout.addWidget(QLabel(f"<b>{title}</b>"))
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        layout.addLayout(form)
        layout.addStretch(1)
        return form

    def _line(self, form: QFormLayout, key: str, label: str, default: str) -> None:
        widget = QLineEdit(default)
        self.appearance_fields[key] = widget
        form.addRow(label, widget)

    def _spin(self, form: QFormLayout, key: str, label: str, minimum: int, maximum: int, suffix: str) -> None:
        widget = QSpinBox()
        widget.setRange(minimum, maximum)
        widget.setSuffix(suffix)
        self.appearance_fields[key] = widget
        form.addRow(label, widget)

    def _combo(self, form: QFormLayout, key: str, label: str, choices: list[str]) -> None:
        widget = QComboBox()
        widget.addItems(choices)
        self.appearance_fields[key] = widget
        form.addRow(label, widget)

    def _check(self, form: QFormLayout, key: str, label: str) -> None:
        widget = QCheckBox(label)
        self.appearance_fields[key] = widget
        form.addRow("", widget)

    @staticmethod
    def _button_row(form: QFormLayout, label: str, callback) -> None:
        button = QPushButton(label)
        button.setObjectName("PrimaryButton")
        button.clicked.connect(callback)
        form.addRow("", button)

    def refresh(self) -> None:
        active = self.service.active_checkins()
        peak = max(int(self.repository.get_setting("checkin_session_peak", 0)), len(active))
        self.repository.set_setting("checkin_session_peak", peak)
        self.overlay_status.setText("Live" if self.overlay_server.running else "Offline")
        self.session_status.setText("Live" if self.overlay_server.running else "Offline")
        self.active_count.setText(str(len(active)))
        self.session_peak.setText(str(peak))
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
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, viewer["user_id"])
            self.tree.addTopLevelItem(item)
        self.preview.setHtml(self._preview_html(active))
        self.load_appearance()
        self.load_messages()

    def load_appearance(self) -> None:
        values = {**DEFAULT_CHECKIN_APPEARANCE, **self.repository.get_setting("checkin_appearance", {})}
        for key, widget in self.appearance_fields.items():
            value = values.get(key)
            if isinstance(widget, QLineEdit):
                widget.setText(str(value if value is not None else ""))
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(value or widget.minimum()))
            elif isinstance(widget, QComboBox):
                index = widget.findText(str(value), Qt.MatchFlag.MatchFixedString)
                widget.setCurrentIndex(max(index, 0))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))

    def save_appearance(self) -> None:
        values = {**DEFAULT_CHECKIN_APPEARANCE, **self.repository.get_setting("checkin_appearance", {})}
        for key, widget in self.appearance_fields.items():
            if isinstance(widget, QLineEdit):
                values[key] = widget.text().strip()
            elif isinstance(widget, QSpinBox):
                values[key] = widget.value()
            elif isinstance(widget, QComboBox):
                values[key] = widget.currentText()
            elif isinstance(widget, QCheckBox):
                values[key] = widget.isChecked()
        self.repository.set_setting("checkin_appearance", values)
        self.repository.set_setting("checkin_restore_active_after_restart", bool(values.get("restore_active_after_restart")))
        self.refresh()

    def load_messages(self) -> None:
        messages = {**DEFAULT_MESSAGE_LISTS, **self.repository.get_setting("checkin_messages", {})}
        for key, edit in self.message_fields.items():
            edit.setPlainText("\n".join(messages.get(key, [])))

    def save_messages(self) -> None:
        payload = {
            key: [line.strip() for line in edit.toPlainText().splitlines() if line.strip()]
            for key, edit in self.message_fields.items()
        }
        self.repository.set_setting("checkin_messages", payload)
        self.load_messages()

    def reset_messages(self) -> None:
        self.repository.set_setting("checkin_messages", DEFAULT_MESSAGE_LISTS)
        self.load_messages()

    def _preview_html(self, active: list[dict]) -> str:
        if not active:
            active = [
                {"display_name": "Killer_Queen55", "shape": "octagon", "color": "#facc15", "is_streamer": True},
                {"display_name": "Alex", "shape": "circle", "color": "#8b5cf6", "is_streamer": False},
                {"display_name": "Jamie", "shape": "triangle", "color": "#22d3ee", "is_streamer": False},
                {"display_name": "FlowFox", "shape": "square", "color": "#f97316", "is_streamer": False},
            ]
        glyphs = {"octagon": "⬣", "circle": "●", "triangle": "▲", "square": "■"}
        html = "<style>.stage{min-height:330px;border:1px solid #303743;border-radius:10px;background:#10151c;padding:22px}.row{display:flex;gap:34px;flex-wrap:wrap;justify-content:center}.a{text-align:center;margin:8px;min-width:120px}.name{max-width:120px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bubble{display:inline-block;border:1px solid #888;border-radius:7px;padding:4px 8px;margin-bottom:8px}.shape{font-size:76px;line-height:80px;text-shadow:0 0 6px #000}.crown{color:#facc15;font-size:22px}</style><div class='stage'><div class='row'>"
        for viewer in active:
            crown = "<div class='crown'>♛</div>" if viewer["shape"] == "octagon" else "<div class='crown'>&nbsp;</div>"
            glyph = glyphs.get(viewer["shape"], "●")
            html += f"<div class='a'><div class='bubble'>Let's study!</div><div class='name'>{escape(viewer['display_name'][:24])}</div>{crown}<div class='shape' style='color:{escape(viewer['color'])}'>{glyph}</div><small>{escape(viewer['shape'])}</small></div>"
        return html + "</div></div>"

    def copy_url(self) -> None:
        QApplication.clipboard().setText(self.overlay_server.checkin_url)

    def preview_overlay(self) -> None:
        if not self.overlay_server.running:
            self.callbacks["start"]()
        webbrowser.open(self.overlay_server.checkin_url)

    def clear_all(self) -> None:
        self.service.clear_active()
        self.refresh()

    def remove_selected(self) -> None:
        item = self.tree.currentItem()
        if not item:
            return
        user_id = item.data(0, Qt.ItemDataRole.UserRole)
        self.service.leave(user_id, item.text(0))
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
