"""Role-aware Twitch chat connection planning.

This module separates the listener role from the sender role. The live IRC
transport can plug into this layer later; tests can exercise routing and
response-account selection without real Twitch credentials.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from ..commands import ChatCommandService
from ..storage import TaskRepository, now

LOG = logging.getLogger(__name__)

STREAMER_METADATA_KEY = "twitch_streamer_account"
BOT_METADATA_KEY = "twitch_bot_account"
MONITORED_CHANNEL_KEY = "twitch_monitored_channel"
RESPONSE_MODE_KEY = "twitch_response_account_mode"
RESPONSE_MODE_AUTOMATIC = "Automatic"
RESPONSE_MODE_BOT = "Bot Account"
RESPONSE_MODE_STREAMER = "Streamer Account"


class ChatSender(Protocol):
    def send_message(self, channel: str, account_login: str, message: str) -> None: ...


class DryRunChatSender:
    """Non-network sender used until the Twitch IRC transport is connected."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    def send_message(self, channel: str, account_login: str, message: str) -> None:
        self.sent.append((channel, account_login, message))


@dataclass
class TwitchChatCoordinator:
    repository: TaskRepository
    sender: ChatSender | None = None

    def __post_init__(self) -> None:
        self.sender = self.sender or DryRunChatSender()
        self.commands = ChatCommandService(self.repository)

    def streamer(self) -> dict | None:
        return self.repository.get_setting(STREAMER_METADATA_KEY, None)

    def bot(self) -> dict | None:
        return self.repository.get_setting(BOT_METADATA_KEY, None)

    def monitored_channel(self) -> str:
        channel = self.repository.get_setting(MONITORED_CHANNEL_KEY, "")
        streamer = self.streamer() or {}
        return (channel or streamer.get("login") or "").strip().lstrip("#").casefold()

    def set_monitored_channel(self, channel: str) -> None:
        self.repository.set_setting(MONITORED_CHANNEL_KEY, channel.strip().lstrip("#").casefold())

    def response_mode(self) -> str:
        mode = self.repository.get_setting(RESPONSE_MODE_KEY, RESPONSE_MODE_AUTOMATIC)
        if mode not in {RESPONSE_MODE_AUTOMATIC, RESPONSE_MODE_BOT, RESPONSE_MODE_STREAMER}:
            return RESPONSE_MODE_AUTOMATIC
        return mode

    def set_response_mode(self, mode: str) -> None:
        self.repository.set_setting(RESPONSE_MODE_KEY, mode if mode in {RESPONSE_MODE_AUTOMATIC, RESPONSE_MODE_BOT, RESPONSE_MODE_STREAMER} else RESPONSE_MODE_AUTOMATIC)

    def active_response_account(self) -> tuple[str | None, dict | None, str | None]:
        streamer = self.streamer()
        bot = self.bot()
        mode = self.response_mode()
        if mode == RESPONSE_MODE_BOT:
            return ("bot", bot, None if bot else "Bot Account mode requires a connected bot account.")
        if mode == RESPONSE_MODE_STREAMER:
            return ("streamer", streamer, None if streamer else "Streamer Account mode requires a connected streamer account.")
        if bot:
            return ("bot", bot, None)
        if streamer:
            return ("streamer", streamer, None)
        return (None, None, "No chat response account is connected.")

    def active_response_login(self) -> str:
        _role, account, _warning = self.active_response_account()
        return account.get("login", "") if account else ""

    def same_account_warning(self) -> str:
        streamer, bot = self.streamer(), self.bot()
        if streamer and bot and streamer.get("user_id") == bot.get("user_id"):
            return "The bot and streamer accounts are the same. Study Budy can still work, but chat responses will appear from the streamer account."
        return ""

    def listener_status(self) -> str:
        if not self.streamer():
            return "No streamer account connected"
        if not self.monitored_channel():
            return "No monitored channel selected"
        return f"Authorized for {self.monitored_channel()} (chat transport pending)"

    def sender_status(self) -> str:
        _role, account, warning = self.active_response_account()
        if warning:
            return warning
        return f"Responses will be sent as: {account['login']} (chat transport pending)"

    def test_full_chat_flow(self) -> str:
        client_id = self.repository.get_setting("twitch_client_id", "")
        channel = self.monitored_channel()
        streamer = self.streamer()
        lines = [f"Client ID: {'Configured' if client_id else 'Not configured'}"]
        if not client_id:
            return "\n".join(lines + ["Streamer: Not tested", "Result: Add a Twitch Client ID first."])
        if not channel:
            return "\n".join(lines + ["Monitored channel: Not selected", "Result: No monitored channel is selected."])
        if not streamer:
            return "\n".join(lines + ["Streamer: Not authorized", f"Monitored channel: {channel}", "Result: Streamer authorization is required before Study Budy can listen to chat."])
        _role, sender, warning = self.active_response_account()
        if warning:
            return "\n".join(
                lines
                + [
                    f"Streamer: Authorized as {streamer['login']}",
                    f"Monitored channel: {channel}",
                    "Chat listener: Transport pending",
                    "Command dispatcher: Ready",
                    f"Response account: {warning}",
                    "Chat sender: Not available",
                ]
            )
        if channel != streamer.get("login", "").casefold():
            return "\n".join(lines + [f"Streamer: Authorized as {streamer['login']}", f"Monitored channel: {channel}", f"Result: Study Budy is configured to listen in {channel}. Streamer channel is {streamer.get('login', '')}."])
        return "\n".join(
            lines
            + [
                f"Streamer: Authorized as {streamer['login']}",
                f"Monitored channel: {channel}",
                "Chat listener: Transport pending",
                "Command dispatcher: Ready",
                f"Response account: {sender['login']}",
                "Chat sender: Transport pending",
            ]
        )

    def route_incoming_message(
        self,
        channel: str,
        user_id: str,
        display_name: str,
        message: str,
        *,
        is_broadcaster: bool = False,
        is_moderator: bool = False,
    ) -> str | None:
        if channel.strip().lstrip("#").casefold() != self.monitored_channel():
            return None
        response = self.commands.handle(
            user_id,
            display_name,
            message,
            is_broadcaster=is_broadcaster,
            is_moderator=is_moderator,
        )
        if not response:
            return None
        _role, account, warning = self.active_response_account()
        if warning or not account:
            LOG.warning("Command processed, but no chat response account is connected")
            return response
        self.sender.send_message(self.monitored_channel(), account["login"], f"@{display_name} {response}")
        return response


def account_metadata(role: str, user, scopes: tuple[str, ...], timestamp: str | None = None) -> dict:
    stamp = timestamp or now()
    return {
        "role": role,
        "user_id": user.user_id,
        "login": user.login,
        "display_name": user.display_name,
        "granted_scopes": list(scopes),
        "connected_at": stamp,
        "last_validated_at": stamp,
        "authorization_status": "Authorized",
        "chat_status": "Chat transport pending",
    }
