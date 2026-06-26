"""Connections screen for Twitch streamer and optional bot accounts."""

from __future__ import annotations

import threading
import logging
import re
from datetime import datetime, timezone

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .icons import icon
from .storage import TaskRepository
from .theme import Theme
from .twitch.api import TwitchAPIClient
from .twitch.auth import TwitchAuthError, TwitchDeviceAuthClient
from .twitch.chat import (
    BOT_METADATA_KEY,
    MONITORED_CHANNEL_KEY,
    RESPONSE_MODE_AUTOMATIC,
    RESPONSE_MODE_BOT,
    RESPONSE_MODE_KEY,
    RESPONSE_MODE_STREAMER,
    STREAMER_METADATA_KEY,
    TwitchChatCoordinator,
    account_metadata,
)
from .twitch.credentials import BOT_CREDENTIAL_KEY, STREAMER_CREDENTIAL_KEY, TokenCredentialStore
from .twitch.models import DeviceCode, REQUIRED_CHAT_SCOPES, TokenSet, missing_required_scopes


ROLE_LABELS = {"streamer": "Streamer", "bot": "Bot"}
LOG = logging.getLogger(__name__)
CLIENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{20,80}$")
CLIENT_ID_HELP_TEXT = """How to Find Your Twitch Client ID

1. Sign into the Twitch account that will own the Study Budy developer application.
2. Open the Twitch Developer Console.
3. Enable two-factor authentication on that Twitch account if Twitch requires it.
4. Open the Applications section.
5. Choose Register Your Application.
6. Enter an application name such as Study Budy Desktop.
7. Enter the OAuth redirect URL required by the Twitch registration form.
8. Select the most appropriate application category.
9. Create the application.
10. Open Manage for the new application.
11. Copy the value labeled Client ID.
12. Return to Study Budy.
13. Paste it into the Twitch Client ID field.
14. Click Save Client ID.

The Client ID identifies the Study Budy application. It does not connect a Twitch account by itself.

Do not paste your Twitch password, access token, refresh token, or Client Secret into this field.

The same Client ID is used to authorize both your streamer account and your optional bot account.
"""


class TwitchAuthWorker(QThread):
    code_ready = Signal(object)
    status_changed = Signal(str)
    authorized = Signal(str, object, object)
    failed = Signal(str)

    def __init__(self, role: str, client_id: str, scopes: tuple[str, ...]) -> None:
        super().__init__()
        self.role = role
        self.client_id = client_id
        self.scopes = scopes
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        try:
            label = ROLE_LABELS[self.role].lower()
            client = TwitchDeviceAuthClient(self.client_id)
            self.status_changed.emit(f"Requesting Twitch authorization for {label} account...")
            device = client.request_device_code(self.scopes)
            self.code_ready.emit(device)
            self.status_changed.emit(f"Waiting for Twitch authorization for {label} account")
            tokens = client.wait_for_token(device, self.scopes, self.cancel_event, self.status_changed.emit)
            self.status_changed.emit("Authorization approved")
            self.authorized.emit(self.role, device, tokens)
        except TwitchAuthError as exc:
            self.failed.emit(str(exc))


