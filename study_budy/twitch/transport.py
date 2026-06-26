"""Live Twitch chat receiving and sending transports.

Study Budy uses Twitch IRC for receiving chat commands because it is small,
packaging-friendly, and maps cleanly onto the existing command dispatcher.
Responses are sent with Twitch's Helix Send Chat Message endpoint so bot and
streamer accounts can be selected by role.
"""

from __future__ import annotations

import logging
import re
import socket
import ssl
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import requests

from .credentials import BOT_CREDENTIAL_KEY, STREAMER_CREDENTIAL_KEY, TokenCredentialStore


LOG = logging.getLogger(__name__)
IRC_HOST = "irc.chat.twitch.tv"
IRC_PORT = 6697
SEND_CHAT_MESSAGE_ENDPOINT = "https://api.twitch.tv/helix/chat/messages"
IRC_AUTH_FAILED_MESSAGES = (
    "login authentication failed",
    "improperly formatted auth",
    "invalid nick",
)


@dataclass(frozen=True)
class NormalizedChatMessage:
    channel: str
    user_id: str
    login: str
    display_name: str
    text: str
    is_broadcaster: bool = False
    is_moderator: bool = False
    badges: tuple[str, ...] = ()


class TwitchTransportError(RuntimeError):
    """Plain-language live chat transport error."""


class ChatMessageHandler(Protocol):
    def __call__(self, message: NormalizedChatMessage) -> None: ...


