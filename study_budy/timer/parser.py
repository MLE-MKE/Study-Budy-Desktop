"""Shared timer duration parsing and formatting."""

from __future__ import annotations


MAX_TIMER_SECONDS = 24 * 60 * 60


class TimerParseError(ValueError):
    """Raised when a timer duration cannot be accepted."""


def parse_duration(value: str) -> int:
    text = value.strip()
    if not text:
        raise TimerParseError("Enter a timer duration.")
    if text.startswith("-"):
        raise TimerParseError("Timer duration cannot be negative.")
    if any(ch not in "0123456789:" for ch in text):
        raise TimerParseError("Use numbers and colons only, such as 30:00 or 1:30:00.")
    parts = text.split(":")
    if len(parts) > 3 or any(part == "" for part in parts):
        raise TimerParseError("Use seconds, minutes:seconds, or hours:minutes:seconds.")
    try:
        numbers = [int(part) for part in parts]
    except ValueError as exc:
        raise TimerParseError("Use whole numbers only.") from exc
    if len(parts) == 1:
        seconds = numbers[0]
    elif len(parts) == 2:
        minutes, second_part = numbers
        if second_part > 59:
            raise TimerParseError("Seconds must be 59 or less.")
        seconds = minutes * 60 + second_part
    else:
        hours, minutes, second_part = numbers
        if minutes > 59:
            raise TimerParseError("Minutes must be 59 or less when hours are included.")
        if second_part > 59:
            raise TimerParseError("Seconds must be 59 or less.")
        seconds = hours * 3600 + minutes * 60 + second_part
    if seconds > MAX_TIMER_SECONDS:
        raise TimerParseError("Timer duration cannot exceed 24 hours.")
    return seconds


def format_duration(seconds: int) -> str:
    safe = max(0, int(seconds))
    hours, remainder = divmod(safe, 3600)
    minutes, second_part = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{second_part:02d}"
    return f"{minutes:02d}:{second_part:02d}"
