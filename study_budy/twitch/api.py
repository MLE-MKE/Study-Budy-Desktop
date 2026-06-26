"""Small Twitch Helix/API client for account validation."""

from __future__ import annotations

import requests

from .auth import TwitchAuthError
from .models import TokenValidation, TwitchUser


VALIDATE_ENDPOINT = "https://id.twitch.tv/oauth2/validate"
USERS_ENDPOINT = "https://api.twitch.tv/helix/users"


class TwitchAPIClient:
    def __init__(self, client_id: str, session: requests.Session | None = None, timeout: int = 12) -> None:
        self.client_id = client_id.strip()
        self.session = session or requests.Session()
        self.timeout = timeout

    def validate_token(self, access_token: str) -> TokenValidation:
        try:
            response = self.session.get(VALIDATE_ENDPOINT, headers={"Authorization": f"OAuth {access_token}"}, timeout=self.timeout)
        except requests.RequestException as exc:
            raise TwitchAuthError("Unable to validate Twitch authorization.", "network_error") from exc
        payload = self._json(response)
        if response.status_code >= 400:
            raise TwitchAuthError("Authorization expired. Reconnect your account.", "token_validation_failed")
        try:
            return TokenValidation(
                client_id=payload["client_id"],
                login=payload["login"],
                user_id=payload["user_id"],
                scopes=tuple(payload.get("scopes", ())),
                expires_in=int(payload.get("expires_in", 0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TwitchAuthError("Twitch returned validation data Study Budy could not read.", "bad_validation_response") from exc

    def fetch_user(self, access_token: str) -> TwitchUser:
        try:
            response = self.session.get(
                USERS_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}", "Client-Id": self.client_id},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TwitchAuthError("Unable to look up the connected Twitch user.", "network_error") from exc
        payload = self._json(response)
        if response.status_code >= 400:
            raise TwitchAuthError("Unable to look up the connected Twitch user.", "user_lookup_failed")
        try:
            user = payload["data"][0]
            return TwitchUser(user_id=user["id"], login=user["login"], display_name=user["display_name"])
        except (KeyError, IndexError, TypeError) as exc:
            raise TwitchAuthError("Twitch did not return a user for this authorization.", "user_lookup_failed") from exc

    @staticmethod
    def _json(response: requests.Response) -> dict:
        try:
            payload = response.json()
        except ValueError as exc:
            raise TwitchAuthError("Twitch returned a response Study Budy could not read.", "bad_json") from exc
        return payload if isinstance(payload, dict) else {}
