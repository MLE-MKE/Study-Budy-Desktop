"""Centralized, safe Twitch task command handling."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from .storage import TaskRepository, ValidationError

COMMANDS = {
    "task": "!task <description> — add a task",
    "tasks": "!tasks — show your current tasks",
    "done": "!done <number> — finish a task",
    "undo": "!undo <number> — reopen a task",
    "cleardone": "!cleardone — archive finished tasks",
    "help": "!help — show commands",
}


@dataclass
class ChatCommandService:
    repository: TaskRepository
    _last_seen: dict[str, float] | None = None

    def __post_init__(self) -> None:
        self._last_seen = {}

    def handle(self, user_id: str, display_name: str, message: str) -> str | None:
        if not message.startswith("!"):
            return None
        now = monotonic()
        if now - self._last_seen.get(user_id, 0) < 1:
            return "Please wait a moment before repeating a Study Budy command."
        self._last_seen[user_id] = now
        command, _, argument = message[1:].partition(" ")
        command, argument = command.casefold(), argument.strip()
        participant = self.repository.get_or_create_participant(display_name, "viewer", user_id)
        tasks = self.repository.list_tasks(participant["id"])
        if command == "task":
            try:
                self.repository.add_task(display_name, argument)
            except ValidationError as exc:
                return str(exc)
            return f"Task added for {display_name}."
        if command == "tasks":
            active = [task for task in tasks if not task["is_complete"]]
            return "No active tasks." if not active else " | ".join(f"{i + 1}. {task['text']}" for i, task in enumerate(active))
        if command in {"done", "undo"}:
            if not argument.isdigit() or int(argument) < 1 or int(argument) > len(tasks):
                return f"Use !{command} followed by a valid task number."
            self.repository.set_task_complete(tasks[int(argument) - 1]["id"], command == "done")
            return "Task completed." if command == "done" else "Task reopened."
        if command == "cleardone":
            count = self.repository.archive_completed(participant["id"])
            return f"Archived {count} finished task(s)."
        if command == "help":
            return "Study Budy: " + " | ".join(COMMANDS.values())
        return None
