"""Connections screen for Twitch streamer and optional bot accounts."""

from __future__ import annotations

import threading
import logging
import re
from dataclasses import dataclass
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
AUTH_IDLE = "Idle"
AUTH_REQUESTING = "Requesting Code"
AUTH_WAITING = "Waiting for Authorization"
AUTH_AUTHORIZED = "Authorized"
AUTH_DENIED = "Denied"
AUTH_EXPIRED = "Expired"
AUTH_CANCELLED = "Cancelled"
AUTH_FAILED = "Failed"
CLIENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{20,80}$")
CLIENT_ID_HELP_TEXT = """Twitch Client ID Setup

Most users only need to do this once.

What is a Client ID?

A Client ID is the public app ID Twitch gives to Study Budy. It is not your Twitch username, password, token, or Client Secret.

Create one in Twitch

1. Open the Twitch Developer Console:
   https://dev.twitch.tv/console/apps
2. Sign in with the Twitch account you want to use to manage the app.
3. If Twitch asks for two-factor authentication, turn it on for that Twitch account.
4. Click Register Your Application.
5. Name it something simple, such as:
   Study Budy Desktop
6. Twitch will ask for an OAuth Redirect URL.
   You do not need to find one in Study Budy. Study Budy uses a code-based Twitch login flow, but Twitch still requires this box when creating an app.
   In the OAuth Redirect URL box, enter:
   http://localhost
7. If Twitch asks for more than one redirect URL, only one is needed for Study Budy.
8. For Category, choose Application Integration.
   If Twitch changes the category list and Application Integration is not shown, choose Chat Bot, Tool, or Other as the closest match.
9. If Twitch asks for Client Type, choose Public.
   Do not choose Confidential for Study Budy Desktop. Public is correct because Study Budy runs on your computer and does not need a Client Secret.
10. Click Create.
11. Open Manage for the app you just created.
12. Copy the value named Client ID.

Add it to Study Budy

1. Return to Study Budy.
2. Paste only the Client ID into the Twitch Client ID box.
3. Click Save Client ID.
4. Then connect your Streamer Account.
5. Optional: connect your Bot Account if you want chat replies to come from a separate bot username.

Important safety notes

- Do not paste your Twitch password.
- Do not paste a Client Secret.
- Do not paste an access token or refresh token.
- The same Client ID can be used for both the streamer account and bot account.

If chat stays stuck on Connecting after changing scopes, disconnect and reconnect the streamer account so Twitch can grant the new chat permissions.
"""


@dataclass
class AuthorizationContext:
    role: str
    state: str = AUTH_IDLE
    worker: "TwitchAuthWorker | None" = None
    device: DeviceCode | None = None
    started_at: datetime | None = None
    message: str = ""


class TwitchAuthWorker(QThread):
    code_ready = Signal(object)
    status_changed = Signal(str)
    authorized = Signal(str, object, object)
    failed = Signal(str, str)

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
            LOG.info("%s device-code request started", ROLE_LABELS[self.role])
            self.status_changed.emit(f"Requesting Twitch authorization for {label} account...")
            device = client.request_device_code(self.scopes)
            LOG.info("%s device-code response received", ROLE_LABELS[self.role])
            self.code_ready.emit(device)
            self.status_changed.emit(f"Waiting for Twitch authorization for {label} account")
            LOG.info("%s authorization polling started", ROLE_LABELS[self.role])
            tokens = client.wait_for_token(device, self.scopes, self.cancel_event, self.status_changed.emit)
            LOG.info("%s authorization approved", ROLE_LABELS[self.role])
            self.status_changed.emit("Authorization approved")
            self.authorized.emit(self.role, device, tokens)
        except TwitchAuthError as exc:
            LOG.info("%s authorization ended: %s", ROLE_LABELS[self.role], exc.code)
            self.failed.emit(self.role, str(exc))
        except Exception:
            LOG.exception("%s authorization worker failed", ROLE_LABELS.get(self.role, self.role))
            self.failed.emit(self.role, "Study Budy hit an unexpected error while connecting to Twitch.")


