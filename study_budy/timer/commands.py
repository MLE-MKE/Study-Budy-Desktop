"""Twitch chat command handling for the Study Timer."""

from __future__ import annotations

from dataclasses import dataclass

from .parser import TimerParseError, format_duration
from .service import TimerService
from ..storage import TaskRepository


HELP_TEXT = (
    "Study Timer: !ttimer start 30:00 | pause | resume | add 05:00 | "
    "subtract 01:00 | reset | clear | status"
)


@dataclass
class TimerCommandService:
    repository: TaskRepository

    def __post_init__(self) -> None:
        self.timer = TimerService(self.repository)

    def handle(
        self,
        message: str,
        *,
        is_broadcaster: bool = False,
        is_moderator: bool = False,
    ) -> str | None:
        text = message.strip()
        if not text.startswith("!"):
            return None
        command, _, rest = text[1:].partition(" ")
        if command.casefold() != "ttimer":
            return None
        if not (is_broadcaster or is_moderator):
            return "Only the broadcaster and moderators can control the Study Budy timer."
        action, _, argument = rest.strip().partition(" ")
        action = action.casefold()
        try:
            if action == "start":
                state = self.timer.start(argument)
                return f"Study timer started: {format_duration(state['remaining_seconds'])}."
            if action == "pause":
                state = self.timer.pause()
                return f"Study timer paused: {format_duration(state['remaining_seconds'])} remaining."
            if action in {"resume", "unpause"}:
                before = self.timer.state()
                state = self.timer.resume()
                if before["state"] != "paused":
                    return "There is no paused Study timer to resume."
                return f"Study timer resumed: {format_duration(state['remaining_seconds'])} remaining."
            if action == "add":
                state = self.timer.add_time(argument)
                return f"Study timer updated: {format_duration(state['remaining_seconds'])} remaining."
            if action in {"subtract", "sub"}:
                state = self.timer.subtract_time(argument)
                return f"Study timer updated: {format_duration(state['remaining_seconds'])} remaining."
            if action == "reset":
                state = self.timer.reset()
                return f"Study timer reset to {format_duration(state['remaining_seconds'])}."
            if action == "clear":
                self.timer.clear()
                return "Study timer cleared."
            if action == "status":
                state = self.timer.state()
                return f"Study timer is {state['state']}: {format_duration(state['remaining_seconds'])} remaining."
            if action == "help":
                return HELP_TEXT
        except TimerParseError as exc:
            return str(exc)
        return HELP_TEXT
