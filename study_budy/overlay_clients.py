"""Live Browser Source client heartbeats for Study Budy overlays."""

from __future__ import annotations

import time
from threading import Lock

TIMER_OVERLAY_CLIENT = "timer"
CHECKIN_OVERLAY_CLIENT = "checkin"
OVERLAY_CLIENT_TIMEOUT_SECONDS = 6.0

_HEARTBEATS: dict[str, float] = {}
_LOCK = Lock()


def record_overlay_heartbeat(client_id: str) -> None:
    """Mark an overlay client as currently active in this desktop process."""
    with _LOCK:
        _HEARTBEATS[client_id] = time.monotonic()


def is_overlay_client_connected(client_id: str, timeout_seconds: float = OVERLAY_CLIENT_TIMEOUT_SECONDS) -> bool:
    """Return True only when an overlay has pinged the app recently."""
    with _LOCK:
        timestamp = _HEARTBEATS.get(client_id)
    return timestamp is not None and (time.monotonic() - timestamp) <= timeout_seconds


def clear_overlay_heartbeats() -> None:
    """Reset tracked overlay clients for tests and clean shutdown paths."""
    with _LOCK:
        _HEARTBEATS.clear()
