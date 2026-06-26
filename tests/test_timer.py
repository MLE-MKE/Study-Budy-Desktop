from __future__ import annotations

import time

import pytest

from study_budy.commands import ChatCommandService
from study_budy.overlay_service import create_overlay_app
from study_budy.storage import TaskRepository
from study_budy.timer import service as timer_service_module
from study_budy.timer.parser import TimerParseError, format_duration, parse_duration
from study_budy.timer.service import TimerService


@pytest.fixture
def repository(tmp_path):
    repo = TaskRepository(tmp_path / "study-budy.db")
    repo.initialize()
    timer_service_module._RESTORED_REPOSITORIES.clear()
    return repo


@pytest.mark.parametrize(
    ("value", "seconds", "display"),
    [
        ("45", 45, "00:45"),
        ("05:00", 300, "05:00"),
        ("30:00", 1800, "30:00"),
        ("1:30:00", 5400, "01:30:00"),
        ("24:00:00", 86400, "24:00:00"),
        ("90:00", 5400, "01:30:00"),
    ],
)
def test_parse_valid_durations(value, seconds, display):
    assert parse_duration(value) == seconds
    assert format_duration(seconds) == display


@pytest.mark.parametrize("value", ["", "-1", "abc", "1.5", "1:2:3:4", "01:00:99", "1:60:00", "24:00:01", "25:00:00"])
def test_parse_rejects_invalid_durations(value):
    with pytest.raises(TimerParseError):
        parse_duration(value)


def test_timer_service_start_pause_resume_reset_clear_and_complete(repository):
    timer = TimerService(repository)
    assert timer.start("30:00")["state"] == "running"
    assert timer.pause()["state"] == "paused"
    assert timer.resume()["state"] == "running"
    assert timer.add_time("05:00")["remaining_seconds"] == 2100
    assert timer.subtract_time("01:00")["remaining_seconds"] == 2040
    assert timer.reset()["state"] == "stopped"
    assert timer.state()["remaining_seconds"] == 2100
    assert timer.clear()["remaining_seconds"] == 0
    assert timer.complete()["state"] == "complete"


def test_timer_never_goes_negative_or_above_24_hours(repository):
    timer = TimerService(repository)
    timer.start("10")
    assert timer.subtract_time("20")["remaining_seconds"] == 0
    timer.start("24:00:00")
    with pytest.raises(TimerParseError):
        timer.add_time("1")


def test_completion_fires_once_and_browser_refresh_does_not_reset(repository):
    timer = TimerService(repository)
    timer.start("1")
    state = repository.get_setting("timer_state")
    state["updated_at"] = state["updated_at"] - 5
    repository.set_setting("timer_state", state)
    first = timer.snapshot()
    second = TimerService(repository).snapshot()
    assert first["state"] == "complete"
    assert second["state"] == "complete"
    assert second["remaining_seconds"] == 0
    assert second["completion_fired"] is True


def test_restart_restoration_calculates_elapsed_time(repository):
    timer = TimerService(repository)
    timer.start("30")
    state = repository.get_setting("timer_state")
    state["updated_at"] = state["updated_at"] - 10
    repository.set_setting("timer_state", state)
    timer_service_module._RESTORED_REPOSITORIES.clear()
    restored = TimerService(repository).state()
    assert 18 <= restored["remaining_seconds"] <= 20
    assert restored["state"] == "running"


def test_paused_restart_behavior_when_continue_is_off(repository):
    timer = TimerService(repository)
    timer.start("30")
    state = repository.get_setting("timer_state")
    state["continue_after_restart"] = False
    state["updated_at"] = state["updated_at"] - 10
    repository.set_setting("timer_state", state)
    timer_service_module._RESTORED_REPOSITORIES.clear()
    restored = TimerService(repository).state()
    assert restored["state"] == "paused"
    assert 18 <= restored["remaining_seconds"] <= 20


def test_multiple_overlays_remain_synchronized(repository):
    timer = TimerService(repository)
    timer.start("05:00")
    client_a = create_overlay_app(repository).test_client()
    client_b = create_overlay_app(repository).test_client()
    assert client_a.get("/api/timer").get_json()["remaining_seconds"] == client_b.get("/api/timer").get_json()["remaining_seconds"]


def test_ttimer_commands_and_permissions(repository):
    commands = ChatCommandService(repository)
    assert commands.handle("viewer", "Viewer", "!timer start 30:00") is None
    assert "Only the broadcaster" in commands.handle("viewer2", "Viewer", "!ttimer start 30:00")
    assert "started" in commands.handle("broadcaster", "Streamer", "!ttimer start 30:00", is_broadcaster=True)
    commands._last_seen.clear()
    assert "paused" in commands.handle("mod1", "Mod", "!ttimer pause", is_moderator=True)
    commands._last_seen.clear()
    assert "resumed" in commands.handle("mod2", "Mod", "!ttimer unpause", is_moderator=True)
    commands._last_seen.clear()
    assert "updated" in commands.handle("mod3", "Mod", "!ttimer add 05:00", is_moderator=True)
    commands._last_seen.clear()
    assert "updated" in commands.handle("mod4", "Mod", "!ttimer subtract 01:00", is_moderator=True)
    commands._last_seen.clear()
    assert "updated" in commands.handle("mod5", "Mod", "!ttimer sub 01:00", is_moderator=True)
    commands._last_seen.clear()
    assert "reset" in commands.handle("mod6", "Mod", "!ttimer reset", is_moderator=True)
    commands._last_seen.clear()
    assert "running" not in commands.handle("mod7", "Mod", "!ttimer status", is_moderator=True).casefold()
    commands._last_seen.clear()
    assert "Study Timer" in commands.handle("mod8", "Mod", "!ttimer help", is_moderator=True)
    commands._last_seen.clear()
    before = TimerService(repository).state()
    assert "cannot exceed" in commands.handle("mod9", "Mod", "!ttimer start 25:00:00", is_moderator=True)
    assert TimerService(repository).state()["remaining_seconds"] == before["remaining_seconds"]
    commands._last_seen.clear()
    assert "cleared" in commands.handle("mod10", "Mod", "!ttimer clear", is_moderator=True)


def test_timer_overlay_routes_are_separate_and_apply_appearance(repository):
    timer = TimerService(repository)
    timer.start("1:00:00")
    timer.set_appearance({"outline_mode": "white", "font_family": "Press Start 2P", "text_color": "<script>alert(1)</script>"})
    client = create_overlay_app(repository).test_client()
    assert client.get("/overlay").status_code == 200
    assert client.get("/checkin").status_code == 200
    assert client.get("/timer").status_code == 200
    payload = client.get("/api/timer").get_json()
    assert payload["remaining_display"] == "01:00:00"
    assert payload["appearance"]["font_family"] == "Press Start 2P"
    css = client.get("/timer/timer.css").get_data(as_text=True)
    js = client.get("/timer/timer.js").get_data(as_text=True)
    assert "PressStart2P-Regular.ttf" in css
    assert "webkitTextStroke" in js
    assert "innerHTML" not in js
    assert client.get("/timer/fonts/PressStart2P-Regular.ttf").status_code == 200


def test_no_black_and_no_outline_modes_are_supported(repository):
    timer = TimerService(repository)
    assert timer.set_appearance({"outline_mode": "black", "outline_width": 4})["outline_mode"] == "black"
    assert timer.set_appearance({"outline_mode": "none", "outline_width": 0})["outline_width"] == 0
