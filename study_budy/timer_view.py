"""Desktop control page for the separate Study Timer overlay."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QSignalBlocker

from .icons import icon
from .server import OverlayServer
from .storage import TaskRepository
from .theme import Theme
from .timer.parser import TimerParseError, format_duration
from .timer.service import TimerService


FONT_OPTIONS = ("Press Start 2P", "Segoe UI", "Arial", "Comic Sans MS", "Consolas", "Impact")
LOG = logging.getLogger(__name__)


class TimerView(QWidget):
    def __init__(self, repository: TaskRepository, overlay_server: OverlayServer, callbacks: dict[str, callable]) -> None:
        super().__init__()
        self.repository = repository
        self.overlay_server = overlay_server
        self.callbacks = callbacks
        self.timer = TimerService(repository)
        self.dirty = False
        self.loading_controls = False

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(Theme.SECTION_SPACING)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page = QWidget()
        self.main = QVBoxLayout(page)
        self.main.setSpacing(Theme.SECTION_SPACING)
        self.main.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(page)
        root.addWidget(scroll, 1)

        title = QLabel("Timer")
        title.setObjectName("H1")
        self.main.addWidget(title)
        self._build_status_card()
        self._build_controls_card()
        self._build_appearance_card()
        self._build_instructions_card()
        self.main.addStretch(1)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1000)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start()
        self.refresh()

    def _build_status_card(self) -> None:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title = QLabel("Timer Status")
        title.setObjectName("H2")
        layout.addWidget(title)
        grid = QGridLayout()
        self.overlay_status = QLineEdit()
        self.overlay_status.setReadOnly(True)
        self.chat_status = QLineEdit("Twitch chat connector not connected")
        self.chat_status.setReadOnly(True)
        self.timer_state = QLineEdit()
        self.timer_state.setReadOnly(True)
        self.remaining = QLineEdit()
        self.remaining.setReadOnly(True)
        self.timer_url = QLineEdit()
        self.timer_url.setReadOnly(True)
        for row, (label, field) in enumerate(
            (
                ("Timer overlay status", self.overlay_status),
                ("Chat connection status", self.chat_status),
                ("Timer state", self.timer_state),
                ("Current remaining time", self.remaining),
                ("Timer overlay URL", self.timer_url),
            )
        ):
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(field, row, 1)
        layout.addLayout(grid)
        row = QHBoxLayout()
        for label, callback, primary in (
            ("Copy URL", self.copy_url, True),
            ("Preview Overlay", self.preview_overlay, False),
            ("Refresh Overlay", self.callbacks["restart"], False),
            ("Start Overlay", self.callbacks["start"], False),
            ("Stop Overlay", self.callbacks["stop"], False),
            ("Restart Overlay", self.callbacks["restart"], False),
        ):
            button = QPushButton(label)
            if primary:
                button.setObjectName("PrimaryButton")
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)
        self.main.addWidget(card)

    def _build_controls_card(self) -> None:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title = QLabel("Timer Controls")
        title.setObjectName("H2")
        layout.addWidget(title)
        self.big_timer = QLabel("00:00")
        self.big_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.big_timer.setStyleSheet(f"font-size: 54px; font-weight: 900; color: {Theme.PURPLE};")
        layout.addWidget(self.big_timer)
        self.preview_timer = QLabel("05:00")
        self.preview_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_timer.setStyleSheet("font-size: 64px; font-weight: 900; padding: 18px;")
        layout.addWidget(self.preview_timer)
        input_row = QHBoxLayout()
        input_row.addWidget(QLabel("Time input"))
        self.duration_input = QLineEdit("30:00")
        self.duration_input.setPlaceholderText("30:00, 1:30:00, or 45")
        input_row.addWidget(self.duration_input, 1)
        layout.addLayout(input_row)
        buttons = QGridLayout()
        actions = (
            ("Start Timer", self.start_timer),
            ("Pause", self.pause_timer),
            ("Resume", self.resume_timer),
            ("Add Time", self.add_time),
            ("Subtract Time", self.subtract_time),
            ("Reset", self.reset_timer),
            ("Clear", self.clear_timer),
            ("Complete", self.complete_timer),
        )
        for index, (label, callback) in enumerate(actions):
            button = QPushButton(label)
            if index == 0:
                button.setObjectName("PrimaryButton")
            button.clicked.connect(callback)
            row, column = divmod(index, 4)
            buttons.addWidget(button, row, column)
        layout.addLayout(buttons)
        self.control_message = QLabel("")
        self.control_message.setObjectName("Muted")
        self.control_message.setWordWrap(True)
        layout.addWidget(self.control_message)
        self.main.addWidget(card)

    def _build_appearance_card(self) -> None:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title = QLabel("Timer Appearance")
        title.setObjectName("H2")
        layout.addWidget(title)
        form = QGridLayout()
        self.font_family = QComboBox()
        self.font_family.addItems(FONT_OPTIONS)
        self.font_size = self._spin(16, 300)
        self.font_weight = QComboBox()
        self.font_weight.addItems(("400", "600", "700", "800", "900"))
        self.text_color = QLineEdit("#ffffff")
        self.outline_mode = QComboBox()
        self.outline_mode.addItems(("none", "white", "black", "custom"))
        self.outline_color = QLineEdit("#000000")
        self.outline_width = self._spin(0, 12)
        self.text_opacity = self._spin(0, 100)
        self.letter_spacing = self._spin(-10, 30)
        self.background_enabled = QCheckBox("Background enabled")
        self.background_color = QLineEdit("#000000")
        self.background_opacity = self._spin(0, 100)
        self.padding = self._spin(0, 200)
        self.corner_radius = self._spin(0, 100)
        self.horizontal_align = QComboBox()
        self.horizontal_align.addItems(("left", "center", "right"))
        self.vertical_align = QComboBox()
        self.vertical_align.addItems(("top", "center", "bottom"))
        self.completion_animation = QComboBox()
        self.completion_animation.addItems(("none", "pulse", "bounce", "flash", "fade"))
        self.hide_when_inactive = QCheckBox("Hide when inactive")
        self.continue_after_restart = QCheckBox("Continue running timer after Study Budy restarts")
        rows = (
            ("Font", self.font_family),
            ("Font size", self.font_size),
            ("Font weight", self.font_weight),
            ("Timer color", self._color_row(self.text_color)),
            ("Outline", self.outline_mode),
            ("Outline color", self._color_row(self.outline_color)),
            ("Outline thickness", self.outline_width),
            ("Text opacity", self.text_opacity),
            ("Letter spacing", self.letter_spacing),
            ("Background color", self._color_row(self.background_color)),
            ("Background opacity", self.background_opacity),
            ("Padding", self.padding),
            ("Corner radius", self.corner_radius),
            ("Horizontal alignment", self.horizontal_align),
            ("Vertical alignment", self.vertical_align),
            ("Completion animation", self.completion_animation),
        )
        for row, (label, widget) in enumerate(rows):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(widget, row, 1)
        layout.addLayout(form)
        layout.addWidget(self.background_enabled)
        layout.addWidget(self.hide_when_inactive)
        layout.addWidget(self.continue_after_restart)
        buttons = QHBoxLayout()
        self.save_button = QPushButton("Save Timer Appearance")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.clicked.connect(self.save_appearance)
        self.save_button.setEnabled(False)
        reset = QPushButton("Reset Timer Appearance to Defaults")
        reset.clicked.connect(self.reset_appearance)
        buttons.addWidget(self.save_button)
        buttons.addWidget(reset)
        layout.addLayout(buttons)
        self.dirty_label = QLabel("")
        self.dirty_label.setObjectName("SmallNote")
        layout.addWidget(self.dirty_label)
        self._connect_appearance_signals()
        self.main.addWidget(card)

    def _build_instructions_card(self) -> None:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title = QLabel("How the Study Timer Works")
        title.setObjectName("H2")
        layout.addWidget(title)
        browser = QTextBrowser()
        browser.setHtml(
            """
            <h3>Add the timer to OBS</h3>
            <ol>
              <li>Start the Study Budy overlay service.</li>
              <li>Copy the Timer Overlay URL.</li>
              <li>Open OBS or Streamlabs Desktop.</li>
              <li>Add a new Browser Source.</li>
              <li>Paste the Timer Overlay URL.</li>
              <li>Set the Browser Source background to transparent.</li>
              <li>Resize and position the timer in your scene.</li>
              <li>Keep this as a separate Browser Source from the task and Check-In overlays.</li>
            </ol>
            <h3>Control the timer from Study Budy</h3>
            <p>Enter a duration and use Start, Pause, Resume, Add Time, Subtract Time, Reset, or Clear.
            The timer supports up to 24 hours.</p>
            <p><b>Examples:</b> 30:00 means 30 minutes, 1:30:00 means 1 hour and 30 minutes, 45 means 45 seconds.</p>
            <h3>Control the timer through Twitch chat</h3>
            <p>Broadcasters and moderators can use !ttimer start 30:00, pause, add 05:00, and clear.</p>
            <p>The command intentionally uses two T characters: <b>!ttimer</b>. The timer cannot be set above 24 hours.</p>
            """
        )
        browser.setMinimumHeight(320)
        layout.addWidget(browser)
        self.main.addWidget(card)

    def refresh(self) -> None:
        state = self.timer.state()
        self.overlay_status.setText("Live" if self.overlay_server.running else "Offline")
        self.timer_state.setText(state["state"].title())
        self.remaining.setText(format_duration(state["remaining_seconds"]))
        self.big_timer.setText(format_duration(state["remaining_seconds"]))
        self.timer_url.setText(self.overlay_server.timer_url)
        if not self.dirty:
            self.load_appearance()
        self.apply_preview(self.collect_appearance())

    def load_appearance(self) -> None:
        self.loading_controls = True
        values = self.timer.appearance()
        blockers = [QSignalBlocker(widget) for widget in self._appearance_widgets()]
        try:
            self.font_family.setCurrentText(values["font_family"])
            self.font_size.setValue(int(values["font_size"]))
            self.font_weight.setCurrentText(str(values["font_weight"]))
            self.text_color.setText(values["text_color"])
            self.outline_mode.setCurrentText(values["outline_mode"])
            self.outline_color.setText(values["outline_color"])
            self.outline_width.setValue(int(values["outline_width"]))
            self.text_opacity.setValue(int(values["text_opacity"]))
            self.letter_spacing.setValue(int(values["letter_spacing"]))
            self.background_enabled.setChecked(bool(values["background_enabled"]))
            self.background_color.setText(values["background_color"])
            self.background_opacity.setValue(int(values["background_opacity"]))
            self.padding.setValue(int(values["padding"]))
            self.corner_radius.setValue(int(values["corner_radius"]))
            self.horizontal_align.setCurrentText(values["horizontal_align"])
            self.vertical_align.setCurrentText(values["vertical_align"])
            self.completion_animation.setCurrentText(values["completion_animation"])
            self.hide_when_inactive.setChecked(bool(values["hide_when_inactive"]))
            self.continue_after_restart.setChecked(bool(self.timer.state()["continue_after_restart"]))
        finally:
            del blockers
            self.loading_controls = False
        self.apply_preview(values)

    def save_appearance(self) -> None:
        self.save_button.setEnabled(False)
        try:
            normalized = self.timer.set_appearance(self.collect_appearance())
            self.timer.set_continue_after_restart(self.continue_after_restart.isChecked())
            self.dirty = False
            self.dirty_label.setText("")
            self.control_message.setText("Timer appearance settings saved.")
            self.apply_preview(normalized)
        except Exception:
            LOG.exception("Timer appearance settings could not be saved.")
            self.save_button.setEnabled(True)
            self.control_message.setText("Timer appearance settings could not be saved. Check the application log for details.")
        else:
            self.save_button.setEnabled(False)

    def reset_appearance(self) -> None:
        values = self.timer.reset_appearance()
        self.load_appearance()
        self.dirty = False
        self.save_button.setEnabled(False)
        self.dirty_label.setText("")
        self.apply_preview(values)
        self.control_message.setText("Timer appearance settings saved.")

    def start_timer(self) -> None:
        self._run_action(lambda: self.timer.start(self.duration_input.text()), "Timer started.")

    def pause_timer(self) -> None:
        self._run_action(self.timer.pause, "Timer paused.")

    def resume_timer(self) -> None:
        self._run_action(self.timer.resume, "Timer resumed.")

    def add_time(self) -> None:
        self._run_action(lambda: self.timer.add_time(self.duration_input.text()), "Time added.")

    def subtract_time(self) -> None:
        self._run_action(lambda: self.timer.subtract_time(self.duration_input.text()), "Time subtracted.")

    def reset_timer(self) -> None:
        self._run_action(self.timer.reset, "Timer reset.")

    def clear_timer(self) -> None:
        self._run_action(self.timer.clear, "Timer cleared.")

    def complete_timer(self) -> None:
        self._run_action(self.timer.complete, "Timer completed.")

    def _run_action(self, action, success: str) -> None:
        try:
            action()
        except TimerParseError as exc:
            self.control_message.setText(str(exc))
        else:
            self.control_message.setText(success)
        self.refresh()

    def copy_url(self) -> None:
        QApplication.clipboard().setText(self.overlay_server.timer_url)
        self.control_message.setText("Timer overlay URL copied.")

    def preview_overlay(self) -> None:
        QDesktopServices.openUrl(QUrl(self.overlay_server.timer_url))

    def _spin(self, minimum: int, maximum: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        return spin

    def _color_row(self, field: QLineEdit) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(field, 1)
        button = QPushButton("Pick")
        button.clicked.connect(lambda: self.pick_color(field))
        layout.addWidget(button)
        return row

    def pick_color(self, field: QLineEdit) -> None:
        color = QColorDialog.getColor()
        if color.isValid():
            field.setText(color.name(QColor.NameFormat.HexRgb).upper())

    def collect_appearance(self) -> dict:
        return {
            "font_family": self.font_family.currentText(),
            "font_size": self.font_size.value(),
            "font_weight": int(self.font_weight.currentText()),
            "text_color": self.text_color.text().strip(),
            "outline_mode": self.outline_mode.currentText(),
            "outline_color": self.outline_color.text().strip(),
            "outline_width": self.outline_width.value(),
            "text_opacity": self.text_opacity.value(),
            "letter_spacing": self.letter_spacing.value(),
            "background_enabled": self.background_enabled.isChecked(),
            "background_color": self.background_color.text().strip(),
            "background_opacity": self.background_opacity.value(),
            "padding": self.padding.value(),
            "corner_radius": self.corner_radius.value(),
            "horizontal_align": self.horizontal_align.currentText(),
            "vertical_align": self.vertical_align.currentText(),
            "completion_animation": self.completion_animation.currentText(),
            "hide_when_inactive": self.hide_when_inactive.isChecked(),
        }

    def mark_dirty(self) -> None:
        if self.loading_controls:
            return
        self.dirty = True
        self.save_button.setEnabled(True)
        self.dirty_label.setText("Unsaved changes")
        self.apply_preview(self.timer.normalize_appearance(self.collect_appearance()))

    def apply_preview(self, appearance: dict) -> None:
        values = self.timer.normalize_appearance(appearance)
        outline_width = values["outline_width"]
        outline_color = values["outline_color"]
        background = "transparent"
        if values["background_enabled"]:
            alpha = round(values["background_opacity"] * 2.55)
            background = f"{values['background_color']}{alpha:02X}"
        stroke = "none" if values["outline_mode"] == "none" or outline_width <= 0 else f"0 0 {outline_width + 1}px {outline_color}"
        self.preview_timer.setStyleSheet(
            f"font-family: '{values['font_family']}', Consolas, monospace;"
            f"font-size: {values['font_size']}px;"
            f"font-weight: {values['font_weight']};"
            f"color: {values['text_color']};"
            f"opacity: {values['text_opacity'] / 100};"
            f"letter-spacing: {values['letter_spacing']}px;"
            f"background: {background};"
            f"padding: {values['padding']}px;"
            f"border-radius: {values['corner_radius']}px;"
            f"text-shadow: {stroke};"
        )

    def _connect_appearance_signals(self) -> None:
        for combo in (self.font_family, self.font_weight, self.outline_mode, self.horizontal_align, self.vertical_align, self.completion_animation):
            combo.currentTextChanged.connect(self.mark_dirty)
        for spin in (self.font_size, self.outline_width, self.text_opacity, self.letter_spacing, self.background_opacity, self.padding, self.corner_radius):
            spin.valueChanged.connect(self.mark_dirty)
        for field in (self.text_color, self.outline_color, self.background_color):
            field.textChanged.connect(self.mark_dirty)
        for checkbox in (self.background_enabled, self.hide_when_inactive, self.continue_after_restart):
            checkbox.toggled.connect(self.mark_dirty)

    def _appearance_widgets(self) -> list[QWidget]:
        return [
            self.font_family, self.font_size, self.font_weight, self.text_color, self.outline_mode,
            self.outline_color, self.outline_width, self.text_opacity, self.letter_spacing,
            self.background_enabled, self.background_color, self.background_opacity, self.padding,
            self.corner_radius, self.horizontal_align, self.vertical_align, self.completion_animation,
            self.hide_when_inactive, self.continue_after_restart,
        ]

    @staticmethod
    def _card() -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        return card
