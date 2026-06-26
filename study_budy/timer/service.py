"""Python-owned countdown timer state for the Browser Source overlay."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import re
from typing import Any

from .models import DEFAULT_TIMER_APPEARANCE, DEFAULT_TIMER_STATE
from .parser import MAX_TIMER_SECONDS, TimerParseError, format_duration, parse_duration
from ..storage import TaskRepository

LOG = logging.getLogger(__name__)
HEX_COLOR = re.compile(r"^#[0-9A-F]{6}$")
FONT_OPTIONS = {"Press Start 2P", "Segoe UI", "Arial", "Comic Sans MS", "Consolas", "Impact"}
OUTLINE_MODES = {"none", "white", "black", "custom"}
ALIGNMENTS = {"left", "center", "right"}
VERTICAL_ALIGNMENTS = {"top", "center", "bottom"}
ANIMATIONS = {"none", "pulse", "bounce", "flash", "fade"}


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
            self._write_appearance(self.normalize_appearance(DEFAULT_TIMER_APPEARANCE))
        key = str(self.repository.path.resolve())
        if key not in _RESTORED_REPOSITORIES:
            self._restore_after_startup()
            _RESTORED_REPOSITORIES.add(key)

    def state(self) -> dict[str, Any]:
        state = {**DEFAULT_TIMER_STATE, **(self.repository.get_setting("timer_state", {}) or {})}
        return self._normalize_running_state(state)

    def appearance(self) -> dict[str, Any]:
        stored = self.repository.get_setting("timer_appearance", None)
        if stored is None:
            stored = self._read_namespaced_appearance()
        return self.normalize_appearance({**DEFAULT_TIMER_APPEARANCE, **(stored or {})})

    def set_appearance(self, appearance: dict[str, Any]) -> dict[str, Any]:
        current = self.appearance()
        current.update(appearance)
        normalized = self.normalize_appearance(current)
        self._write_appearance(normalized)
        saved = self.appearance()
        if saved != normalized:
            LOG.error("Timer appearance settings round trip mismatch.")
            raise RuntimeError("Timer appearance settings could not be saved.")
        return normalized

    def reset_appearance(self) -> dict[str, Any]:
        self._write_appearance(self.normalize_appearance(DEFAULT_TIMER_APPEARANCE))
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
            "appearance_event": {
                "type": "timer_appearance",
                "event_id": self.repository.get_setting("timer_appearance_event_id", 0),
                "appearance": appearance,
            },
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

    def normalize_appearance(self, values: dict[str, Any]) -> dict[str, Any]:
        normalized = {**DEFAULT_TIMER_APPEARANCE, **values}
        normalized["font_family"] = normalized["font_family"] if normalized.get("font_family") in FONT_OPTIONS else DEFAULT_TIMER_APPEARANCE["font_family"]
        normalized["font_size"] = self._clamp_int(normalized.get("font_size"), 16, 300)
        normalized["font_weight"] = self._clamp_int(normalized.get("font_weight"), 100, 900)
        normalized["text_color"] = self._normalize_color(normalized.get("text_color"), DEFAULT_TIMER_APPEARANCE["text_color"])
        normalized["outline_mode"] = str(normalized.get("outline_mode", "black")).casefold()
        if normalized["outline_mode"] not in OUTLINE_MODES:
            normalized["outline_mode"] = "black"
        normalized["outline_color"] = self._normalize_color(normalized.get("outline_color"), DEFAULT_TIMER_APPEARANCE["outline_color"])
        if normalized["outline_mode"] == "white":
            normalized["outline_color"] = "#FFFFFF"
        elif normalized["outline_mode"] == "black":
            normalized["outline_color"] = "#000000"
        elif normalized["outline_mode"] == "none":
            normalized["outline_width"] = 0
        normalized["outline_width"] = self._clamp_int(normalized.get("outline_width"), 0, 12)
        normalized["text_opacity"] = self._clamp_int(normalized.get("text_opacity"), 0, 100)
        normalized["letter_spacing"] = self._clamp_int(normalized.get("letter_spacing"), -10, 30)
        normalized["background_enabled"] = bool(normalized.get("background_enabled"))
        normalized["background_color"] = self._normalize_color(normalized.get("background_color"), DEFAULT_TIMER_APPEARANCE["background_color"])
        normalized["background_opacity"] = self._clamp_int(normalized.get("background_opacity"), 0, 100)
        normalized["padding"] = self._clamp_int(normalized.get("padding"), 0, 200)
        normalized["corner_radius"] = self._clamp_int(normalized.get("corner_radius"), 0, 100)
        if normalized.get("horizontal_align") not in ALIGNMENTS:
            normalized["horizontal_align"] = "center"
        if normalized.get("vertical_align") not in VERTICAL_ALIGNMENTS:
            normalized["vertical_align"] = "center"
        if normalized.get("completion_animation") not in ANIMATIONS:
            normalized["completion_animation"] = "pulse"
        normalized["hide_when_inactive"] = bool(normalized.get("hide_when_inactive"))
        normalized["completion_sound"] = bool(normalized.get("completion_sound", False))
        return normalized

    def _write_appearance(self, appearance: dict[str, Any]) -> None:
        self.repository.set_setting("timer_appearance", appearance)
        for key, value in appearance.items():
            self.repository.set_setting(f"timer.appearance.{key}", value)
        event_id = int(self.repository.get_setting("timer_appearance_event_id", 0)) + 1
        self.repository.set_setting("timer_appearance_event_id", event_id)

    def _read_namespaced_appearance(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for key in DEFAULT_TIMER_APPEARANCE:
            value = self.repository.get_setting(f"timer.appearance.{key}", None)
            if value is not None:
                values[key] = value
        return values

    @staticmethod
    def _normalize_color(value: Any, fallback: str) -> str:
        text = str(value or "").strip()
        if not text:
            return fallback
        if not text.startswith("#"):
            text = f"#{text}"
        if len(text) == 4:
            text = "#" + "".join(ch * 2 for ch in text[1:])
        text = text.upper()
        return text if HEX_COLOR.match(text) else fallback
