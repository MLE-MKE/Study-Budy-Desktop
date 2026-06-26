"""Timer defaults and state helpers."""

from __future__ import annotations


DEFAULT_TIMER_APPEARANCE = {
    "font_family": "Press Start 2P",
    "font_size": 96,
    "font_weight": "700",
    "text_color": "#ffffff",
    "text_opacity": 100,
    "letter_spacing": 1,
    "outline_mode": "black",
    "outline_color": "#000000",
    "outline_width": 4,
    "background_enabled": False,
    "background_color": "#000000",
    "background_opacity": 45,
    "padding": 24,
    "corner_radius": 18,
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
