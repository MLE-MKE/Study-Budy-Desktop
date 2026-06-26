"""Centralized, safe Twitch chat command handling."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from .checkin import CheckInService
from .storage import TaskRepository, ValidationError
from .timer.commands import TimerCommandService

COMMANDS = {
    "task": "!task <description> - add a task",
    "addtask": "!addtask <description> - add a task",
    "tasks": "!tasks - show your current tasks",
    "tasklist": "!tasklist - show your current tasks",
    "done": "!done <number> - finish a task",
    "undo": "!undo <number> - reopen a task",
    "cleardone": "!cleardone - archive finished tasks",
    "clear": "!clear - archive finished tasks",
    "checkin": "!checkin - join the Check-In shape overlay",
    "shape": "!shape circle|triangle|square - choose your shape",
    "leave": "!leave - leave the Check-In shape overlay",
    "ttimer": "!ttimer help - show Study Timer commands",
    "help": "!help - show commands",
}


@dataclass
class ChatCommandService:
    repository: TaskRepository
    _last_seen: dict[str, float] | None = None

    def __post_init__(self) -> None:
        self._last_seen = {}
        self.checkins = CheckInService(self.repository)
        self.timers = TimerCommandService(self.repository)

    def handle(
        self,
        user_id: str,
        display_name: str,
        message: str,
        *,
        is_broadcaster: bool = False,
        is_moderator: bool = False,
    ) -> str | None:
        if not message.startswith("!"):
            return None
        timestamp = monotonic()
        if timestamp - self._last_seen.get(user_id, 0) < 1:
            return "Please wait a moment before repeating a Study Budy command."
        self._last_seen[user_id] = timestamp
        command, _, argument = message[1:].partition(" ")
        command, argument = command.casefold(), argument.strip()
        participant = self.repository.get_or_create_participant(display_name, "viewer", user_id)
        tasks = self.repository.list_tasks(participant["id"])

        if command == "ttimer":
            return self.timers.handle(message, is_broadcaster=is_broadcaster, is_moderator=is_moderator)

        if command in {"task", "addtask"}:
            try:
                self.repository.add_task(display_name, argument)
            except ValidationError as exc:
                return str(exc)
            self.checkins.emit_event("task_added", user_id, display_name, {})
            return f"Task added for {display_name}."

        if command in {"tasks", "tasklist"}:
            active = [task for task in tasks if not task["is_complete"]]
            return "No active tasks." if not active else " | ".join(f"{i + 1}. {task['text']}" for i, task in enumerate(active))

        if command in {"done", "undo"}:
            if not argument.isdigit() or int(argument) < 1 or int(argument) > len(tasks):
                return f"Use !{command} followed by a valid task number."
            self.repository.set_task_complete(tasks[int(argument) - 1]["id"], command == "done")
            if command == "done":
                self.checkins.emit_event("task_completed", user_id, display_name, {})
            return "Task completed." if command == "done" else "Task reopened."

        if command in {"cleardone", "clear"}:
            count = self.repository.archive_completed(participant["id"])
            return f"Archived {count} finished task(s)."

        if command == "checkin":
            checkin = self.checkins.checkin(user_id, display_name)
            return f"{display_name} checked in as a {checkin['shape']}."

        if command == "shape":
            try:
                shape = self.checkins.set_shape(user_id, display_name, argument)
            except ValueError as exc:
                return str(exc)
            return f"{display_name}'s shape is now {shape['shape']}."

        if command == "leave":
            if self.checkins.leave(user_id, display_name):
                return f"{display_name} left the Check-In overlay."
            return "You are not currently checked in."

        if command == "help":
            return "Study Budy: " + " | ".join(COMMANDS.values())

        return None
