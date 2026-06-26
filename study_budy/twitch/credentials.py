"""Secure credential storage for Twitch OAuth tokens."""

from __future__ import annotations

import json

import keyring
from keyring.errors import KeyringError

from .models import TokenSet


SERVICE_NAME = "Study Budy Twitch"
STREAMER_CREDENTIAL_KEY = "study_budy_twitch_streamer"
BOT_CREDENTIAL_KEY = "study_budy_twitch_bot"
STREAMER_ACCESS_KEY = "study_budy_twitch_streamer_access"
STREAMER_REFRESH_KEY = "study_budy_twitch_streamer_refresh"
STREAMER_META_KEY = "study_budy_twitch_streamer_meta"
BOT_ACCESS_KEY = "study_budy_twitch_bot_access"
BOT_REFRESH_KEY = "study_budy_twitch_bot_refresh"
BOT_META_KEY = "study_budy_twitch_bot_meta"
STREAMER_ACCOUNT = STREAMER_CREDENTIAL_KEY
BOT_ACCOUNT = BOT_CREDENTIAL_KEY


class CredentialStoreError(RuntimeError):
    """Raised when secure token storage is unavailable or corrupted."""


class TokenCredentialStore:
    """Store Twitch tokens in the operating system credential manager."""

    def __init__(self, service_name: str = SERVICE_NAME) -> None:
        self.service_name = service_name

    @staticmethod
    def _keys(account: str) -> tuple[str, str, str]:
        if account == STREAMER_CREDENTIAL_KEY:
            return STREAMER_ACCESS_KEY, STREAMER_REFRESH_KEY, STREAMER_META_KEY
        if account == BOT_CREDENTIAL_KEY:
            return BOT_ACCESS_KEY, BOT_REFRESH_KEY, BOT_META_KEY
        return f"{account}_access", f"{account}_refresh", f"{account}_meta"

    def save_tokens(self, account: str, tokens: TokenSet) -> None:
        access_key, refresh_key, meta_key = self._keys(account)
        metadata = {"expires_in": tokens.expires_in, "scopes": list(tokens.scopes), "token_type": tokens.token_type}
        try:
            keyring.set_password(self.service_name, access_key, tokens.access_token)
            keyring.set_password(self.service_name, refresh_key, tokens.refresh_token)
            keyring.set_password(self.service_name, meta_key, json.dumps(metadata))
        except KeyringError as exc:
            raise CredentialStoreError("Secure credential storage is unavailable.") from exc

    def load_tokens(self, account: str) -> TokenSet | None:
        access_key, refresh_key, meta_key = self._keys(account)
        try:
            access_token = keyring.get_password(self.service_name, access_key)
            refresh_token = keyring.get_password(self.service_name, refresh_key)
            metadata_raw = keyring.get_password(self.service_name, meta_key)
        except KeyringError as exc:
            raise CredentialStoreError("Secure credential storage is unavailable.") from exc
        if access_token and refresh_token:
            try:
                metadata = json.loads(metadata_raw or "{}")
            except json.JSONDecodeError:
                metadata = {}
            return TokenSet(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=int(metadata.get("expires_in", 0)),
                scopes=tuple(metadata.get("scopes") or ()),
                token_type=metadata.get("token_type", "bearer"),
            )
        try:
            raw = keyring.get_password(self.service_name, account)
        except KeyringError as exc:
            raise CredentialStoreError("Secure credential storage is unavailable.") from exc
        if not raw:
            return None
        try:
            payload = json.loads(raw)
            return TokenSet(
                access_token=payload["access_token"],
                refresh_token=payload["refresh_token"],
                expires_in=int(payload.get("expires_in", 0)),
                scopes=tuple(payload.get("scopes") or payload.get("scope") or ()),
                token_type=payload.get("token_type", "bearer"),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise CredentialStoreError("Stored Twitch credentials could not be read.") from exc

    def delete_tokens(self, account: str) -> None:
        for key in (*self._keys(account), account):
            try:
                keyring.delete_password(self.service_name, key)
            except keyring.errors.PasswordDeleteError:
                continue
            except KeyringError as exc:
                raise CredentialStoreError("Secure credential storage is unavailable.") from exc


class MemoryTokenCredentialStore(TokenCredentialStore):
    """In-memory store for tests; never used by the desktop app by default."""

    def __init__(self) -> None:
        self.tokens: dict[str, TokenSet] = {}
        self.secret_entries: dict[str, str] = {}

    def save_tokens(self, account: str, tokens: TokenSet) -> None:
        self.tokens[account] = tokens
        access_key, refresh_key, meta_key = self._keys(account)
        self.secret_entries[access_key] = tokens.access_token
        self.secret_entries[refresh_key] = tokens.refresh_token
        self.secret_entries[meta_key] = json.dumps({"expires_in": tokens.expires_in, "scopes": list(tokens.scopes), "token_type": tokens.token_type})

    def load_tokens(self, account: str) -> TokenSet | None:
        return self.tokens.get(account)

    def delete_tokens(self, account: str) -> None:
        self.tokens.pop(account, None)
        for key in self._keys(account):
            self.secret_entries.pop(key, None)
