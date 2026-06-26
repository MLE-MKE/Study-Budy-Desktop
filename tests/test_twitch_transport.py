from __future__ import annotations

from study_budy.storage import TaskRepository
from study_budy.twitch.chat import BOT_METADATA_KEY, STREAMER_METADATA_KEY, TwitchChatCoordinator
from study_budy.twitch.credentials import BOT_CREDENTIAL_KEY, MemoryTokenCredentialStore
from study_budy.twitch.models import REQUIRED_CHAT_SCOPES, TokenSet
from study_budy.twitch.transport import NormalizedChatMessage, TwitchHelixChatSender, parse_privmsg


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self.payload = payload or {}

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.posts = []

    def post(self, url: str, headers: dict, json: dict, timeout: int):
        self.posts.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return self.response


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
        "authorization_status": "Authorized",
    }


def test_irc_privmsg_parses_identity_badges_and_text():
    line = (
        "@badge-info=;badges=broadcaster/1,moderator/1;color=#fff;display-name=Killer_Queen55;"
        "user-id=123 :killer_queen55!killer_queen55@killer_queen55.tmi.twitch.tv "
        "PRIVMSG #killer_queen55 :!addtask Live test"
    )
    message = parse_privmsg(line)
    assert message is not None
    assert message.channel == "killer_queen55"
    assert message.user_id == "123"
    assert message.display_name == "Killer_Queen55"
    assert message.text == "!addtask Live test"
    assert message.is_broadcaster
    assert message.is_moderator


def test_live_message_reaches_existing_command_dispatcher(tmp_path):
    repository = repo(tmp_path)
    repository.set_setting(STREAMER_METADATA_KEY, account("streamer", "killer_queen55", "1"))
    chat = TwitchChatCoordinator(repository)
    response = chat.handle_live_message(
        NormalizedChatMessage(
            channel="killer_queen55",
            user_id="viewer-1",
            login="alex",
            display_name="Alex",
            text="!addtask Test task",
        )
    )
    assert response == "Task added for Alex."
    assert repository.task_snapshot()[0]["tasks"][0]["text"] == "Test task"


def test_helix_sender_uses_broadcaster_and_bot_sender_ids(tmp_path):
    repository = repo(tmp_path)
    repository.set_setting(STREAMER_METADATA_KEY, account("streamer", "killer_queen55", "streamer-id"))
    repository.set_setting(BOT_METADATA_KEY, account("bot", "killer_queens_jester", "bot-id"))
    store = MemoryTokenCredentialStore()
    store.save_tokens(BOT_CREDENTIAL_KEY, TokenSet("bot-access", "bot-refresh", 100, REQUIRED_CHAT_SCOPES))
    session = FakeSession(FakeResponse(200))
    sender = TwitchHelixChatSender(repository, store, lambda: "client-id", session=session)

    sender.send_message("killer_queen55", "killer_queens_jester", "@Alex Task added.")

    request = session.posts[0]
    assert request["json"]["broadcaster_id"] == "streamer-id"
    assert request["json"]["sender_id"] == "bot-id"
    assert request["json"]["message"] == "@Alex Task added."
    assert request["headers"]["Client-Id"] == "client-id"
    assert "bot-access" in request["headers"]["Authorization"]


def test_sender_failure_does_not_undo_local_command(tmp_path):
    repository = repo(tmp_path)
    repository.set_setting(STREAMER_METADATA_KEY, account("streamer", "killer_queen55", "streamer-id"))
    repository.set_setting(BOT_METADATA_KEY, account("bot", "killer_queens_jester", "bot-id"))
    store = MemoryTokenCredentialStore()
    store.save_tokens(BOT_CREDENTIAL_KEY, TokenSet("bot-access", "bot-refresh", 100, REQUIRED_CHAT_SCOPES))
    chat = TwitchChatCoordinator(
        repository,
        sender=TwitchHelixChatSender(repository, store, lambda: "client-id", session=FakeSession(FakeResponse(500))),
    )
    response = chat.handle_live_message(
        NormalizedChatMessage(
            channel="killer_queen55",
            user_id="viewer-1",
            login="alex",
            display_name="Alex",
            text="!addtask Still saved",
        )
    )
    assert response == "Task added for Alex."
    assert repository.task_snapshot()[0]["tasks"][0]["text"] == "Still saved"
    assert "failed" in chat.sender_state.casefold()
