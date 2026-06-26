from __future__ import annotations

import json
import logging
import threading

import pytest
from PySide6.QtWidgets import QApplication

from study_budy.connections_view import CLIENT_ID_HELP_TEXT, ConnectionsView
from study_budy.storage import TaskRepository
from study_budy.twitch.api import TwitchAPIClient
from study_budy.twitch.auth import (
    AuthorizationCancelled,
    AuthorizationDenied,
    AuthorizationExpired,
    AuthorizationPending,
    TwitchAuthError,
    TwitchDeviceAuthClient,
)
from study_budy.twitch.credentials import MemoryTokenCredentialStore, STREAMER_ACCOUNT
from study_budy.twitch.models import REQUIRED_CHAT_SCOPES, TokenSet, missing_required_scopes


class FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self.payload = payload

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self, posts: list[FakeResponse] | None = None, gets: list[FakeResponse] | None = None) -> None:
        self.posts = posts or []
        self.gets = gets or []
        self.post_calls: list[dict] = []
        self.get_calls: list[dict] = []

    def post(self, url: str, data: dict, timeout: int) -> FakeResponse:
        self.post_calls.append({"url": url, "data": data, "timeout": timeout})
        return self.posts.pop(0)

    def get(self, url: str, headers: dict, timeout: int) -> FakeResponse:
        self.get_calls.append({"url": url, "headers": headers, "timeout": timeout})
        return self.gets.pop(0)


@pytest.fixture
def repository(tmp_path):
    repo = TaskRepository(tmp_path / "study-budy.db")
    repo.initialize()
    return repo


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def token_payload(access: str = "access-token", refresh: str = "refresh-token", scopes=None) -> dict:
    return {
        "access_token": access,
        "refresh_token": refresh,
        "expires_in": 14400,
        "scope": list(scopes or REQUIRED_CHAT_SCOPES),
        "token_type": "bearer",
    }


def test_device_code_request_success():
    session = FakeSession(
        posts=[
            FakeResponse(
                200,
                {
                    "device_code": "device",
                    "user_code": "ABCD-EFGH",
                    "verification_uri": "https://www.twitch.tv/activate",
                    "expires_in": 1800,
                    "interval": 5,
                },
            )
        ]
    )
    code = TwitchDeviceAuthClient("client-id", session=session).request_device_code(REQUIRED_CHAT_SCOPES)
    assert code.user_code == "ABCD-EFGH"
    assert session.post_calls[0]["data"]["client_id"] == "client-id"
    assert session.post_calls[0]["data"]["scopes"] == "user:read:chat user:write:chat"


def test_device_code_request_failure():
    session = FakeSession(posts=[FakeResponse(400, {"message": "bad client"})])
    with pytest.raises(TwitchAuthError, match="bad client"):
        TwitchDeviceAuthClient("client-id", session=session).request_device_code(REQUIRED_CHAT_SCOPES)


def test_pending_success_denied_and_expired_authorization():
    pending = FakeSession(posts=[FakeResponse(400, {"message": "authorization_pending"})])
    with pytest.raises(AuthorizationPending):
        TwitchDeviceAuthClient("client-id", session=pending).poll_token_once("device", REQUIRED_CHAT_SCOPES)

    success = FakeSession(posts=[FakeResponse(200, token_payload())])
    tokens = TwitchDeviceAuthClient("client-id", session=success).poll_token_once("device", REQUIRED_CHAT_SCOPES)
    assert tokens.access_token == "access-token"

    denied = FakeSession(posts=[FakeResponse(400, {"message": "access_denied"})])
    with pytest.raises(AuthorizationDenied):
        TwitchDeviceAuthClient("client-id", session=denied).poll_token_once("device", REQUIRED_CHAT_SCOPES)

    expired = FakeSession(posts=[FakeResponse(400, {"message": "expired_token"})])
    with pytest.raises(AuthorizationExpired):
        TwitchDeviceAuthClient("client-id", session=expired).poll_token_once("device", REQUIRED_CHAT_SCOPES)


def test_cancelled_authorization_stops_polling():
    session = FakeSession(posts=[])
    cancel = threading.Event()
    cancel.set()
    device = type("Device", (), {"expires_in": 1800, "interval": 1, "device_code": "device"})()
    with pytest.raises(AuthorizationCancelled):
        TwitchDeviceAuthClient("client-id", session=session).wait_for_token(device, REQUIRED_CHAT_SCOPES, cancel)
    assert session.post_calls == []


