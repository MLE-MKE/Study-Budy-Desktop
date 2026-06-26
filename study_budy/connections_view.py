"""Connections screen for Twitch, OBS, and preview-mode state."""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .icons import icon
from .storage import TaskRepository, now
from .theme import Theme
from .twitch.api import TwitchAPIClient
from .twitch.auth import TwitchAuthError, TwitchDeviceAuthClient
from .twitch.credentials import STREAMER_ACCOUNT, TokenCredentialStore
from .twitch.models import DeviceCode, REQUIRED_CHAT_SCOPES, StreamerAccount, TokenSet, missing_required_scopes


class TwitchAuthWorker(QThread):
    code_ready = Signal(object)
    status_changed = Signal(str)
    authorized = Signal(object, object)
    failed = Signal(str)

    def __init__(self, client_id: str, scopes: tuple[str, ...]) -> None:
        super().__init__()
        self.client_id = client_id
        self.scopes = scopes
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        try:
            client = TwitchDeviceAuthClient(self.client_id)
            self.status_changed.emit("Requesting authorization code")
            device = client.request_device_code(self.scopes)
            self.code_ready.emit(device)
            self.status_changed.emit("Waiting for Twitch authorization")
            tokens = client.wait_for_token(device, self.scopes, self.cancel_event, self.status_changed.emit)
            self.status_changed.emit("Authorization approved")
            self.authorized.emit(device, tokens)
        except TwitchAuthError as exc:
            self.failed.emit(str(exc))


