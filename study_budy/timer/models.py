"""Timer defaults and state helpers."""

from __future__ import annotations


DEFAULT_TIMER_APPEARANCE = {
    "font_family": "Segoe UI",
    "font_size": 96,
    "font_weight": 700,
    "text_color": "#FFFFFF",
    "text_opacity": 100,
    "letter_spacing": 0,
    "outline_mode": "black",
    "outline_color": "#000000",
    "outline_width": 3,
    "background_enabled": False,
    "background_color": "#000000",
    "background_opacity": 0,
    "padding": 8,
    "corner_radius": 8,
    "horizontal_align": "center",
    "vertical_align": "center",
    "completion_animation": "pulse",
    "hide_when_inactive": False,
    "completion_sound": False,
}


DEFAULT_TIMER_STATE = {
    "configured_seconds": 0,
    "remaining_seconds": 0,
    "state": "stopped",
    "started_at": None,
    "paused_at": None,
    "updated_at": None,
    "completed_at": None,
    "completion_fired": False,
    "continue_after_restart": True,
}


TIMER_COMMAND_PERMISSIONS = {
    "broadcaster": True,
    "moderator": True,
    "viewer": False,
}