class ConnectionsView(QWidget):
    def __init__(self, repository: TaskRepository, on_refresh) -> None:
        super().__init__()
        self.repository = repository
        self.on_refresh = on_refresh
        self.credential_store = TokenCredentialStore()
        self.chat = TwitchChatCoordinator(repository, credential_store=self.credential_store, client_id_getter=self._client_id_value)
        self.auth_worker: TwitchAuthWorker | None = None
        self.auth_role: str | None = None
        self.current_device: DeviceCode | None = None
        self.code_started_at: datetime | None = None
        self.auth_context: AuthorizationContext | None = None
        self.client_id_dirty = False

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
        self.client_id.textEdited.connect(self.on_client_id_edited)
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
        self.chat_status_timer = QTimer(self)
        self.chat_status_timer.setInterval(2000)
        self.chat_status_timer.timeout.connect(self.refresh)
        self.chat_status_timer.start()
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

    def on_client_id_edited(self, _text: str) -> None:
        self.client_id_dirty = True
        saved = self.repository.get_setting("twitch_client_id", "").strip()
        current = self.client_id.text().strip()
        if current and current != saved:
            self.client_id_status.setText("Unsaved Changes")
            self.client_id_status.setObjectName("StatusBad")
            self.client_id_status.style().unpolish(self.client_id_status)
            self.client_id_status.style().polish(self.client_id_status)

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
        self.client_id_dirty = False
        self.client_id.setText(saved)
        self.flow_result.setText("Twitch Client ID saved.")
        self.update_client_id_status()

    def update_client_id_status(self) -> None:
        saved = self.repository.get_setting("twitch_client_id", "").strip()
        current = self.client_id.text().strip()
        unsaved = self.client_id_dirty and current != saved
        configured = bool(saved)
        self.client_id_status.setText("Unsaved Changes" if unsaved else ("Configured" if configured else "Not Configured"))
        self.client_id_status.setObjectName("StatusBad" if unsaved or not configured else "StatusGood")
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
        if self._authorization_in_progress():
            self.flow_result.setText("Finish or cancel the current Twitch authorization before connecting another account.")
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
        self.auth_context = AuthorizationContext(
            role=role,
            state=AUTH_REQUESTING,
            message=f"Requesting Twitch authorization for {role} account...",
        )
        self.current_device = None
        self.code_started_at = None
        self.user_code.setText("--------")
        self.auth_expiration.setText("")
        self.auth_title.setText(f"Authorize Study Budy {ROLE_LABELS[role]} Account")
        self.auth_hint.setText(
            "Sign into the Twitch account you want to use as the Study Budy bot. Do not authorize your streamer account unless you want both roles to use the same account."
            if role == "bot"
            else "Sign into the Twitch account that owns the channel you want Study Budy to monitor."
        )
        self.auth_status.setText(self.auth_context.message)
        self.flow_result.setText(self.auth_context.message)
        self.auth_worker = TwitchAuthWorker(role, client_id, REQUIRED_CHAT_SCOPES)
        self.auth_context.worker = self.auth_worker
        self.auth_worker.code_ready.connect(self.on_code_ready)
        self.auth_worker.status_changed.connect(self.on_auth_status_changed)
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
        if self.auth_context:
            self.auth_context.state = AUTH_CANCELLED
            self.auth_context.message = "Authorization cancelled."
        if self.auth_worker and self.auth_worker.isRunning():
            self.auth_worker.cancel()
        self.countdown.stop()
        self.auth_status.setText("Authorization cancelled")
        self.flow_result.setText("Authorization cancelled.")
        self._clear_authorization_panel()
        self.refresh()

    @Slot(object)
    def on_code_ready(self, device: DeviceCode) -> None:
        self.current_device = device
        self.code_started_at = datetime.now(timezone.utc)
        if self.auth_context:
            self.auth_context.state = AUTH_WAITING
            self.auth_context.device = device
            self.auth_context.started_at = self.code_started_at
            self.auth_context.message = "Waiting for Twitch authorization"
        self.user_code.setText(device.user_code)
        self.countdown.start()
        self.update_countdown()

    @Slot(str)
    def on_auth_status_changed(self, message: str) -> None:
        if self.auth_context:
            self.auth_context.message = message
            if "waiting" in message.casefold():
                self.auth_context.state = AUTH_WAITING
        self.auth_status.setText(message)

    @Slot(str, object, object)
    def on_authorized(self, role: str, _device: DeviceCode, tokens: TokenSet) -> None:
        try:
            LOG.info("%s token validation started", ROLE_LABELS[role])
            api = TwitchAPIClient(self.client_id.text().strip())
            validation = api.validate_token(tokens.access_token)
            missing = missing_required_scopes(validation.scopes or tokens.scopes)
            if missing:
                raise TwitchAuthError(f"Required Twitch permissions are missing: {', '.join(missing)}", "missing_scopes")
            LOG.info("%s token validation succeeded", ROLE_LABELS[role])
            user = api.fetch_user(tokens.access_token)
            LOG.info("%s user lookup succeeded for %s", ROLE_LABELS[role], user.login)
            credential_key = STREAMER_CREDENTIAL_KEY if role == "streamer" else BOT_CREDENTIAL_KEY
            metadata_key = STREAMER_METADATA_KEY if role == "streamer" else BOT_METADATA_KEY
            self.credential_store.save_tokens(credential_key, tokens)
            LOG.info("%s credential storage succeeded", ROLE_LABELS[role])
            metadata = account_metadata(role, user, tuple(validation.scopes))
            if role == "streamer":
                metadata["chat_status"] = "Authorized. Live chat connection is not implemented yet."
            else:
                metadata["chat_status"] = f"Ready to respond as {user.login}. Live chat sending is not implemented yet."
            self.repository.set_setting(metadata_key, metadata)
            self.repository.set_setting("development_bot", False)
            if role == "streamer":
                self.chat.set_monitored_channel(user.login)
                self.monitored_channel.setText(user.login)
                listener_status = self.chat.start_listener(self.credential_store, self._client_id_value)
                LOG.info("Twitch chat listener startup: %s", listener_status)
            if role == "bot" and self.response_mode.currentText() == RESPONSE_MODE_AUTOMATIC:
                self.chat.set_response_mode(RESPONSE_MODE_AUTOMATIC)
            sender_status = self.chat.prepare_sender(self.credential_store, self._client_id_value)
            LOG.info("Twitch chat sender readiness: %s", sender_status)
            warning = self.chat.same_account_warning()
            if self.auth_context:
                self.auth_context.state = AUTH_AUTHORIZED
                self.auth_context.message = f"{ROLE_LABELS[role]} account authorized."
            self.flow_result.setText(
                warning
                or (
                    f"{ROLE_LABELS[role]} account authorized. "
                    f"{self.chat.listener_status()} {self.chat.sender_status()}"
                )
            )
            self._clear_authorization_panel()
        except Exception as exc:
            LOG.exception("%s authorization success cleanup failed", ROLE_LABELS.get(role, role))
            if self.auth_context:
                self.auth_context.state = AUTH_FAILED
                self.auth_context.message = str(exc)
            self.auth_status.setText(str(exc))
            self.flow_result.setText(str(exc))
        finally:
            self.countdown.stop()
            self.refresh()
            self.on_refresh()

    def on_auth_failed(self, role: str, message: str) -> None:
        lower = message.casefold()
        if self.auth_context:
            if "denied" in lower:
                self.auth_context.state = AUTH_DENIED
            elif "expired" in lower:
                self.auth_context.state = AUTH_EXPIRED
            elif "cancel" in lower:
                self.auth_context.state = AUTH_CANCELLED
            else:
                self.auth_context.state = AUTH_FAILED
            self.auth_context.message = message
        LOG.info("%s authorization terminal failure: %s", ROLE_LABELS.get(role, role), message)
        self.auth_status.setText(message)
        self.flow_result.setText(message)
        self.countdown.stop()
        self._clear_authorization_panel()
        self.refresh()

    def on_auth_finished(self) -> None:
        LOG.info("Twitch authorization worker cleanup completed")
        self.auth_worker = None
        if self.auth_context and self.auth_context.state in {AUTH_REQUESTING, AUTH_WAITING}:
            self.auth_context.state = AUTH_FAILED
            self.auth_context.message = "Twitch authorization stopped before it completed."
            self.flow_result.setText(self.auth_context.message)
            self._clear_authorization_panel()
        if not self._authorization_in_progress():
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
            if role == "streamer":
                account["chat_status"] = self.chat.start_listener(self.credential_store, self._client_id_value)
            else:
                account["chat_status"] = self.chat.prepare_sender(self.credential_store, self._client_id_value)
            self.repository.set_setting(metadata_key, account)
            self.flow_result.setText(f"{ROLE_LABELS[role]} authorization is valid. {account['chat_status']}")
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
        if role == "streamer":
            self.chat.stop_listener()
            self.repository.set_setting("twitch_listener_status", "Not connected")
        if role == "bot":
            self.repository.set_setting("twitch_sender_status", "Not connected")
        self.refresh()
        self.on_refresh()

    def test_full_chat_flow(self) -> None:
        self.save_chat_configuration()
        self.flow_result.setText(self.chat.test_full_chat_flow())

    def refresh(self) -> None:
        streamer = self.repository.get_setting(STREAMER_METADATA_KEY, None)
        bot = self.repository.get_setting(BOT_METADATA_KEY, None)
        saved_client_id = self.repository.get_setting("twitch_client_id", "")
        if not self.client_id_dirty:
            self.client_id.setText(saved_client_id)
        self.update_client_id_status()
        self.monitored_channel.setText(self.chat.monitored_channel())
        self.response_mode.setCurrentText(self.chat.response_mode())
        self._fill_account("streamer", streamer, self.streamer_fields)
        self._fill_account("bot", bot, self.bot_fields)
        active = self.chat.active_response_login()
        self.active_response.setText(f"Responses will be sent as: {active}" if active else "No response account connected")
        self.listener_status.setText(self.chat.listener_status())
        self.sender_status.setText(self.chat.sender_status())
        auth_running = self._authorization_in_progress()
        self.auth_card.setVisible(auth_running)
        for role in ("streamer", "bot"):
            button = self._connection_button(role)
            button.setEnabled(not auth_running)
            if auth_running and self.auth_role == role:
                button.setText("Connecting...")
            else:
                account = streamer if role == "streamer" else bot
                button.setText(f"Reconnect {ROLE_LABELS[role]} Account" if account else f"Connect {ROLE_LABELS[role]} Account")

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
            "Chat-send status": self.chat.sender_status() if connected else "Not connected",
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

    def _client_id_value(self) -> str:
        return self.client_id.text().strip() or self.repository.get_setting("twitch_client_id", "")

    def _authorization_in_progress(self) -> bool:
        return bool(
            self.auth_worker
            and self.auth_worker.isRunning()
            and (
                not self.auth_context
                or self.auth_context.state in {AUTH_REQUESTING, AUTH_WAITING}
            )
        )

    def _clear_authorization_panel(self) -> None:
        self.countdown.stop()
        self.current_device = None
        self.code_started_at = None
        self.user_code.setText("--------")
        self.auth_expiration.setText("")
        self.auth_card.setVisible(False)
