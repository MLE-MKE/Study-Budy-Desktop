"""Twitch OAuth Device Code Flow client."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import requests

from .models import DeviceCode, TokenSet


DEVICE_ENDPOINT = "https://id.twitch.tv/oauth2/device"
TOKEN_ENDPOINT = "https://id.twitch.tv/oauth2/token"
DEVICE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"


class TwitchAuthError(RuntimeError):
    """Plain-language OAuth error suitable for UI display."""

    def __init__(self, message: str, code: str = "auth_error") -> None:
        super().__init__(message)
        self.code = code


class AuthorizationPending(TwitchAuthError):
    def __init__(self) -> None:
        super().__init__("Waiting for Twitch authorization.", "authorization_pending")


class AuthorizationDenied(TwitchAuthError):
    def __init__(self) -> None:
        super().__init__("Authorization was denied.", "access_denied")


class AuthorizationExpired(TwitchAuthError):
    def __init__(self) -> None:
        super().__init__("Authorization expired. Generate a new code and try again.", "expired_token")


class AuthorizationSlowDown(TwitchAuthError):
    def __init__(self) -> None:
        super().__init__("Twitch asked Study Budy to slow down while waiting for authorization.", "slow_down")


class AuthorizationCancelled(TwitchAuthError):
    def __init__(self) -> None:
        super().__init__("Authorization cancelled.", "cancelled")


class TwitchDeviceAuthClient:
    def __init__(self, client_id: str, session: requests.Session | None = None, timeout: int = 12) -> None:
        self.client_id = client_id.strip()
        self.session = session or requests.Session()
        self.timeout = timeout
        if not self.client_id:
            raise TwitchAuthError("Enter a Twitch Client ID before connecting.", "missing_client_id")

    def request_device_code(self, scopes: tuple[str, ...]) -> DeviceCode:
        try:
            response = self.session.post(
                DEVICE_ENDPOINT,
                data={"client_id": self.client_id, "scopes": " ".join(scopes)},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TwitchAuthError("Unable to reach Twitch. Check your internet connection.", "network_error") from exc
        payload = self._json(response)
        if response.status_code >= 400:
            raise TwitchAuthError(self._message(payload, "Twitch could not create an authorization code."), "device_code_failed")
        try:
            return DeviceCode(
                device_code=payload["device_code"],
                user_code=payload["user_code"],
                verification_uri=payload["verification_uri"],
                expires_in=int(payload["expires_in"]),
                interval=max(1, int(payload.get("interval", 5))),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TwitchAuthError("Twitch returned an authorization response Study Budy could not read.", "bad_response") from exc

    def poll_token_once(self, device_code: str, scopes: tuple[str, ...]) -> TokenSet:
        try:
            response = self.session.post(
                TOKEN_ENDPOINT,
                data={
                    "client_id": self.client_id,
                    "scopes": " ".join(scopes),
                    "device_code": device_code,
                    "grant_type": DEVICE_GRANT_TYPE,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TwitchAuthError("Unable to reach Twitch. Check your internet connection.", "network_error") from exc
        payload = self._json(response)
        if response.status_code >= 400:
            code = str(payload.get("message") or payload.get("error") or "").casefold().replace(" ", "_")
            if code == "authorization_pending":
                raise AuthorizationPending()
            if code in {"access_denied", "authorization_denied"}:
                raise AuthorizationDenied()
            if code in {"expired_token", "authorization_expired", "expired_device_code"}:
                raise AuthorizationExpired()
            if code == "slow_down":
                raise AuthorizationSlowDown()
            if "invalid" in code and "device" in code:
                raise TwitchAuthError("The Twitch authorization code is no longer valid.", "invalid_device_code")
            raise TwitchAuthError(self._message(payload, "Twitch authorization failed."), code or "token_error")
        try:
            return TokenSet(
                access_token=payload["access_token"],
                refresh_token=payload["refresh_token"],
                expires_in=int(payload.get("expires_in", 0)),
                scopes=tuple(payload.get("scope") or payload.get("scopes") or ()),
                token_type=payload.get("token_type", "bearer"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TwitchAuthError("Twitch returned token data Study Budy could not read.", "bad_token_response") from exc

    def wait_for_token(
        self,
        device: DeviceCode,
        scopes: tuple[str, ...],
        cancel_event: threading.Event,
        status_callback: Callable[[str], None] | None = None,
    ) -> TokenSet:
        deadline = time.monotonic() + device.expires_in
        interval = max(1, device.interval)
        while time.monotonic() < deadline:
            if cancel_event.is_set():
                raise AuthorizationCancelled()
            try:
                return self.poll_token_once(device.device_code, scopes)
            except AuthorizationPending:
                if status_callback:
                    status_callback("Waiting for Twitch authorization")
                cancel_event.wait(min(interval, max(0.1, deadline - time.monotonic())))
            except AuthorizationSlowDown:
                interval += 5
                if status_callback:
                    status_callback("Waiting for Twitch authorization. Twitch asked Study Budy to slow down.")
                cancel_event.wait(min(interval, max(0.1, deadline - time.monotonic())))
        raise AuthorizationExpired()

    def refresh_tokens(self, refresh_token: str) -> TokenSet:
        try:
            response = self.session.post(
                TOKEN_ENDPOINT,
                data={"client_id": self.client_id, "grant_type": "refresh_token", "refresh_token": refresh_token},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TwitchAuthError("Unable to refresh Twitch authorization.", "network_error") from exc
        payload = self._json(response)
        if response.status_code >= 400:
            raise TwitchAuthError(self._message(payload, "Twitch authorization expired. Reconnect your account."), "refresh_failed")
        try:
            return TokenSet(
                access_token=payload["access_token"],
                refresh_token=payload["refresh_token"],
                expires_in=int(payload.get("expires_in", 0)),
                scopes=tuple(payload.get("scope") or payload.get("scopes") or ()),
                token_type=payload.get("token_type", "bearer"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TwitchAuthError("Twitch returned refresh data Study Budy could not read.", "bad_refresh_response") from exc

    @staticmethod
    def _json(response: requests.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise TwitchAuthError("Twitch returned a response Study Budy could not read.", "bad_json") from exc
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _message(payload: dict[str, Any], fallback: str) -> str:
        message = payload.get("message") or payload.get("error_description") or payload.get("error")
        return str(message) if message else fallback
