"""Check-In shape overlay state, commands, and events."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .storage import TaskRepository, now

VIEWER_SHAPES = ("circle", "triangle", "square")
STREAMER_SHAPE = "octagon"
DEFAULT_COLORS = {
    "circle": "#8b5cf6",
    "triangle": "#22d3ee",
    "square": "#f97316",
    "octagon": "#facc15",
}


DEFAULT_CHECKIN_APPEARANCE = {
    "browser_width": 1280,
    "browser_height": 720,
    "overlay_padding": 48,
    "viewer_spacing": 34,
    "vertical_spacing": 70,
    "arrangement_mode": "Around Streamer",
    "max_visible_viewers": 24,
    "viewer_shape_size": 72,
    "streamer_shape_size": 88,
    "outline_color": "#1b0b45",
    "outline_width": 4,
    "shape_opacity": 96,
    "show_names": True,
    "name_font": "Comic Sans MS",
    "name_size": 16,
    "name_color": "#ffffff",
    "name_shadow": True,
    "bubble_color": "#1f1830",
    "bubble_opacity": 92,
    "bubble_text_color": "#ffffff",
    "message_duration": 4,
    "max_simultaneous_reactions": 4,
    "join_animation": "pop",
    "idle_animation": "bounce",
    "leave_animation": "black_portal",
    "completion_animation": "Celebrate",
    "animation_speed": 100,
    "reduced_motion": False,
    "show_streamer": True,
    "show_speech_bubbles": True,
    "enable_reactions": True,
    "restore_active_after_restart": False,
}

CHECKIN_MESSAGES = ["I'm here!", "Ready to study!", "Let's work!"]
DANCE_COOLDOWN_SECONDS = 10


def initialize_checkin(repository: TaskRepository) -> None:
    """Create Check-In tables without changing existing task-table behavior."""
    with repository.connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS checkin_users (
                user_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                preferred_shape TEXT,
                preferred_color TEXT,
                assigned_shape TEXT NOT NULL,
                assigned_color TEXT NOT NULL,
                total_checkins INTEGER NOT NULL DEFAULT 0,
                last_checkin_at TEXT,
                active_state TEXT NOT NULL DEFAULT 'inactive',
                is_streamer INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS checkin_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                user_id TEXT,
                display_name TEXT,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            """
        )


