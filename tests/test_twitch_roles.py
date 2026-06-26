from __future__ import annotations

import json
import logging

from study_budy.storage import TaskRepository
from study_budy.twitch.chat import (
    BOT_METADATA_KEY,
    MONITORED_CHANNEL_KEY,
    RESPONSE_MODE_AUTOMATIC,
    RESPONSE_MODE_BOT,
    RESPONSE_MODE_STREAMER,
    STREAMER_METADATA_KEY,
    DryRunChatSender,
    TwitchChatCoordinator,
)
from study_budy.twitch.credentials import (
    BOT_ACCESS_KEY,
    BOT_CREDENTIAL_KEY,
    BOT_REFRESH_KEY,
    STREAMER_ACCESS_KEY,
    STREAMER_CREDENTIAL_KEY,
    STREAMER_REFRESH_KEY,
    MemoryTokenCredentialStore,
)
from study_budy.twitch.models import REQUIRED_CHAT_SCOPES, TokenSet


def repo(tmp_path):
    repository = TaskRepository(tmp_path / "study-budy.db")
    repository.initialize()
    return repository


def account(role: str, login: str, user_id: str) -> dict:
    return {
        "role": role,
        "user_id": user_id,
        "login": login,
        "display_name": login,
        "granted_scopes": list(REQUIRED_CHAT_SCOPES),
        "connected_at": "now",
        "last_validated_at": "now",
        "authorization_status": "Authorized",
        "chat_status": "Ready",
    }


def test_streamer_and_bot_credentials_remain_separate(tmp_path):
    store = MemoryTokenCredentialStore()
    store.save_tokens(STREAMER_CREDENTIAL_KEY, TokenSet("streamer-access", "streamer-refresh", 100, REQUIRED_CHAT_SCOPES))
    store.save_tokens(BOT_CREDENTIAL_KEY, TokenSet("bot-access", "bot-refresh", 100, REQUIRED_CHAT_SCOPES))
    assert store.load_tokens(STREAMER_CREDENTIAL_KEY).access_token == "streamer-access"
    assert store.load_tokens(BOT_CREDENTIAL_KEY).access_token == "bot-access"
    assert STREAMER_ACCESS_KEY != BOT_ACCESS_KEY
    assert STREAMER_REFRESH_KEY != BOT_REFRESH_KEY
    assert store.secret_entries[STREAMER_ACCESS_KEY] == "streamer-access"
    assert store.secret_entries[BOT_ACCESS_KEY] == "bot-access"


def test_connecting_each_role_does_not_overwrite_the_other(tmp_path):
    repository = repo(tmp_path)
    repository.set_setting(STREAMER_METADATA_KEY, account("streamer", "killer_queen55", "1"))
    repository.set_setting(BOT_METADATA_KEY, account("bot", "killer_queens_jester", "2"))
    repository.set_setting(STREAMER_METADATA_KEY, account("streamer", "killer_queen55", "1"))
    assert repository.get_setting(BOT_METADATA_KEY)["login"] == "killer_queens_jester"
    repository.set_setting(BOT_METADATA_KEY, account("bot", "killer_queens_jester", "2"))
    assert repository.get_setting(STREAMER_METADATA_KEY)["login"] == "killer_queen55"


def test_monitored_channel_defaults_to_streamer_login_and_bot_uses_streamer_channel(tmp_path):
    repository = repo(tmp_path)
    repository.set_setting(STREAMER_METADATA_KEY, account("streamer", "killer_queen55", "1"))
    repository.set_setting(BOT_METADATA_KEY, account("bot", "killer_queens_jester", "2"))
    sender = DryRunChatSender()
    chat = TwitchChatCoordinator(repository, sender)
    assert chat.monitored_channel() == "killer_queen55"
    chat.route_incoming_message("killer_queen55", "42", "viewer", "!addtask Finish laundry")
    assert sender.sent[0][0] == "killer_queen55"
    assert sender.sent[0][1] == "killer_queens_jester"


def test_response_account_selection_modes(tmp_path):
    repository = repo(tmp_path)
    chat = TwitchChatCoordinator(repository)
    repository.set_setting(STREAMER_METADATA_KEY, account("streamer", "killer_queen55", "1"))
    repository.set_setting(BOT_METADATA_KEY, account("bot", "killer_queens_jester", "2"))
    chat.set_response_mode(RESPONSE_MODE_AUTOMATIC)
    assert chat.active_response_login() == "killer_queens_jester"
    repository.set_setting(BOT_METADATA_KEY, None)
    assert chat.active_response_login() == "killer_queen55"
    chat.set_response_mode(RESPONSE_MODE_BOT)
    assert chat.active_response_account()[2] == "Bot Account mode requires a connected bot account."
    chat.set_response_mode(RESPONSE_MODE_STREAMER)
    assert chat.active_response_login() == "killer_queen55"


