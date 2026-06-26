"""Typed Twitch OAuth and user models."""

from __future__ import annotations

from dataclasses import dataclass


REQUIRED_CHAT_SCOPES = ("chat:read", "chat:edit", "user:read:chat", "user:write:chat")


@dataclass(frozen=True)
class DeviceCode:
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str
    expires_in: int
    scopes: tuple[str, ...]
    token_type: str = "bearer"


@dataclass(frozen=True)
class TwitchUser:
    user_id: str
    login: str
    display_name: str


@dataclass(frozen=True)
class TokenValidation:
    client_id: str
    login: str
    user_id: str
    scopes: tuple[str, ...]
    expires_in: int


@dataclass(frozen=True)
class StreamerAccount:
    user_id: str
    login: str
    display_name: str
    channel: str
    granted_scopes: tuple[str, ...]
    connected_at: str
    last_validated_at: str


@dataclass(frozen=True)
class TwitchAccountMetadata:
    role: str
    user_id: str
    login: str
    display_name: str
    granted_scopes: tuple[str, ...]
    connected_at: str
    last_validated_at: str
    authorization_status: str = "Authorized"
    chat_status: str = "Not connected"


def missing_required_scopes(scopes: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    granted = set(scopes)
    return tuple(scope for scope in REQUIRED_CHAT_SCOPES if scope not in granted)
