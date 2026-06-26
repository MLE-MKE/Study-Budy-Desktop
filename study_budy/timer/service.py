"""Python-owned countdown timer state for the Browser Source overlay."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .models import DEFAULT_TIMER_APPEARANCE, DEFAULT_TIMER_STATE
from .parser import MAX_TIMER_SECONDS, TimerParseError, format_duration, parse_duration
from ..storage import TaskRepository


def timestamp() -> float:
    return datetime.now(timezone.utc).timestamp()


_RESTORED_REPOSITORIES: set[str] = set()


@dataclass
class TimerService:
    repository: TaskRepository

    def __post_init__(self) -> None:
        if self.repository.get_setting("timer_state", None) is None:
            self.repository.set_setting("timer_state", DEFAULT_TIMER_STATE)
        if self.repository.get_setting("timer_appearance", None) is None:
            self.repository.set_setting("timer_appearance", DEFAULT_TIMER_APPEARANCE)
        key = str(self.repository.path.resolve())
        if key not in _RESTORED_REPOSITORIES:
            self._restore_after_startup()
            _RESTORED_REPOSITORIES.add(key)

    def state(self) -> dict[str, Any]:
        state = {**DEFAULT_TIMER_STATE, **(self.repository.get_setting("timer_state", {}) or {})}
        return self._normalize_running_state(state)

    def appearance(self) -> dict[str, Any]:
        return {**DEFAULT_TIMER_APPEARANCE, **(self.repository.get_setting("timer_appearance", {}) or {})}

    def set_appearance(self, appearance: dict[str, Any]) -> dict[str, Any]:
        current = self.appearance()
        current.update(appearance)
        current["font_size"] = self._clamp_int(current.get("font_size"), 16, 300)
        current["outline_width"] = self._clamp_int(current.get("outline_width"), 0, 12)
        current["text_opacity"] = self._clamp_int(current.get("text_opacity"), 0, 100)
        current["background_opacity"] = self._clamp_int(current.get("background_opacity"), 0, 100)
        current["padding"] = self._clamp_int(current.get("padding"), 0, 200)
        current["corner_radius"] = self._clamp_int(current.get("corner_radius"), 0, 100)
        self.repository.set_setting("timer_appearance", current)
        return current

    def reset_appearance(self) -> dict[str, Any]:
        self.repository.set_setting("timer_appearance", DEFAULT_TIMER_APPEARANCE)
        return self.appearance()

    def start(self, value: str | int) -> dict[str, Any]:
        seconds = parse_duration(str(value)) if isinstance(value, str) else int(value)
        if seconds > MAX_TIMER_SECONDS:
            raise TimerParseError("Timer duration cannot exceed 24 hours.")
        now_value = timestamp()
        return self._save(
            {
                **DEFAULT_TIMER_STATE,
                "configured_seconds": seconds,
                "remaining_seconds": seconds,
                "state": "running" if seconds > 0 else "complete",
                "started_at": now_value,
                "updated_at": now_value,
                "completed_at": now_value if seconds == 0 else None,
                "completion_fired": seconds == 0,
                "continue_after_restart": self.continue_after_restart(),
            }
        )

    def pause(self) -> dict[str, Any]:
        state = self.state()
        if state["state"] == "running":
            state["state"] = "paused"
            state["paused_at"] = timestamp()
            state["updated_at"] = state["paused_at"]
        return self._save(state)

    def resume(self) -> dict[str, Any]:
        state = self.state()
        if state["state"] != "paused" or state["remaining_seconds"] <= 0:
            return state
        state["state"] = "running"
        state["paused_at"] = None
        state["updated_at"] = timestamp()
        return self._save(state)

    def add_time(self, value: str | int) -> dict[str, Any]:
        amount = parse_duration(str(value)) if isinstance(value, str) else int(value)
        state = self.state()
        remaining = min(MAX_TIMER_SECONDS, state["remaining_seconds"] + amount)
        if state["remaining_seconds"] + amount > MAX_TIMER_SECONDS:
            raise TimerParseError("Timer duration cannot exceed 24 hours.")
        state["remaining_seconds"] = remaining
        state["configured_seconds"] = min(MAX_TIMER_SECONDS, max(state["configured_seconds"], remaining))
        state["completion_fired"] = False
        state["completed_at"] = None
        if remaining > 0 and state["state"] in {"stopped", "complete"}:
            state["state"] = "running"
        state["updated_at"] = timestamp()
        return self._save(state)

    def subtract_time(self, value: str | int) -> dict[str, Any]:
        amount = parse_duration(str(value)) if isinstance(value, str) else int(value)
        state = self.state()
        state["remaining_seconds"] = max(0, state["remaining_seconds"] - amount)
        state["updated_at"] = timestamp()
        if state["remaining_seconds"] == 0:
            state["state"] = "complete"
            state["completed_at"] = state["updated_at"]
            state["completion_fired"] = True
        return self._save(state)

    def reset(self) -> dict[str, Any]:
        state = self.state()
        state["remaining_seconds"] = state["configured_seconds"]
        state["state"] = "stopped"
        state["paused_at"] = None
        state["updated_at"] = timestamp()
        state["completed_at"] = None
        state["completion_fired"] = False
        return self._save(state)

    def clear(self) -> dict[str, Any]:
        state = self.state()
        state["remaining_seconds"] = 0
        state["state"] = "stopped"
        state["paused_at"] = None
        state["updated_at"] = timestamp()
        state["completed_at"] = None
        state["completion_fired"] = False
        return self._save(state)

    def complete(self) -> dict[str, Any]:
        state = self.state()
        state["remaining_seconds"] = 0
        state["state"] = "complete"
        state["updated_at"] = timestamp()
        state["completed_at"] = state["completed_at"] or state["updated_at"]
        state["completion_fired"] = True
        return self._save(state)

    def set_continue_after_restart(self, enabled: bool) -> dict[str, Any]:
        state = self.state()
        state["continue_after_restart"] = bool(enabled)
        return self._save(state)

    def snapshot(self) -> dict[str, Any]:
        state = self.state()
        appearance = self.appearance()
        return {
            "type": "timer_state",
            **state,
            "remaining_display": format_duration(state["remaining_seconds"]),
            "server_timestamp": timestamp(),
            "appearance": appearance,
        }

    def continue_after_restart(self) -> bool:
        return bool((self.repository.get_setting("timer_state", {}) or {}).get("continue_after_restart", True))

    def _normalize_running_state(self, state: dict[str, Any]) -> dict[str, Any]:
        if state.get("state") != "running":
            return state
        now_value = timestamp()
        updated_at = float(state.get("updated_at") or now_value)
        elapsed = max(0, int(now_value - updated_at))
        if elapsed:
            state["remaining_seconds"] = max(0, int(state.get("remaining_seconds", 0)) - elapsed)
            state["updated_at"] = now_value
        if state["remaining_seconds"] <= 0:
            state["remaining_seconds"] = 0
            state["state"] = "complete"
            state["completed_at"] = state.get("completed_at") or now_value
            state["completion_fired"] = True
        return self._save(state)

    def _restore_after_startup(self) -> None:
        state = {**DEFAULT_TIMER_STATE, **(self.repository.get_setting("timer_state", {}) or {})}
        if state.get("state") == "running" and not state.get("continue_after_restart", True):
            now_value = timestamp()
            updated_at = float(state.get("updated_at") or now_value)
            elapsed = max(0, int(now_value - updated_at))
            state["remaining_seconds"] = max(0, int(state.get("remaining_seconds", 0)) - elapsed)
            state["state"] = "complete" if state["remaining_seconds"] <= 0 else "paused"
            state["paused_at"] = now_value
            state["updated_at"] = now_value
            if state["remaining_seconds"] <= 0:
                state["completed_at"] = now_value
                state["completion_fired"] = True
            self._save(state)

    def _save(self, state: dict[str, Any]) -> dict[str, Any]:
        clean = {**DEFAULT_TIMER_STATE, **state}
        clean["configured_seconds"] = self._clamp_int(clean.get("configured_seconds"), 0, MAX_TIMER_SECONDS)
        clean["remaining_seconds"] = self._clamp_int(clean.get("remaining_seconds"), 0, MAX_TIMER_SECONDS)
        if clean["state"] not in {"stopped", "running", "paused", "complete"}:
            clean["state"] = "stopped"
        self.repository.set_setting("timer_state", clean)
        return clean

    @staticmethod
    def _clamp_int(value: Any, minimum: int, maximum: int) -> int:
        try:
            integer = int(value)
        except (TypeError, ValueError):
            integer = minimum
        return max(minimum, min(maximum, integer))
