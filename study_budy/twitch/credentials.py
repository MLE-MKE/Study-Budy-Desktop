"""Secure credential storage for Twitch OAuth tokens."""

from __future__ import annotations

import json
from dataclasses import asdict

import keyring
from keyring.errors import KeyringError

from .models import TokenSet


SERVICE_NAME = "Study Budy Twitch"
STREAMER_ACCOUNT = "streamer"


class CredentialStoreError(RuntimeError):
    """Raised when secure token storage is unavailable or corrupted."""


class TokenCredentialStore:
    """Store Twitch tokens in the operating system credential manager."""

    def __init__(self, service_name: str = SERVICE_NAME) -> None:
        self.service_name = service_name

    def save_tokens(self, account: str, tokens: TokenSet) -> None:
        payload = asdict(tokens)
        payload["scopes"] = list(tokens.scopes)
        try:
            keyring.set_password(self.service_name, account, json.dumps(payload))
        except KeyringError as exc:
            raise CredentialStoreError("Secure credential storage is unavailable.") from exc

    def load_tokens(self, account: str) -> TokenSet | None:
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
        try:
            keyring.delete_password(self.service_name, account)
        except keyring.errors.PasswordDeleteError:
            return
        except KeyringError as exc:
            raise CredentialStoreError("Secure credential storage is unavailable.") from exc


class MemoryTokenCredentialStore(TokenCredentialStore):
    """In-memory store for tests; never used by the desktop app by default."""

    def __init__(self) -> None:
        self.tokens: dict[str, TokenSet] = {}

    def save_tokens(self, account: str, tokens: TokenSet) -> None:
        self.tokens[account] = tokens

    def load_tokens(self, account: str) -> TokenSet | None:
        return self.tokens.get(account)

    def delete_tokens(self, account: str) -> None:
        self.tokens.pop(account, None)