def parse_irc_tags(raw: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for pair in raw.split(";"):
        key, _, value = pair.partition("=")
        tags[key] = value.replace(r"\s", " ").replace(r"\:", ";").replace(r"\\", "\\")
    return tags


def parse_badges(raw: str) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(item.split("/", 1)[0] for item in raw.split(",") if item)


def parse_privmsg(line: str) -> NormalizedChatMessage | None:
    tags: dict[str, str] = {}
    rest = line
    if line.startswith("@"):
        raw_tags, _, rest = line.partition(" ")
        tags = parse_irc_tags(raw_tags[1:])
    if " PRIVMSG " not in rest:
        return None
    prefix, _, tail = rest.partition(" PRIVMSG ")
    channel_part, _, text = tail.partition(" :")
    channel = channel_part.strip().lstrip("#").casefold()
    login = tags.get("login") or prefix.split("!", 1)[0].lstrip(":")
    display_name = tags.get("display-name") or login
    user_id = tags.get("user-id") or login
    badges = parse_badges(tags.get("badges", ""))
    return NormalizedChatMessage(
        channel=channel,
        user_id=user_id,
        login=login,
        display_name=display_name,
        text=text.rstrip("\r\n"),
        is_broadcaster="broadcaster" in badges,
        is_moderator="moderator" in badges or "broadcaster" in badges,
        badges=badges,
    )


class TwitchIRCChatListener:
    """Background Twitch IRC listener for one monitored channel."""

    def __init__(
        self,
        *,
        channel: str,
        login: str,
        access_token: str,
        on_message: ChatMessageHandler,
        on_status: Callable[[str], None] | None = None,
        socket_factory: Callable[[], socket.socket] | None = None,
        reconnect_delay: float = 5.0,
    ) -> None:
        self.channel = channel.strip().lstrip("#").casefold()
        self.login = login.strip().casefold()
        self.access_token = access_token
        self.on_message = on_message
        self.on_status = on_status or (lambda _status: None)
        self.socket_factory = socket_factory
        self.reconnect_delay = reconnect_delay
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None
        self._socket: socket.socket | None = None
        self.last_error = ""

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._ready.clear()
        self._thread = threading.Thread(target=self._run, name="StudyBudyTwitchIRC", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        try:
            if self._socket:
                self._socket.close()
        except OSError:
            LOG.debug("Twitch IRC socket already closed")

    def is_ready(self) -> bool:
        return self._ready.is_set()

    def _connect_socket(self) -> socket.socket:
        if self.socket_factory:
            return self.socket_factory()
        raw = socket.create_connection((IRC_HOST, IRC_PORT), timeout=20)
        return ssl.create_default_context().wrap_socket(raw, server_hostname=IRC_HOST)

    def _send(self, text: str) -> None:
        if not self._socket:
            raise TwitchTransportError("Twitch chat socket is not connected.")
        self._socket.sendall((text + "\r\n").encode("utf-8"))

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.on_status(f"Connecting chat listener for {self.channel}")
                self._socket = self._connect_socket()
                self._send("CAP REQ :twitch.tv/tags twitch.tv/commands")
                self._send(f"PASS oauth:{self.access_token}")
                self._send(f"NICK {self.login}")
                self._send(f"JOIN #{self.channel}")
                self._read_loop()
            except Exception as exc:
                if self._stop.is_set():
                    break
                self.last_error = str(exc)
                self._ready.clear()
                LOG.warning("Twitch IRC listener failed: %s", exc)
                self.on_status(f"Chat listener failed: {exc}")
                if self._stop.wait(self.reconnect_delay):
                    break
                self.on_status("Reconnecting chat listener")
            finally:
                try:
                    if self._socket:
                        self._socket.close()
                except OSError:
                    LOG.debug("Twitch IRC socket close failed during cleanup")
                self._socket = None
        self._ready.clear()

    def _read_loop(self) -> None:
        buffer = ""
        while not self._stop.is_set():
            assert self._socket is not None
            chunk = self._socket.recv(4096)
            if not chunk:
                raise TwitchTransportError("Twitch chat connection closed.")
            buffer += chunk.decode("utf-8", errors="replace")
            while "\r\n" in buffer:
                line, buffer = buffer.split("\r\n", 1)
                self._handle_line(line)

    def _handle_line(self, line: str) -> None:
        if not line:
            return
        if line.startswith("PING"):
            self._send("PONG :tmi.twitch.tv")
            return
        lower = line.casefold()
        if " NOTICE " in line and any(message in lower for message in IRC_AUTH_FAILED_MESSAGES):
            raise TwitchTransportError("Twitch rejected the chat login. Reconnect the streamer account and make sure chat permissions are approved.")
        if " 001 " in line or " 376 " in line or re.search(rf"\s(353|366)\s+{re.escape(self.login)}\s+", lower):
            self._ready.set()
            self.on_status(f"Listening in {self.channel}")
            LOG.info("Twitch IRC listener joined monitored channel")
            return
        if " USERSTATE #" in line and f"#{self.channel}" in lower:
            self._ready.set()
            self.on_status(f"Listening in {self.channel}")
            LOG.info("Twitch IRC listener confirmed user state in monitored channel")
            return
        if " JOIN #" in line and self.login in lower:
            self._ready.set()
            self.on_status(f"Listening in {self.channel}")
            LOG.info("Twitch IRC listener joined monitored channel")
            return
        message = parse_privmsg(line)
        if message:
            LOG.info("Incoming Twitch chat command candidate received")
            self.on_message(message)


class TwitchHelixChatSender:
    """Send Study Budy command responses through Twitch Helix chat messages."""

    def __init__(
        self,
        repository,
        credential_store: TokenCredentialStore,
        client_id_getter: Callable[[], str],
        *,
        session: requests.Session | None = None,
    ) -> None:
        self.repository = repository
        self.credential_store = credential_store
        self.client_id_getter = client_id_getter
        self.session = session or requests.Session()
        self.last_status = "Not connected"

    def send_message(self, channel: str, account_login: str, message: str) -> None:
        from .chat import BOT_METADATA_KEY, STREAMER_METADATA_KEY

        streamer = self.repository.get_setting(STREAMER_METADATA_KEY, None) or {}
        bot = self.repository.get_setting(BOT_METADATA_KEY, None) or {}
        sender_role, sender = ("bot", bot) if bot.get("login") == account_login else ("streamer", streamer)
        if not streamer.get("user_id"):
            raise TwitchTransportError("Streamer channel ID is not available.")
        if not sender.get("user_id"):
            raise TwitchTransportError("Selected response account is not available.")
        credential_key = BOT_CREDENTIAL_KEY if sender_role == "bot" else STREAMER_CREDENTIAL_KEY
        tokens = self.credential_store.load_tokens(credential_key)
        if not tokens:
            raise TwitchTransportError("Selected response account needs to be reconnected.")
        client_id = self.client_id_getter().strip()
        if not client_id:
            raise TwitchTransportError("Twitch Client ID is not configured.")
        payload = {
            "broadcaster_id": streamer["user_id"],
            "sender_id": sender["user_id"],
            "message": message[:500],
        }
        try:
            response = self.session.post(
                SEND_CHAT_MESSAGE_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {tokens.access_token}",
                    "Client-Id": client_id,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=12,
            )
        except requests.RequestException as exc:
            self.last_status = "Failed"
            raise TwitchTransportError("Study Budy could not reach Twitch to send a chat response.") from exc
        if response.status_code >= 400:
            self.last_status = "Failed"
            raise TwitchTransportError(f"Twitch rejected the chat response with status {response.status_code}.")
        self.last_status = f"Ready to send as {account_login}"
        LOG.info("Twitch chat response sent")
