"""Centralized, safe Twitch chat command handling."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from .checkin import CheckInService
from .storage import TaskRepository, ValidationError
from .timer.commands import TimerCommandService

COMMANDS = {
    "addtask": "!addtask <description> - add a task",
    "tasklist": "!tasklist - show your current tasks",
    "done": "!done <task number> - complete one task",
    "clear": "!clear <task number> - clear one task",
    "clearall": "!clearall - clear your whole task list",
    "checkin": "!checkin - join the Check-In shape overlay",
    "checkout": "!checkout - leave the Check-In shape overlay",
    "dance": "!dance - make your checked-in shape dance",
    "ttimer": "!ttimer start <time>|pause|add <time>|clear",
    "help": "!help - show commands",
}
HELP_TEXT = (
    "Tasks: !addtask <task>, !tasklist, !done #, !clear #, !clearall | "
    "Check-In: !checkin, !checkout, !dance | "
    "Timer for streamer/mods: !ttimer start <time>, pause, add <time>, clear"
)


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
        command, argument = command.casefold(), " ".join(argument.split())
        participant = self.repository.get_or_create_participant(display_name, "viewer", user_id)
        tasks = self.repository.list_tasks(participant["id"])

        if command == "ttimer":
            return self.timers.handle(message, is_broadcaster=is_broadcaster, is_moderator=is_moderator)

        if command == "addtask":
            if not argument:
                return "Please include a task. Example: !addtask Finish laundry"
            try:
                task = self.repository.add_task(display_name, argument, twitch_user_id=user_id)
            except ValidationError as exc:
                return str(exc)
            self.checkins.emit_event("task_added", user_id, display_name, {})
            updated_tasks = self.repository.list_tasks(participant["id"])
            number = next((index + 1 for index, item in enumerate(updated_tasks) if item["id"] == task["id"]), len(updated_tasks))
            return f"Added task {number}: {task['text']}"

        if command == "tasklist":
            if not tasks:
                return "Your task list is empty. Add one with !addtask"
            parts = [f"{index + 1}. {'✅ ' if task['is_complete'] else ''}{task['text']}" for index, task in enumerate(tasks)]
            response = "Your tasks: " + " | ".join(parts)
            if len(response) > 430:
                return f"You have {len(tasks)} task(s). Use !done # or !clear # with the task number shown in Study Budy."
            return response

        if command == "done":
            index = self._task_number(argument, "done")
            if isinstance(index, str):
                return index
            if index < 1 or index > len(tasks):
                return f"Task {argument} was not found. Use !tasklist to see your task numbers."
            task = self.repository.set_task_complete(tasks[index - 1]["id"], True)
            self.checkins.emit_event("task_completed", user_id, display_name, {})
            return f"Completed task {index}: {task['text']}"

        if command == "clear":
            index = self._task_number(argument, "clear")
            if isinstance(index, str):
                return index
            if index < 1 or index > len(tasks):
                return f"Task {argument} was not found. Use !tasklist to see your task numbers."
            task = tasks[index - 1]
            self.repository.archive_task(task["id"])
            return f"Cleared task {index}: {task['text']}"

        if command == "clearall":
            count = self.repository.archive_all_tasks(participant["id"])
            return "Your task list is already empty." if count == 0 else "Your task list has been cleared."

        if command == "checkin":
            if any(item["user_id"] == user_id for item in self.checkins.active_checkins()):
                return "You are already checked in."
            self.checkins.checkin(user_id, display_name)
            return "You are checked in!"

        if command == "checkout":
            if self.checkins.leave(user_id, display_name):
                return "You are checked out. See you next time!"
            return "You are not currently checked in."

        if command == "dance":
            result = self.checkins.dance(user_id, display_name)
            if result == "dancing":
                return "Your shape is dancing!"
            if result == "cooldown":
                return "Your shape needs a moment before dancing again."
            return "Check in first with !checkin"

        if command == "help":
            return HELP_TEXT

        return None

    @staticmethod
    def _task_number(argument: str, command: str) -> int | str:
        if not argument or not argument.isdigit():
            return f"Use a task number. Example: !{command} 2"
        return int(argument)