def test_token_validation_user_lookup_and_missing_scopes():
    session = FakeSession(
        gets=[
            FakeResponse(
                200,
                {
                    "client_id": "client-id",
                    "login": "killer_queen55",
                    "user_id": "123",
                    "scopes": list(REQUIRED_CHAT_SCOPES),
                    "expires_in": 1000,
                },
            ),
            FakeResponse(200, {"data": [{"id": "123", "login": "killer_queen55", "display_name": "Killer_Queen55"}]}),
        ]
    )
    api = TwitchAPIClient("client-id", session=session)
    validation = api.validate_token("access-token")
    user = api.fetch_user("access-token")
    assert validation.user_id == "123"
    assert user.display_name == "Killer_Queen55"
    assert missing_required_scopes(("user:read:chat",)) == ("user:write:chat",)


def test_refresh_token_rotation():
    session = FakeSession(posts=[FakeResponse(200, token_payload("new-access", "new-refresh"))])
    tokens = TwitchDeviceAuthClient("client-id", session=session).refresh_tokens("old-refresh")
    assert tokens.access_token == "new-access"
    assert tokens.refresh_token == "new-refresh"
    assert session.post_calls[0]["data"]["grant_type"] == "refresh_token"


def test_disconnect_clears_credentials():
    store = MemoryTokenCredentialStore()
    store.save_tokens(STREAMER_ACCOUNT, TokenSet("access-token", "refresh-token", 10, REQUIRED_CHAT_SCOPES))
    store.delete_tokens(STREAMER_ACCOUNT)
    assert store.load_tokens(STREAMER_ACCOUNT) is None


def test_duplicate_connection_attempt_is_blocked(qapp, repository):
    view = ConnectionsView(repository, lambda: None)
    view.credential_store = MemoryTokenCredentialStore()
    repository.set_setting("twitch_client_id", "client-id")
    view.client_id.setText("client-id")

    class RunningWorker:
        def isRunning(self):
            return True

    view.auth_worker = RunningWorker()
    view.connect_streamer()
    assert "already in progress" in view.explanation.text()


def test_client_id_help_and_validation(qapp, repository, monkeypatch):
    view = ConnectionsView(repository, lambda: None)
    assert "How to Find Your Twitch Client ID" in CLIENT_ID_HELP_TEXT
    assert "Do not paste your Twitch password" in CLIENT_ID_HELP_TEXT
    called = []
    monkeypatch.setattr("study_budy.connections_view.QDesktopServices.openUrl", lambda url: called.append(url.toString()) or True)
    view.open_developer_console()
    assert called == ["https://dev.twitch.tv/console/apps"]
    view.client_id.setText("")
    view.save_client_id_setting()
    assert "needs a Twitch Client ID" in view.explanation.text()
    view.client_id.setText("bad secret")
    view.save_client_id_setting()
    assert "does not look valid" in view.explanation.text()
    view.client_id.setText("a" * 30)
    view.save_client_id_setting()
    assert repository.get_setting("twitch_client_id") == "a" * 30
    assert view.client_id_status.text() == "Configured"
    assert repository.get_setting("twitch_streamer_account", None) is None
    assert repository.get_setting("twitch_bot_account", None) is None


def test_connect_buttons_are_wired_and_missing_client_id_is_visible(qapp, repository):
    view = ConnectionsView(repository, lambda: None)
    view.streamer_connect_streamer_account.click()
    assert "needs a Twitch Client ID" in view.explanation.text()
    view.bot_connect_bot_account.click()
    assert "needs a Twitch Client ID" in view.explanation.text()


def test_connection_button_feedback_and_restore(qapp, repository):
    view = ConnectionsView(repository, lambda: None)
    view.client_id.setText("a" * 30)

    class FakeWorker:
        def __init__(self):
            self._running = True

        def isRunning(self):
            return self._running

    view.auth_worker = FakeWorker()
    view.auth_role = "bot"
    view.refresh()
    assert view.bot_connect_bot_account.text() == "Connecting..."
    assert not view.bot_connect_bot_account.isEnabled()
    view.auth_worker._running = False
    view.on_auth_finished()
    assert view.bot_connect_bot_account.text() == "Connect Bot Account"
    assert view.bot_connect_bot_account.isEnabled()


def test_tokens_are_not_stored_in_settings_sqlite_or_logs(repository, caplog):
    caplog.set_level(logging.DEBUG)
    store = MemoryTokenCredentialStore()
    store.save_tokens(STREAMER_ACCOUNT, TokenSet("access-secret", "refresh-secret", 10, REQUIRED_CHAT_SCOPES))
    repository.set_setting(
        "twitch_streamer_account",
        {"user_id": "123", "login": "queen", "display_name": "Queen", "granted_scopes": list(REQUIRED_CHAT_SCOPES)},
    )
    raw_database = repository.path.read_bytes()
    assert b"access-secret" not in raw_database
    assert b"refresh-secret" not in raw_database
    assert "access-secret" not in caplog.text
    assert "refresh-secret" not in caplog.text
    exported_settings = json.dumps(repository.get_setting("twitch_streamer_account"))
    assert "access-secret" not in exported_settings
    assert "refresh-secret" not in exported_settings
