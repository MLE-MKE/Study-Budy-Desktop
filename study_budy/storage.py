"""SQLite-backed task and settings repository.

All mutations pass through this module so the desktop UI, Twitch connector and
localhost overlay agree on one durable source of truth.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

MAX_TASK_LENGTH = 280


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ValidationError(ValueError):
    """Raised when user-supplied task data cannot safely be accepted."""


class TaskRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.path = Path(database_path)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS participants (
                    id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL UNIQUE,
                    twitch_user_id TEXT,
                    participant_type TEXT NOT NULL DEFAULT 'viewer',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
                    text TEXT NOT NULL,
                    is_complete INTEGER NOT NULL DEFAULT 0,
                    position INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                );
                CREATE INDEX IF NOT EXISTS ix_tasks_participant_position
                    ON tasks(participant_id, position);
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    status TEXT NOT NULL
                );
                """
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
            if "archived_at" not in columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN archived_at TEXT")
            participant_columns = {row["name"] for row in conn.execute("PRAGMA table_info(participants)")}
            if "twitch_user_id" not in participant_columns:
                conn.execute("ALTER TABLE participants ADD COLUMN twitch_user_id TEXT")

    @staticmethod
    def validate_task_text(text: str) -> str:
        clean = " ".join(text.split())
        if not clean:
            raise ValidationError("Enter a task description.")
        if len(clean) > MAX_TASK_LENGTH:
            raise ValidationError(f"Tasks can be at most {MAX_TASK_LENGTH} characters.")
        return clean

    @staticmethod
    def _participant(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _task(row: sqlite3.Row) -> dict[str, Any]:
        task = dict(row)
        task["is_complete"] = bool(task["is_complete"])
        return task

    def get_or_create_participant(
        self, display_name: str, participant_type: str = "viewer", twitch_user_id: str | None = None
    ) -> dict[str, Any]:
        name = " ".join(display_name.split())
        if not name or len(name) > 80:
            raise ValidationError("Participant names must be between 1 and 80 characters.")
        normalized = name.casefold()
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM participants WHERE normalized_name = ?", (normalized,)
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE participants SET display_name=?, twitch_user_id=COALESCE(?, twitch_user_id), is_active=1, updated_at=? WHERE id=?",
                    (name, twitch_user_id, now(), row["id"]),
                )
                row = conn.execute("SELECT * FROM participants WHERE id=?", (row["id"],)).fetchone()
                return self._participant(row)
            participant_id = str(uuid4())
            timestamp = now()
            conn.execute(
                """INSERT INTO participants
                (id, display_name, normalized_name, twitch_user_id, participant_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (participant_id, name, normalized, twitch_user_id, participant_type, timestamp, timestamp),
            )
            return self._participant(conn.execute("SELECT * FROM participants WHERE id=?", (participant_id,)).fetchone())

    def add_task(self, participant_name: str, text: str, participant_type: str = "viewer") -> dict[str, Any]:
        clean = self.validate_task_text(text)
        participant = self.get_or_create_participant(participant_name, participant_type)
        with self.connection() as conn:
            position = conn.execute(
                "SELECT COALESCE(MAX(position), 0) + 1 FROM tasks WHERE participant_id=?",
                (participant["id"],),
            ).fetchone()[0]
            task_id, timestamp = str(uuid4()), now()
            conn.execute(
                """INSERT INTO tasks (id, participant_id, text, position, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (task_id, participant["id"], clean, position, timestamp, timestamp),
            )
            return self._task(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())

    def list_participants(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        query = """
            SELECT p.*, SUM(CASE WHEN t.is_complete=0 THEN 1 ELSE 0 END) AS incomplete_count,
                   SUM(CASE WHEN t.is_complete=1 THEN 1 ELSE 0 END) AS complete_count
            FROM participants p LEFT JOIN tasks t ON t.participant_id=p.id AND t.archived_at IS NULL
        """
        if not include_inactive:
            query += " WHERE p.is_active=1"
        query += " GROUP BY p.id ORDER BY CASE p.participant_type WHEN 'streamer' THEN 0 ELSE 1 END, p.display_name COLLATE NOCASE"
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(query)]

    def list_tasks(self, participant_id: str | None = None, include_completed: bool = True, include_archived: bool = False) -> list[dict[str, Any]]:
        query = "SELECT * FROM tasks"
        clauses, args = [], []
        if participant_id:
            clauses.append("participant_id=?")
            args.append(participant_id)
        if not include_completed:
            clauses.append("is_complete=0")
        if not include_archived:
            clauses.append("archived_at IS NULL")
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY participant_id, position"
        with self.connection() as conn:
            return [self._task(row) for row in conn.execute(query, args)]

    def task_snapshot(self, include_completed: bool = True, include_archived: bool = False) -> list[dict[str, Any]]:
        participants = self.list_participants()
        tasks = self.list_tasks(include_completed=include_completed, include_archived=include_archived)
        by_participant: dict[str, list[dict[str, Any]]] = {}
        for task in tasks:
            by_participant.setdefault(task["participant_id"], []).append(task)
        for participant in participants:
            participant["tasks"] = by_participant.get(participant["id"], [])
        return participants

    def update_task(self, task_id: str, text: str) -> dict[str, Any]:
        clean = self.validate_task_text(text)
        with self.connection() as conn:
            result = conn.execute("UPDATE tasks SET text=?, updated_at=? WHERE id=?", (clean, now(), task_id))
            if not result.rowcount:
                raise KeyError("Task not found.")
            return self._task(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())

    def set_task_complete(self, task_id: str, complete: bool) -> dict[str, Any]:
        with self.connection() as conn:
            previous = conn.execute("SELECT is_complete FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not previous:
                raise KeyError("Task not found.")
            result = conn.execute(
                "UPDATE tasks SET is_complete=?, completed_at=?, updated_at=? WHERE id=?",
                (int(complete), now() if complete else None, now(), task_id),
            )
            if not result.rowcount:
                raise KeyError("Task not found.")
            if complete and not previous["is_complete"]:
                row = conn.execute("SELECT value_json FROM settings WHERE key='lifetime_completed'").fetchone()
                total = (json.loads(row["value_json"]) if row else 0) + 1
                conn.execute(
                    "INSERT INTO settings(key, value_json, updated_at) VALUES ('lifetime_completed', ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at",
                    (json.dumps(total), now()),
                )
            return self._task(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())

    def archive_task(self, task_id: str) -> None:
        with self.connection() as conn:
            if not conn.execute("UPDATE tasks SET archived_at=?, updated_at=? WHERE id=?", (now(), now(), task_id)).rowcount:
                raise KeyError("Task not found.")

    def archive_completed(self, participant_id: str | None = None) -> int:
        with self.connection() as conn:
            query, args = "UPDATE tasks SET archived_at=?, updated_at=? WHERE is_complete=1 AND archived_at IS NULL", [now(), now()]
            if participant_id:
                query += " AND participant_id=?"
                args.append(participant_id)
            return conn.execute(query, args).rowcount

    def lifetime_completed(self) -> int:
        return int(self.get_setting("lifetime_completed", 0))

    def start_session(self) -> None:
        with self.connection() as conn:
            active = conn.execute("SELECT id FROM sessions WHERE status='live' LIMIT 1").fetchone()
            if not active:
                conn.execute("INSERT INTO sessions(id, started_at, status) VALUES (?, ?, 'live')", (str(uuid4()), now()))

    def end_session(self) -> None:
        with self.connection() as conn:
            conn.execute("UPDATE sessions SET status='ended', ended_at=? WHERE status='live'", (now(),))

    def total_sessions(self) -> int:
        with self.connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]

    def delete_task(self, task_id: str) -> None:
        with self.connection() as conn:
            if not conn.execute("DELETE FROM tasks WHERE id=?", (task_id,)).rowcount:
                raise KeyError("Task not found.")

    def remove_participant(self, participant_id: str, permanently: bool = False) -> None:
        with self.connection() as conn:
            if permanently:
                result = conn.execute("DELETE FROM participants WHERE id=?", (participant_id,))
            else:
                result = conn.execute("UPDATE participants SET is_active=0, updated_at=? WHERE id=?", (now(), participant_id))
            if not result.rowcount:
                raise KeyError("Participant not found.")

    def reorder_task(self, task_id: str, direction: int) -> None:
        if direction not in (-1, 1):
            raise ValidationError("Tasks can only move one position at a time.")
        with self.connection() as conn:
            current = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not current:
                raise KeyError("Task not found.")
            comparison = "<" if direction < 0 else ">"
            order = "DESC" if direction < 0 else "ASC"
            adjacent = conn.execute(
                f"""SELECT * FROM tasks WHERE participant_id=? AND position {comparison} ?
                ORDER BY position {order} LIMIT 1""",
                (current["participant_id"], current["position"]),
            ).fetchone()
            if adjacent:
                conn.execute("UPDATE tasks SET position=? WHERE id=?", (adjacent["position"], current["id"]))
                conn.execute("UPDATE tasks SET position=? WHERE id=?", (current["position"], adjacent["id"]))

    def set_setting(self, key: str, value: Any) -> None:
        with self.connection() as conn:
            conn.execute(
                """INSERT INTO settings(key, value_json, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at""",
                (key, json.dumps(value), now()),
            )

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self.connection() as conn:
            row = conn.execute("SELECT value_json FROM settings WHERE key=?", (key,)).fetchone()
        return default if row is None else json.loads(row["value_json"])

    def export_json(self, destination: str | Path) -> Path:
        payload = {"format": "study-budy-export-v1", "participants": self.task_snapshot(), "settings": {}}
        with self.connection() as conn:
            payload["settings"] = {row["key"]: json.loads(row["value_json"]) for row in conn.execute("SELECT * FROM settings")}
        destination = Path(destination)
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return destination

    def import_json(self, source: str | Path) -> int:
        """Merge a Study Budy export after validating every supported task."""
        try:
            payload = json.loads(Path(source).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValidationError("The selected file is not a valid Study Budy JSON export.") from exc
        if payload.get("format") != "study-budy-export-v1" or not isinstance(payload.get("participants"), list):
            raise ValidationError("This file is not a Study Budy task export.")
        imported = 0
        for person in payload["participants"]:
            if not isinstance(person, dict) or not isinstance(person.get("display_name"), str):
                raise ValidationError("The export contains an invalid participant.")
            participant = self.get_or_create_participant(person["display_name"], person.get("participant_type", "viewer"))
            for task in person.get("tasks", []):
                if not isinstance(task, dict) or not isinstance(task.get("text"), str):
                    raise ValidationError("The export contains an invalid task.")
                created = self.add_task(participant["display_name"], task["text"], participant["participant_type"])
                if task.get("is_complete"):
                    self.set_task_complete(created["id"], True)
                imported += 1
        for key, value in payload.get("settings", {}).items():
            if isinstance(key, str):
                self.set_setting(key, value)
        return imported

    def migrate_legacy_json(self, source: str | Path) -> int:
        """One-time, idempotent best-effort migration of the prototype tasks.json."""
        source = Path(source)
        marker = "legacy_json_migrated"
        if self.get_setting(marker, False) or not source.exists():
            return 0
        try:
            legacy = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 0
        if not isinstance(legacy, dict):
            return 0
        count = 0
        for name, tasks in legacy.items():
            if not isinstance(name, str) or not isinstance(tasks, list):
                continue
            for task in tasks:
                text = task.get("text") if isinstance(task, dict) else str(task)
                try:
                    added = self.add_task(name, text)
                except ValidationError:
                    continue
                if isinstance(task, dict) and task.get("done"):
                    self.set_task_complete(added["id"], True)
                count += 1
        self.set_setting(marker, True)
        return count

    def backup(self, backup_directory: str | Path) -> Path:
        target = Path(backup_directory) / f"study-budy-{datetime.now():%Y%m%d-%H%M%S}.db"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.path, target)
        return target