class ConnectionsView(QWidget):
    def __init__(self, repository: TaskRepository, on_refresh) -> None:
        super().__init__()
        self.repository = repository
        self.on_refresh = on_refresh
        self.credential_store = TokenCredentialStore()
        self.chat = TwitchChatCoordinator(repository)
        self.auth_worker: TwitchAuthWorker | None = None
        self.auth_role: str | None = None
        self.current_device: DeviceCode | None = None
        self.code_started_at: datetime | None = None

        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        self.root = QVBoxLayout(content)
        self.root.setContentsMargins(24, 24, 24, 24)
        self.root.setSpacing(Theme.SECTION_SPACING)
        scroll.setWidget(content)
        page.addWidget(scroll)

        title = QLabel("Connections")
        title.setObjectName("H1")
        self.root.addWidget(title)

        client_card = self._card()
        client_layout = QVBoxLayout(client_card)
        client_layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title_row = QHBoxLayout()
        app_title = QLabel("Twitch Application")
        app_title.setObjectName("H2")
        self.client_id_status = QLabel("Not Configured")
        self.client_id_status.setObjectName("StatusBad")
        title_row.addWidget(app_title)
        title_row.addStretch(1)
        title_row.addWidget(self.client_id_status)
        client_layout.addLayout(title_row)
        client_box = QGridLayout()
        client_box.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        self.client_id_help = QPushButton("?")
        self.client_id_help.setFixedWidth(42)
        self.client_id_help.clicked.connect(self.show_client_id_help)
        self.client_id = QLineEdit(self.repository.get_setting("twitch_client_id", ""))
        self.client_id.setPlaceholderText("Twitch Client ID")
        self.save_client_id = QPushButton("Save Client ID")
        self.save_client_id.clicked.connect(self.save_client_id_setting)
        client_box.addWidget(QLabel("Twitch Client ID"), 0, 0)
        client_box.addWidget(self.client_id_help, 0, 1)
        client_box.addWidget(self.client_id, 0, 2)
        client_box.addWidget(self.save_client_id, 0, 3)
        client_layout.addLayout(client_box)
        explanation = QLabel("The Client ID identifies Study Budy to Twitch. It is created in the Twitch Developer Console and is not your username, password, or OAuth token.")
        explanation.setObjectName("SmallNote")
        explanation.setWordWrap(True)
        client_layout.addWidget(explanation)
        self.root.addWidget(client_card)

        self.streamer_card, self.streamer_fields = self._account_card(
            "streamer",
            "Streamer Account",
            "Connect the Twitch account that owns the channel Study Budy should monitor.",
            ("Display name", "Login name", "Twitch user ID", "Channel being monitored", "Authorization status", "Chat-listener status", "Last connection time"),
        )
        self.root.addWidget(self.streamer_card)

        self.bot_card, self.bot_fields = self._account_card(
            "bot",
            "Bot Account",
            "Optional. Connect a separate Twitch account to send Study Budy responses in chat.",
            ("Display name", "Login name", "Twitch user ID", "Authorization status", "Chat-send status", "Last connection time"),
        )
        self.root.addWidget(self.bot_card)

        self._build_chat_configuration()
        self._build_authorization_panel()
        self._build_help_card()
        self._build_preview_tools()
        self.root.addStretch(1)

        self.countdown = QTimer(self)
        self.countdown.setInterval(1000)
        self.countdown.timeout.connect(self.update_countdown)
        self.refresh()

    def _account_card(self, role: str, heading: str, description: str, field_labels: tuple[str, ...]) -> tuple[QFrame, dict[str, QLineEdit]]:
        card = self._card()
        box = QVBoxLayout(card)
        box.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title_row = QHBoxLayout()
        title = QLabel(heading)
        title.setObjectName("H2")
        status = QLabel("Not Connected")
        status.setObjectName("StatusBad")
        setattr(self, f"{role}_status_label", status)
        title_row.addWidget(title)
        title_row.addStretch(1)
        title_row.addWidget(status)
        box.addLayout(title_row)
        copy = QLabel(description)
        copy.setWordWrap(True)
        box.addWidget(copy)
        if role == "bot":
            note = QLabel("The bot account does not need to own the channel. It must be able to join and send messages in the streamer's channel.")
            note.setObjectName("SmallNote")
            note.setWordWrap(True)
            box.addWidget(note)
        fields: dict[str, QLineEdit] = {}
        form = QGridLayout()
        for row, label in enumerate(field_labels):
            field = QLineEdit()
            field.setReadOnly(True)
            fields[label] = field
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(field, row, 1)
        box.addLayout(form)
        buttons = QHBoxLayout()
        button_specs = (
            (f"Connect {ROLE_LABELS[role]} Account", lambda checked=False, role=role: self.connect_account(role), True),
            (f"Test {ROLE_LABELS[role]} Connection", lambda checked=False, role=role: self.test_account(role), False),
            ("Reconnect Chat" if role == "streamer" else "Reconnect Bot", lambda checked=False, role=role: self.test_account(role), False),
            (f"Disconnect {ROLE_LABELS[role]} Account", lambda checked=False, role=role: self.disconnect_account(role), False),
        )
        for label, callback, primary in button_specs:
            button = QPushButton(label)
            if primary:
                button.setObjectName("PrimaryButton")
            button.clicked.connect(callback)
            buttons.addWidget(button)
            setattr(self, f"{role}_{label.lower().replace(' ', '_')}", button)
        box.addLayout(buttons)
        return card, fields

    def _build_chat_configuration(self) -> None:
        card = self._card()
        box = QVBoxLayout(card)
        box.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title = QLabel("Chat Configuration")
        title.setObjectName("H2")
        box.addWidget(title)
        form = QGridLayout()
        self.monitored_channel = QLineEdit(self.chat.monitored_channel())
        self.response_mode = QComboBox()
        self.response_mode.addItems((RESPONSE_MODE_AUTOMATIC, RESPONSE_MODE_BOT, RESPONSE_MODE_STREAMER))
        self.response_mode.setCurrentText(self.chat.response_mode())
        self.response_mode.currentTextChanged.connect(self.save_chat_configuration)
        self.active_response = QLineEdit()
        self.active_response.setReadOnly(True)
        self.listener_status = QLineEdit()
        self.listener_status.setReadOnly(True)
        self.sender_status = QLineEdit()
        self.sender_status.setReadOnly(True)
        form.addWidget(QLabel("Monitored channel"), 0, 0)
        form.addWidget(self.monitored_channel, 0, 1)
        form.addWidget(QLabel("Send chat responses as"), 1, 0)
        form.addWidget(self.response_mode, 1, 1)
        form.addWidget(QLabel("Current active response account"), 2, 0)
        form.addWidget(self.active_response, 2, 1)
        form.addWidget(QLabel("Chat listener status"), 3, 0)
        form.addWidget(self.listener_status, 3, 1)
        form.addWidget(QLabel("Chat sender status"), 4, 0)
        form.addWidget(self.sender_status, 4, 1)
        box.addLayout(form)
        row = QHBoxLayout()
        save = QPushButton("Save Chat Configuration")
        save.clicked.connect(self.save_chat_configuration)
        test = QPushButton("Test Full Chat Flow")
        test.setObjectName("PrimaryButton")
        test.clicked.connect(self.test_full_chat_flow)
        row.addWidget(save)
        row.addWidget(test)
        box.addLayout(row)
        self.flow_result = QLabel("")
        self.flow_result.setWordWrap(True)
        self.explanation = self.flow_result
        box.addWidget(self.flow_result)
        self.root.addWidget(card)

    def _build_authorization_panel(self) -> None:
        self.auth_card = self._card()
        box = QVBoxLayout(self.auth_card)
        box.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        self.auth_title = QLabel("Authorize Study Budy with Twitch")
        self.auth_title.setObjectName("H2")
        box.addWidget(self.auth_title)
        self.auth_hint = QLabel("")
        self.auth_hint.setWordWrap(True)
        box.addWidget(self.auth_hint)
        self.user_code = QLabel("--------")
        self.user_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.user_code.setStyleSheet(f"font-size: 30px; font-weight: 900; letter-spacing: 4px; color: {Theme.PURPLE};")
        box.addWidget(self.user_code)
        buttons = QHBoxLayout()
        for label, callback, primary in (
            ("Open Twitch Authorization", self.open_twitch_authorization, True),
            ("Copy Code", self.copy_code, False),
            ("Generate New Code", self.generate_new_code, False),
            ("Cancel", self.cancel_authorization, False),
        ):
            button = QPushButton(label)
            if primary:
                button.setObjectName("PrimaryButton")
            button.clicked.connect(callback)
            buttons.addWidget(button)
        box.addLayout(buttons)
        self.auth_status = QLabel("")
        self.auth_status.setWordWrap(True)
        self.auth_expiration = QLabel("")
        box.addWidget(self.auth_status)
        box.addWidget(self.auth_expiration)
        self.root.addWidget(self.auth_card)

    def _build_help_card(self) -> None:
        card = self._card()
        box = QVBoxLayout(card)
        box.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title = QLabel("How Twitch Connections Work")
        title.setObjectName("H2")
        box.addWidget(title)
        help_text = QTextBrowser()
        help_text.setHtml(
            """
            <h3>Streamer Account</h3>
            <p>Connect the Twitch account that owns the channel you want Study Budy to monitor. Study Budy reads commands from this channel.</p>
            <h3>Bot Account</h3>
            <p>Connecting a bot account is optional. A bot account lets Study Budy post command responses under a separate Twitch username.</p>
            <p>For example: Streamer channel <b>killer_queen55</b>, Bot account <b>killer_queens_jester</b>.</p>
            <p>The bot joins the streamer's channel and sends Study Budy responses there.</p>
            <h3>Without a bot</h3>
            <p>Study Budy can still work without a bot account. Select Streamer Account or Automatic under Send Chat Responses As.</p>
            <h3>Important</h3>
            <p>Study Budy never asks for or stores Twitch passwords. Streamer and bot accounts are authorized separately. Connecting one account must not disconnect or overwrite the other.</p>
            """
        )
        help_text.setMinimumHeight(260)
        box.addWidget(help_text)
        self.root.addWidget(card)

    def _build_preview_tools(self) -> None:
        card = self._card()
        box = QHBoxLayout(card)
        box.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        for label, callback in (
            ("Enable Preview Mode", self.enable_preview),
            ("Disable Preview Mode", self.disable_preview),
            ("Add Preview Task", self.add_preview_task),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            box.addWidget(button)
        self.root.addWidget(card)

    def save_client_id_setting(self) -> None:
        client_id = self.client_id.text().strip()
        if not client_id:
            self.flow_result.setText("Study Budy needs a Twitch Client ID before it can connect an account. Click the ? icon for setup instructions.")
            self.update_client_id_status()
            return
        if not CLIENT_ID_PATTERN.match(client_id):
            self.flow_result.setText("That Twitch Client ID does not look valid. Copy the Client ID from the Twitch Developer Console.")
            self.update_client_id_status()
            return
        self.repository.set_setting("twitch_client_id", client_id)
        saved = self.repository.get_setting("twitch_client_id", "")
        if saved != client_id:
            self.flow_result.setText("Twitch Client ID could not be saved. Check the application log for details.")
            LOG.error("Twitch Client ID failed storage round trip.")
            return
        self.flow_result.setText("Twitch Client ID saved.")
        self.update_client_id_status()

    def update_client_id_status(self) -> None:
        configured = bool(self.repository.get_setting("twitch_client_id", "").strip())
        self.client_id_status.setText("Configured" if configured else "Not Configured")
        self.client_id_status.setObjectName("StatusGood" if configured else "StatusBad")
        self.client_id_status.style().unpolish(self.client_id_status)
        self.client_id_status.style().polish(self.client_id_status)

    def show_client_id_help(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("How to Find Your Twitch Client ID")
        layout = QVBoxLayout(dialog)
        text = QTextBrowser()
        text.setPlainText(CLIENT_ID_HELP_TEXT)
        text.setMinimumSize(620, 420)
        layout.addWidget(text)
        buttons = QHBoxLayout()
        copy = QPushButton("Copy Developer Console Instructions")
        copy.clicked.connect(lambda: QApplication.clipboard().setText(CLIENT_ID_HELP_TEXT))
        open_console = QPushButton("Open Twitch Developer Console")
        open_console.clicked.connect(self.open_developer_console)
        close = QPushButton("Close")
        close.clicked.connect(dialog.accept)
        buttons.addWidget(copy)
        buttons.addWidget(open_console)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        dialog.exec()

    def open_developer_console(self) -> None:
        if not QDesktopServices.openUrl(QUrl("https://dev.twitch.tv/console/apps")):
            self.flow_result.setText("Study Budy could not open the Twitch Developer Console.")

    def save_chat_configuration(self) -> None:
        self.chat.set_monitored_channel(self.monitored_channel.text())
        self.chat.set_response_mode(self.response_mode.currentText())
        self.refresh()

    def connect_account(self, role: str) -> None:
        LOG.info("%s account connection requested", ROLE_LABELS[role])
        if self.auth_worker and self.auth_worker.isRunning():
            self.flow_result.setText("A Twitch authorization is already in progress.")
            return
        client_id = self.client_id.text().strip() or self.repository.get_setting("twitch_client_id", "")
        if not client_id:
            self.flow_result.setText("Study Budy needs a Twitch Client ID before it can connect an account. Click the ? icon for setup instructions.")
            return
        if not CLIENT_ID_PATTERN.match(client_id):
            self.flow_result.setText("That Twitch Client ID does not look valid. Click the ? icon for setup instructions.")
            return
        self.repository.set_setting("twitch_client_id", client_id)
        self.update_client_id_status()
        self.auth_role = role
        self.current_device = None
        self.code_started_at = None
        self.user_code.setText("--------")
        self.auth_title.setText(f"Authorize Study Budy {ROLE_LABELS[role]} Account")
        self.auth_hint.setText(
            "Sign into the Twitch account you want to use as the Study Budy bot. Do not authorize your streamer account unless you want both roles to use the same account."
            if role == "bot"
            else "Sign into the Twitch account that owns the channel you want Study Budy to monitor."
        )
        self.auth_status.setText(f"Requesting Twitch authorization for {role} account...")
        self.auth_worker = TwitchAuthWorker(role, client_id, REQUIRED_CHAT_SCOPES)
        self.auth_worker.code_ready.connect(self.on_code_ready)
        self.auth_worker.status_changed.connect(self.auth_status.setText)
        self.auth_worker.authorized.connect(self.on_authorized)
        self.auth_worker.failed.connect(self.on_auth_failed)
        self.auth_worker.finished.connect(self.on_auth_finished)
        self._connection_button(role).setEnabled(False)
        self._connection_button(role).setText("Connecting...")
        self.auth_card.setVisible(True)
        self.auth_worker.start()
        self.refresh()

    def connect_streamer(self) -> None:
        self.connect_account("streamer")

    def connect_bot(self) -> None:
        self.connect_account("bot")

    def generate_new_code(self) -> None:
        role = self.auth_role
        self.cancel_authorization()
        if role:
            QTimer.singleShot(150, lambda: self.connect_account(role))

    def open_twitch_authorization(self) -> None:
        if not self.current_device:
            self.flow_result.setText("Study Budy is still waiting for Twitch to create a code.")
            return
        if not QDesktopServices.openUrl(QUrl(self.current_device.verification_uri)):
            self.flow_result.setText("Study Budy could not open the Twitch authorization page.")

    def copy_code(self) -> None:
        QApplication.clipboard().setText(self.user_code.text())
        self.flow_result.setText("Authorization code copied.")

    def cancel_authorization(self) -> None:
        if self.auth_worker and self.auth_worker.isRunning():
            self.auth_worker.cancel()
        self.countdown.stop()
        self.auth_status.setText("Authorization cancelled")
        self.flow_result.setText("Authorization cancelled.")
        self.refresh()

    @Slot(object)
    def on_code_ready(self, device: DeviceCode) -> None:
        self.current_device = device
        self.code_started_at = datetime.now(timezone.utc)
        self.user_code.setText(device.user_code)
        self.countdown.start()
        self.update_countdown()

    @Slot(str, object, object)
    def on_authorized(self, role: str, _device: DeviceCode, tokens: TokenSet) -> None:
        try:
            api = TwitchAPIClient(self.client_id.text().strip())
            validation = api.validate_token(tokens.access_token)
            missing = missing_required_scopes(validation.scopes or tokens.scopes)
            if missing:
                raise TwitchAuthError(f"Required Twitch permissions are missing: {', '.join(missing)}", "missing_scopes")
            user = api.fetch_user(tokens.access_token)
            credential_key = STREAMER_CREDENTIAL_KEY if role == "streamer" else BOT_CREDENTIAL_KEY
            metadata_key = STREAMER_METADATA_KEY if role == "streamer" else BOT_METADATA_KEY
            self.credential_store.save_tokens(credential_key, tokens)
            metadata = account_metadata(role, user, tuple(validation.scopes))
            self.repository.set_setting(metadata_key, metadata)
            self.repository.set_setting("development_bot", False)
            if role == "streamer":
                self.chat.set_monitored_channel(user.login)
                self.monitored_channel.setText(user.login)
            warning = self.chat.same_account_warning()
            self.flow_result.setText(warning or f"{ROLE_LABELS[role]} account connected.")
        except Exception as exc:
            self.flow_result.setText(str(exc))
        finally:
            self.countdown.stop()
            self.refresh()
            self.on_refresh()

    def on_auth_failed(self, message: str) -> None:
        self.auth_status.setText(message)
        self.flow_result.setText(message)
        self.countdown.stop()

    def on_auth_finished(self) -> None:
        self.auth_worker = None
        self.auth_role = None
        self.refresh()

    def update_countdown(self) -> None:
        if not self.current_device or not self.code_started_at:
            self.auth_expiration.setText("")
            return
        elapsed = int((datetime.now(timezone.utc) - self.code_started_at).total_seconds())
        remaining = max(0, self.current_device.expires_in - elapsed)
        self.auth_expiration.setText(f"Code expires in {remaining // 60}:{remaining % 60:02d}")

    def test_account(self, role: str) -> None:
        key = STREAMER_CREDENTIAL_KEY if role == "streamer" else BOT_CREDENTIAL_KEY
        metadata_key = STREAMER_METADATA_KEY if role == "streamer" else BOT_METADATA_KEY
        try:
            tokens = self.credential_store.load_tokens(key)
            account = self.repository.get_setting(metadata_key, None)
            if not tokens or not account:
                self.flow_result.setText(f"{ROLE_LABELS[role]} account is not connected.")
                return
            api = TwitchAPIClient(self.client_id.text().strip())
            validation = api.validate_token(tokens.access_token)
            missing = missing_required_scopes(validation.scopes)
            if missing:
                self.flow_result.setText(f"Required Twitch permissions are missing: {', '.join(missing)}")
                return
            account["last_validated_at"] = account["last_connection_time"] = datetime.now(timezone.utc).isoformat()
            account["authorization_status"] = "Authorized"
            account["chat_status"] = "Ready (chat transport pending)"
            self.repository.set_setting(metadata_key, account)
            self.flow_result.setText(f"{ROLE_LABELS[role]} authorization is valid. Chat transport is ready to be connected.")
        except Exception as exc:
            self.flow_result.setText(str(exc))
        self.refresh()

    def disconnect_account(self, role: str) -> None:
        if QMessageBox.question(self, f"Disconnect {ROLE_LABELS[role]}", f"Disconnect the {ROLE_LABELS[role].lower()} account?") != QMessageBox.StandardButton.Yes:
            return
        key = STREAMER_CREDENTIAL_KEY if role == "streamer" else BOT_CREDENTIAL_KEY
        metadata_key = STREAMER_METADATA_KEY if role == "streamer" else BOT_METADATA_KEY
        self.credential_store.delete_tokens(key)
        self.repository.set_setting(metadata_key, None)
        self.refresh()
        self.on_refresh()

    def test_full_chat_flow(self) -> None:
        self.save_chat_configuration()
        self.flow_result.setText(self.chat.test_full_chat_flow())

    def refresh(self) -> None:
        streamer = self.repository.get_setting(STREAMER_METADATA_KEY, None)
        bot = self.repository.get_setting(BOT_METADATA_KEY, None)
        self.client_id.setText(self.repository.get_setting("twitch_client_id", ""))
        self.update_client_id_status()
        self.monitored_channel.setText(self.chat.monitored_channel())
        self.response_mode.setCurrentText(self.chat.response_mode())
        self._fill_account("streamer", streamer, self.streamer_fields)
        self._fill_account("bot", bot, self.bot_fields)
        active = self.chat.active_response_login()
        self.active_response.setText(f"Responses will be sent as: {active}" if active else "No response account connected")
        self.listener_status.setText(self.chat.listener_status())
        self.sender_status.setText(self.chat.sender_status())
        self.auth_card.setVisible(bool(self.auth_worker and self.auth_worker.isRunning()))
        for role in ("streamer", "bot"):
            button = self._connection_button(role)
            running = bool(self.auth_worker and self.auth_worker.isRunning())
            button.setEnabled(not running)
            button.setText("Connecting..." if running and self.auth_role == role else f"Connect {ROLE_LABELS[role]} Account")

    def _fill_account(self, role: str, account: dict | None, fields: dict[str, QLineEdit]) -> None:
        status = getattr(self, f"{role}_status_label")
        connected = bool(account)
        status.setText("Authorized" if connected else "Not Connected")
        status.setObjectName("StatusGood" if connected else "StatusBad")
        status.style().unpolish(status)
        status.style().polish(status)
        account = account or {}
        mapping = {
            "Display name": account.get("display_name", ""),
            "Login name": account.get("login", ""),
            "Twitch user ID": account.get("user_id", ""),
            "Channel being monitored": self.chat.monitored_channel() if role == "streamer" else "",
            "Authorization status": account.get("authorization_status", "Not connected"),
            "Chat-listener status": self.chat.listener_status() if role == "streamer" else "",
            "Chat-send status": "Available as response sender" if connected else "Not connected",
            "Last connection time": account.get("last_validated_at", ""),
        }
        for label, field in fields.items():
            field.setText(str(mapping.get(label, "")))

    def enable_preview(self) -> None:
        self.repository.set_setting("development_bot", True)
        self.repository.set_setting("preview_bot_name", "killer_queens_jester")
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

    @staticmethod
    def _card() -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        return card

    def _connection_button(self, role: str) -> QPushButton:
        return getattr(self, f"{role}_connect_{ROLE_LABELS[role].lower()}_account")
