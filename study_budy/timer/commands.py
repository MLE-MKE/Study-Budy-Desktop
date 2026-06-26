"""Twitch chat command handling for the Study Timer."""

from __future__ import annotations

from dataclasses import dataclass

from .parser import TimerParseError, format_duration, parse_duration
from .service import TimerService
from ..storage import TaskRepository


HELP_TEXT = (
    "Timer for streamer/mods: !ttimer start <time>, pause, add <time>, clear"
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
                if not argument.strip():
                    return "Include a duration. Example: !ttimer start 30:00"
                state = self.timer.start(argument)
                return f"Timer started for {format_duration(state['remaining_seconds'])}."
            if action == "pause":
                before = self.timer.state()
                if before["state"] != "running":
                    return "There is no running timer to pause."
                state = self.timer.pause()
                return f"Timer paused at {format_duration(state['remaining_seconds'])}."
            if action == "add":
                if not argument.strip():
                    return "Include a duration. Example: !ttimer add 05:00"
                amount = parse_duration(argument)
                state = self.timer.add_time(argument)
                return f"Added {format_duration(amount)}. Timer now has {format_duration(state['remaining_seconds'])} remaining."
            if action == "clear":
                self.timer.clear()
                return "Timer cleared."
            if action == "help":
                return HELP_TEXT
        except TimerParseError as exc:
            text = str(exc)
            if "Enter a timer duration" in text:
                return f"Include a duration. Example: !ttimer {action or 'start'} 30:00"
            if "cannot exceed 24 hours" in text:
                return "The timer cannot exceed 24:00:00."
            if action == "start":
                return "Use !ttimer start MM:SS or !ttimer start HH:MM:SS. Maximum: 24:00:00."
            return str(exc)
        return HELP_TEXT