@dataclass
class CheckInService:
    repository: TaskRepository

    def __post_init__(self) -> None:
        initialize_checkin(self.repository)

    def checkin(self, user_id: str, display_name: str, is_streamer: bool = False) -> dict[str, Any]:
        shape = STREAMER_SHAPE if is_streamer else self.preferred_shape(user_id) or random.choice(VIEWER_SHAPES)
        color = DEFAULT_COLORS[shape]
        timestamp = now()
        with self.repository.connection() as conn:
            existing = conn.execute("SELECT * FROM checkin_users WHERE user_id=?", (user_id,)).fetchone()
            if existing and existing["active_state"] == "active":
                return self._row(existing)
            conn.execute(
                """
                INSERT INTO checkin_users
                    (user_id, display_name, preferred_shape, preferred_color, assigned_shape, assigned_color,
                     total_checkins, last_checkin_at, active_state, is_streamer, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, 'active', ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    assigned_shape=excluded.assigned_shape,
                    assigned_color=excluded.assigned_color,
                    total_checkins=checkin_users.total_checkins + CASE WHEN checkin_users.active_state='active' THEN 0 ELSE 1 END,
                    last_checkin_at=excluded.last_checkin_at,
                    active_state='active',
                    is_streamer=excluded.is_streamer,
                    updated_at=excluded.updated_at
                """,
                (user_id, display_name, None if is_streamer else shape, color, shape, color, timestamp, int(is_streamer), timestamp),
            )
            row = conn.execute("SELECT * FROM checkin_users WHERE user_id=?", (user_id,)).fetchone()
        payload = self._row(row)
        self.emit_event("checkin_joined", user_id, display_name, {"shape": payload["shape"], "message": random.choice(CHECKIN_MESSAGES)})
        return payload

    def leave(self, user_id: str, display_name: str | None = None) -> bool:
        timestamp = now()
        with self.repository.connection() as conn:
            row = conn.execute("SELECT * FROM checkin_users WHERE user_id=? AND active_state='active'", (user_id,)).fetchone()
            if not row:
                return False
            conn.execute("UPDATE checkin_users SET active_state='leaving', updated_at=? WHERE user_id=?", (timestamp, user_id))
        self.emit_event("checkin_left", user_id, display_name or row["display_name"], {"animation": "black_portal"})
        with self.repository.connection() as conn:
            conn.execute("UPDATE checkin_users SET active_state='inactive', updated_at=? WHERE user_id=?", (now(), user_id))
        return True

    def dance(self, user_id: str, display_name: str) -> str:
        timestamp = now()
        with self.repository.connection() as conn:
            row = conn.execute("SELECT * FROM checkin_users WHERE user_id=? AND active_state='active'", (user_id,)).fetchone()
            if not row:
                return "not_checked_in"
            recent = conn.execute(
                "SELECT created_at FROM checkin_events WHERE type='checkin_dance' AND user_id=? ORDER BY id DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            if recent:
                try:
                    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(recent["created_at"])).total_seconds()
                except ValueError:
                    elapsed = DANCE_COOLDOWN_SECONDS
                if elapsed < DANCE_COOLDOWN_SECONDS:
                    return "cooldown"
        self.emit_event("checkin_dance", user_id, display_name, {"animation": "dance", "duration": 3})
        return "dancing"

    def set_shape(self, user_id: str, display_name: str, shape: str) -> dict[str, Any]:
        clean = shape.casefold().strip()
        if clean == STREAMER_SHAPE:
            raise ValueError("The octagon is reserved for the streamer.")
        if clean not in VIEWER_SHAPES:
            raise ValueError("Choose circle, triangle, or square.")
        timestamp = now()
        with self.repository.connection() as conn:
            conn.execute(
                """
                INSERT INTO checkin_users
                    (user_id, display_name, preferred_shape, preferred_color, assigned_shape, assigned_color, active_state, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'inactive', ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    preferred_shape=excluded.preferred_shape,
                    preferred_color=excluded.preferred_color,
                    assigned_shape=CASE WHEN checkin_users.is_streamer=1 THEN checkin_users.assigned_shape ELSE excluded.assigned_shape END,
                    assigned_color=CASE WHEN checkin_users.is_streamer=1 THEN checkin_users.assigned_color ELSE excluded.assigned_color END,
                    updated_at=excluded.updated_at
                """,
                (user_id, display_name, clean, DEFAULT_COLORS[clean], clean, DEFAULT_COLORS[clean], timestamp),
            )
            row = conn.execute("SELECT * FROM checkin_users WHERE user_id=?", (user_id,)).fetchone()
        self.emit_event("shape_changed", user_id, display_name, {"shape": clean})
        return self._row(row)

    def preferred_shape(self, user_id: str) -> str | None:
        with self.repository.connection() as conn:
            row = conn.execute("SELECT preferred_shape FROM checkin_users WHERE user_id=?", (user_id,)).fetchone()
        return row["preferred_shape"] if row and row["preferred_shape"] in VIEWER_SHAPES else None

    def active_checkins(self) -> list[dict[str, Any]]:
        with self.repository.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM checkin_users WHERE active_state='active' ORDER BY is_streamer DESC, last_checkin_at, display_name COLLATE NOCASE"
            ).fetchall()
        return [self._row(row) for row in rows]

    def all_users(self) -> list[dict[str, Any]]:
        with self.repository.connection() as conn:
            rows = conn.execute("SELECT * FROM checkin_users ORDER BY is_streamer DESC, display_name COLLATE NOCASE").fetchall()
        return [self._row(row) for row in rows]

    def clear_active(self) -> None:
        with self.repository.connection() as conn:
            conn.execute("UPDATE checkin_users SET active_state='inactive', updated_at=? WHERE active_state!='inactive'", (now(),))
        self.emit_event("checkins_cleared", None, None, {})

    def reset_for_session_end(self) -> None:
        if not self.repository.get_setting("checkin_restore_active_after_restart", False):
            self.clear_active()

    def emit_event(self, event_type: str, user_id: str | None, display_name: str | None, payload: dict[str, Any]) -> None:
        import json

        with self.repository.connection() as conn:
            conn.execute(
                "INSERT INTO checkin_events(type, user_id, display_name, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (event_type, user_id, display_name, json.dumps(payload), now()),
            )

    def events_since(self, last_id: int = 0) -> list[dict[str, Any]]:
        import json

        with self.repository.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM checkin_events WHERE id>? ORDER BY id ASC LIMIT 100",
                (last_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "type": row["type"],
                "user_id": row["user_id"],
                "display_name": row["display_name"],
                **json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    def snapshot(self) -> dict[str, Any]:
        appearance = {**DEFAULT_CHECKIN_APPEARANCE, **self.repository.get_setting("checkin_appearance", {})}
        return {
            "active": self.active_checkins(),
            "appearance": appearance,
            "events": self.events_since(0)[-25:],
        }

    @staticmethod
    def _row(row) -> dict[str, Any]:
        return {
            "user_id": row["user_id"],
            "display_name": row["display_name"],
            "preferred_shape": row["preferred_shape"],
            "shape": row["assigned_shape"],
            "color": row["assigned_color"],
            "total_checkins": row["total_checkins"],
            "last_checkin_at": row["last_checkin_at"],
            "state": row["active_state"],
            "is_streamer": bool(row["is_streamer"]),
        }