class ConnectionsView(QWidget):
    def __init__(self, repository: TaskRepository, on_refresh) -> None:
        super().__init__()
        self.repository = repository
        self.on_refresh = on_refresh
        self.credential_store = TokenCredentialStore()
        self.auth_worker: TwitchAuthWorker | None = None
        self.current_device: DeviceCode | None = None
        self.code_started_at: datetime | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(Theme.SECTION_SPACING)
        title = QLabel("Connections")
        title.setObjectName("H1")
        root.addWidget(title)

        self.streamer_card = QFrame()
        self.streamer_card.setObjectName("Card")
        self.streamer_box = QVBoxLayout(self.streamer_card)
        self.streamer_box.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        self.streamer_box.setSpacing(Theme.SECTION_SPACING)
        root.addWidget(self.streamer_card)

        self._build_streamer_account()
        self._build_instructions()
        self._build_preview_tools(root)
        root.addStretch(1)

        self.countdown = QTimer(self)
        self.countdown.setInterval(1000)
        self.countdown.timeout.connect(self.update_countdown)
        self.refresh()

    def _build_streamer_account(self) -> None:
        heading_row = QHBoxLayout()
        heading = QLabel("Streamer Account")
        heading.setObjectName("H2")
        heading_row.addWidget(heading)
        heading_row.addStretch(1)
        self.connection_status = QLabel("Status: Not Connected")
        self.connection_status.setObjectName("StatusBad")
        heading_row.addWidget(self.connection_status)
        self.streamer_box.addLayout(heading_row)

        self.explanation = QLabel("Connect the Twitch account that owns the channel where Study Budy will be used.")
        self.explanation.setWordWrap(True)
        self.streamer_box.addWidget(self.explanation)

        client_row = QGridLayout()
        self.client_id = QLineEdit()
        self.client_id.setPlaceholderText("Twitch Client ID")
        self.client_id.setText(self.repository.get_setting("twitch_client_id", ""))
        self.save_client_id = QPushButton("Save Client ID")
        self.save_client_id.clicked.connect(self.save_client_id_setting)
        client_row.addWidget(QLabel("Twitch Client ID"), 0, 0)
        client_row.addWidget(self.client_id, 0, 1)
        client_row.addWidget(self.save_client_id, 0, 2)
        self.streamer_box.addLayout(client_row)

        self.disconnected_area = QWidget()
        disconnected = QVBoxLayout(self.disconnected_area)
        disconnected.setContentsMargins(0, 0, 0, 0)
        self.connect_button = QPushButton("Connect Streamer Account")
        self.connect_button.setObjectName("PrimaryButton")
        self.connect_button.setIcon(icon("twitch"))
        self.connect_button.clicked.connect(self.connect_streamer)
        disconnected.addWidget(self.connect_button)
        privacy = QLabel("Study Budy will never ask for or store your Twitch password.")
        privacy.setObjectName("SmallNote")
        privacy.setWordWrap(True)
        disconnected.addWidget(privacy)
        self.streamer_box.addWidget(self.disconnected_area)

        self.auth_area = QWidget()
        auth = QVBoxLayout(self.auth_area)
        auth.setContentsMargins(0, 0, 0, 0)
        auth_title = QLabel("Authorize Study Budy with Twitch")
        auth_title.setObjectName("H2")
        auth.addWidget(auth_title)
        self.user_code = QLabel("--------")
        self.user_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.user_code.setStyleSheet(f"font-size: 30px; font-weight: 900; letter-spacing: 4px; color: {Theme.PURPLE};")
        auth.addWidget(self.user_code)
        auth_buttons = QHBoxLayout()
        for label, callback, primary in (
            ("Copy Code", self.copy_code, False),
            ("Open Twitch Authorization", self.open_twitch_authorization, True),
            ("Generate New Code", self.generate_new_code, False),
            ("Cancel", self.cancel_authorization, False),
        ):
            button = QPushButton(label)
            if primary:
                button.setObjectName("PrimaryButton")
            button.clicked.connect(callback)
            auth_buttons.addWidget(button)
            setattr(self, label.lower().replace(" ", "_"), button)
        auth.addLayout(auth_buttons)
        self.auth_status = QLabel("Requesting authorization code")
        self.auth_status.setWordWrap(True)
        self.auth_expiration = QLabel("")
        auth.addWidget(self.auth_status)
        auth.addWidget(self.auth_expiration)
        self.streamer_box.addWidget(self.auth_area)

        self.connected_area = QWidget()
        connected = QVBoxLayout(self.connected_area)
        connected.setContentsMargins(0, 0, 0, 0)
        self.connected_form = QGridLayout()
        self.connected_fields: dict[str, QLineEdit] = {}
        for row, label in enumerate(
            (
                "Twitch display name",
                "Twitch login name",
                "Twitch user ID",
                "Channel name",
                "Authorization status",
                "Chat connection status",
                "Last successful connection time",
            )
        ):
            field = QLineEdit()
            field.setReadOnly(True)
            self.connected_fields[label] = field
            self.connected_form.addWidget(QLabel(label), row, 0)
            self.connected_form.addWidget(field, row, 1)
        connected.addLayout(self.connected_form)
        connected_buttons = QHBoxLayout()
        for label, callback, primary in (
            ("Test Connection", self.test_connection, True),
            ("Reconnect Chat", self.reconnect, False),
            ("Disconnect Account", self.disconnect, False),
        ):
            button = QPushButton(label)
            if primary:
                button.setObjectName("PrimaryButton")
            button.clicked.connect(callback)
            connected_buttons.addWidget(button)
        connected.addLayout(connected_buttons)
        self.streamer_box.addWidget(self.connected_area)

    def _build_instructions(self) -> None:
        card = QFrame()
        card.setObjectName("Card")
        box = QVBoxLayout(card)
        box.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title = QLabel("How to connect your streamer account")
        title.setObjectName("H2")
        box.addWidget(title)
        steps = QTextBrowser()
        steps.setOpenExternalLinks(False)
        steps.setHtml(
            """
            <ol>
              <li>Click Connect Streamer Account.</li>
              <li>Study Budy will create a temporary Twitch authorization code.</li>
              <li>Click Open Twitch Authorization.</li>
              <li>Sign into the Twitch account that owns the channel.</li>
              <li>Enter the displayed code if Twitch asks for it.</li>
              <li>Review the requested permissions.</li>
              <li>Click Authorize.</li>
              <li>Return to Study Budy and wait for the account to show Connected.</li>
            </ol>
            <p><b>Note:</b> If the wrong Twitch account opens, cancel the process, sign out of Twitch in the browser
            or use a private browser window, and try again.</p>
            """
        )
        steps.setMaximumHeight(210)
        box.addWidget(steps)
        self.streamer_box.addWidget(card)

    def _build_preview_tools(self, root: QVBoxLayout) -> None:
        card = QFrame()
        card.setObjectName("Card")
        box = QVBoxLayout(card)
        box.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title = QLabel("Preview and Test Tools")
        title.setObjectName("H2")
        box.addWidget(title)
        self.channel_name = QLineEdit()
        self.channel_name.setPlaceholderText("Optional channel override")
        self.channel_name.setText(self.repository.get_setting("twitch_channel", ""))
        box.addWidget(self.channel_name)
        buttons = QHBoxLayout()
        for label, callback in (
            ("Enable Preview Mode", self.connect_bot),
            ("Disable Preview Mode", self.disable_preview),
            ("Add Preview Task", self.add_preview_task),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        box.addLayout(buttons)
        note = QLabel("Preview Mode simulates Twitch readiness without storing Twitch credentials.")
        note.setObjectName("SmallNote")
        note.setWordWrap(True)
        box.addWidget(note)
        root.addWidget(card)

    def save_client_id_setting(self) -> None:
        self.repository.set_setting("twitch_client_id", self.client_id.text().strip())
        self.repository.set_setting("twitch_channel", self.channel_name.text().strip().lstrip("#"))
        self.set_message("Twitch Client ID saved.")

    def refresh(self) -> None:
        account = self.repository.get_setting("twitch_streamer_account", None)
        self.client_id.setText(self.repository.get_setting("twitch_client_id", ""))
        self.channel_name.setText(self.repository.get_setting("twitch_channel", ""))
        connected = bool(account)
        authorizing = bool(self.auth_worker and self.auth_worker.isRunning())
        self.disconnected_area.setVisible(not connected and not authorizing)
        self.auth_area.setVisible(authorizing)
        self.connected_area.setVisible(connected and not authorizing)
        self.connection_status.setText("Status: Connected" if connected else "Status: Not Connected")
        self.connection_status.setObjectName("StatusGood" if connected else "StatusBad")
        self.connection_status.style().unpolish(self.connection_status)
        self.connection_status.style().polish(self.connection_status)
        if account:
            self.fill_connected_account(account)

    def fill_connected_account(self, account: dict) -> None:
        values = {
            "Twitch display name": account.get("display_name", ""),
            "Twitch login name": account.get("login", ""),
            "Twitch user ID": account.get("user_id", ""),
            "Channel name": account.get("channel", account.get("login", "")),
            "Authorization status": "Valid or ready to validate",
            "Chat connection status": account.get("chat_status", "Not connected"),
            "Last successful connection time": account.get("last_validated_at", ""),
        }
        for label, value in values.items():
            self.connected_fields[label].setText(str(value))

    def connect_streamer(self) -> None:
        if self.auth_worker and self.auth_worker.isRunning():
            self.set_message("A Twitch authorization is already in progress.")
            return
        self.save_client_id_setting()
        client_id = self.client_id.text().strip()
        if not client_id:
            self.set_message("Enter a Twitch Client ID before connecting.")
            return
        self.current_device = None
        self.user_code.setText("--------")
        self.auth_status.setText("Requesting authorization code")
        self.auth_worker = TwitchAuthWorker(client_id, REQUIRED_CHAT_SCOPES)
        self.auth_worker.code_ready.connect(self.on_code_ready)
        self.auth_worker.status_changed.connect(self.auth_status.setText)
        self.auth_worker.authorized.connect(self.on_authorized)
        self.auth_worker.failed.connect(self.on_auth_failed)
        self.auth_worker.finished.connect(self.on_auth_finished)
        self.auth_worker.start()
        self.refresh()

    def generate_new_code(self) -> None:
        self.cancel_authorization()
        QTimer.singleShot(150, self.connect_streamer)

    def copy_code(self) -> None:
        QApplication.clipboard().setText(self.user_code.text())
        self.set_message("Authorization code copied.")

    def open_twitch_authorization(self) -> None:
        if not self.current_device:
            self.set_message("Study Budy is still waiting for Twitch to create a code.")
            return
        QDesktopServices.openUrl(QUrl(self.current_device.verification_uri))

    def cancel_authorization(self) -> None:
        if self.auth_worker and self.auth_worker.isRunning():
            self.auth_worker.cancel()
            self.auth_status.setText("Authorization cancelled")
        self.countdown.stop()
        self.refresh()

    @Slot(object)
    def on_code_ready(self, device: DeviceCode) -> None:
        self.current_device = device
        self.code_started_at = datetime.now(timezone.utc)
        self.user_code.setText(device.user_code)
        self.countdown.start()
        self.update_countdown()

    @Slot(object, object)
    def on_authorized(self, _device: DeviceCode, tokens: TokenSet) -> None:
        try:
            api = TwitchAPIClient(self.client_id.text().strip())
            validation = api.validate_token(tokens.access_token)
            missing = missing_required_scopes(validation.scopes or tokens.scopes)
            if missing:
                raise TwitchAuthError(f"Required Twitch permissions are missing: {', '.join(missing)}", "missing_scopes")
            user = api.fetch_user(tokens.access_token)
            self.credential_store.save_tokens(STREAMER_ACCOUNT, tokens)
            timestamp = now()
            account = StreamerAccount(
                user_id=user.user_id,
                login=user.login,
                display_name=user.display_name,
                channel=user.login,
                granted_scopes=tuple(validation.scopes),
                connected_at=timestamp,
                last_validated_at=timestamp,
            )
            self.repository.set_setting("twitch_streamer_account", account.__dict__)
            self.repository.set_setting("twitch_channel", user.login)
            self.repository.set_setting("development_bot", False)
            self.auth_status.setText("Authorization approved")
        except Exception as exc:
            self.set_message(str(exc))
        finally:
            self.countdown.stop()
            self.refresh()
            self.on_refresh()

    def on_auth_failed(self, message: str) -> None:
        self.auth_status.setText(message)
        self.set_message(message)
        self.countdown.stop()

    def on_auth_finished(self) -> None:
        self.refresh()

    def update_countdown(self) -> None:
        if not self.current_device or not self.code_started_at:
            self.auth_expiration.setText("")
            return
        elapsed = int((datetime.now(timezone.utc) - self.code_started_at).total_seconds())
        remaining = max(0, self.current_device.expires_in - elapsed)
        self.auth_expiration.setText(f"Code expires in {remaining // 60}:{remaining % 60:02d}")
        if remaining <= 0:
            self.countdown.stop()
            self.auth_status.setText("Authorization expired")

    def test_connection(self) -> None:
        try:
            tokens = self.credential_store.load_tokens(STREAMER_ACCOUNT)
            if not tokens:
                self.set_message("Authorization expired. Reconnect your account.")
                return
            client_id = self.client_id.text().strip()
            api = TwitchAPIClient(client_id)
            validation = api.validate_token(tokens.access_token)
            missing = missing_required_scopes(validation.scopes)
            if missing:
                self.set_message("Required Twitch permissions are missing.")
                return
            user = api.fetch_user(tokens.access_token)
            account = self.repository.get_setting("twitch_streamer_account", {}) or {}
            if account and account.get("user_id") != user.user_id:
                self.set_message("The stored Twitch account does not match the current authorization.")
                return
            account.update({"last_validated_at": now(), "chat_status": "Chat connector not connected"})
            self.repository.set_setting("twitch_streamer_account", account)
            self.set_message("Authorization is valid, but chat could not connect.")
            self.refresh()
        except Exception as exc:
            self.set_message(str(exc))

    def reconnect(self) -> None:
        self.test_connection()

    def disconnect(self) -> None:
        if QMessageBox.question(self, "Disconnect Twitch", "Disconnect the Twitch streamer account?") != QMessageBox.StandardButton.Yes:
            return
        self.cancel_authorization()
        self.credential_store.delete_tokens(STREAMER_ACCOUNT)
        self.repository.set_setting("twitch_streamer_account", None)
        self.refresh()
        self.on_refresh()

    def connect_bot(self) -> None:
        self.repository.set_setting("development_bot", True)
        self.repository.set_setting("preview_bot_name", "killer_queens_jester")
        self.repository.set_setting("twitch_channel", self.channel_name.text().strip().lstrip("#"))
        self.refresh()
        self.on_refresh()

    def disable_preview(self) -> None:
        self.repository.set_setting("development_bot", False)
        self.refresh()
        self.on_refresh()

    def add_preview_task(self) -> None:
        self.repository.add_task("killer_queens_jester", "Preview test task from Twitch chat")
        self.refresh()
        self.on_refresh()

    def set_message(self, message: str) -> None:
        self.explanation.setText(message)