def test_incoming_messages_route_to_command_parser_and_create_response(tmp_path):
    repository = repo(tmp_path)
    repository.set_setting(STREAMER_METADATA_KEY, account("streamer", "killer_queen55", "1"))
    repository.set_setting(BOT_METADATA_KEY, account("bot", "killer_queens_jester", "2"))
    sender = DryRunChatSender()
    chat = TwitchChatCoordinator(repository, sender)
    response = chat.route_incoming_message("killer_queen55", "42", "viewer", "!addtask Finish laundry")
    assert response == "Added task 1: Finish laundry"
    assert repository.task_snapshot()[0]["tasks"][0]["text"] == "Finish laundry"
    assert sender.sent == [("killer_queen55", "killer_queens_jester", "@viewer Added task 1: Finish laundry")]


def test_no_sender_still_processes_locally_and_logs_warning(tmp_path, caplog):
    repository = repo(tmp_path)
    repository.set_setting(STREAMER_METADATA_KEY, account("streamer", "killer_queen55", "1"))
    repository.set_setting(BOT_METADATA_KEY, None)
    TwitchChatCoordinator(repository).set_response_mode(RESPONSE_MODE_BOT)
    caplog.set_level(logging.WARNING)
    response = TwitchChatCoordinator(repository).route_incoming_message("killer_queen55", "42", "viewer", "!addtask Local only")
    assert response == "Added task 1: Local only"
    assert repository.task_snapshot()[0]["tasks"][0]["text"] == "Local only"
    assert "no chat response account" in caplog.text


def test_disconnect_behaviors_and_same_account_warning(tmp_path):
    repository = repo(tmp_path)
    repository.set_setting(STREAMER_METADATA_KEY, account("streamer", "same_login", "1"))
    repository.set_setting(BOT_METADATA_KEY, account("bot", "same_login", "1"))
    chat = TwitchChatCoordinator(repository)
    assert "same" in chat.same_account_warning().casefold()
    repository.set_setting(BOT_METADATA_KEY, None)
    assert chat.active_response_login() == "same_login"
    repository.set_setting(BOT_METADATA_KEY, account("bot", "bot_login", "2"))
    repository.set_setting(STREAMER_METADATA_KEY, None)
    assert repository.get_setting(BOT_METADATA_KEY)["login"] == "bot_login"


def test_full_chat_flow_reports_failure_states_and_success(tmp_path):
    repository = repo(tmp_path)
    chat = TwitchChatCoordinator(repository)
    assert "Client ID: Not configured" in chat.test_full_chat_flow()
    repository.set_setting("twitch_client_id", "a" * 30)
    assert "No monitored channel is selected" in chat.test_full_chat_flow()
    repository.set_setting(MONITORED_CHANNEL_KEY, "killer_queen55")
    assert "Streamer authorization is required" in chat.test_full_chat_flow()
    repository.set_setting(STREAMER_METADATA_KEY, account("streamer", "killer_queen55", "1"))
    chat.set_response_mode(RESPONSE_MODE_BOT)
    assert "Chat sender: Not available" in chat.test_full_chat_flow()
    repository.set_setting(BOT_METADATA_KEY, account("bot", "killer_queens_jester", "2"))
    assert "Response account: killer_queens_jester" in chat.test_full_chat_flow()
    repository.set_setting(MONITORED_CHANNEL_KEY, "wrong_channel")
    assert "wrong_channel" in chat.test_full_chat_flow()


def test_tokens_are_not_logged_or_stored_in_normal_settings(tmp_path, caplog):
    repository = repo(tmp_path)
    store = MemoryTokenCredentialStore()
    store.save_tokens(STREAMER_CREDENTIAL_KEY, TokenSet("secret-streamer", "refresh-streamer", 100, REQUIRED_CHAT_SCOPES))
    store.save_tokens(BOT_CREDENTIAL_KEY, TokenSet("secret-bot", "refresh-bot", 100, REQUIRED_CHAT_SCOPES))
    repository.set_setting(STREAMER_METADATA_KEY, account("streamer", "killer_queen55", "1"))
    repository.set_setting(BOT_METADATA_KEY, account("bot", "killer_queens_jester", "2"))
    raw = repository.path.read_bytes()
    exported = json.dumps(repository.get_setting(STREAMER_METADATA_KEY)) + json.dumps(repository.get_setting(BOT_METADATA_KEY))
    assert b"secret-streamer" not in raw
    assert b"secret-bot" not in raw
    assert "secret-streamer" not in exported
    assert "secret-bot" not in exported
    assert "secret-streamer" not in caplog.text
    assert "secret-bot" not in caplog.text
