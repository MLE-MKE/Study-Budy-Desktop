from __future__ import annotations

import time

import pytest
from PySide6.QtWidgets import QApplication

from study_budy.commands import ChatCommandService
from study_budy.overlay_service import create_overlay_app
from study_budy.server import OverlayServer
from study_budy.storage import TaskRepository
from study_budy.timer import service as timer_service_module
from study_budy.timer.models import DEFAULT_TIMER_APPEARANCE
from study_budy.timer.parser import TimerParseError, format_duration, parse_duration
from study_budy.timer.service import TimerService
from study_budy.timer_view import TimerView


@pytest.fixture
def repository(tmp_path):
    repo = TaskRepository(tmp_path / "study-budy.db")
    repo.initialize()
    timer_service_module._RESTORED_REPOSITORIES.clear()
    return repo


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


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


def test_timer_appearance_save_pipeline_and_storage_isolation(repository):
    repository.set_setting("appearance", {"text_color": "#111111"})
    repository.set_setting("checkin_appearance", {"name_color": "#222222"})
    timer = TimerService(repository)
    before = timer.state()
    saved = timer.set_appearance(
        {
            "font_family": "Press Start 2P",
            "font_size": 144,
            "text_color": "a855f7",
            "outline_mode": "white",
            "outline_width": 5,
            "background_enabled": True,
            "background_color": "#123456",
            "background_opacity": 33,
        }
    )
    assert saved["text_color"] == "#A855F7"
    assert saved["outline_color"] == "#FFFFFF"
    assert repository.get_setting("timer.appearance.text_color") == "#A855F7"
    assert repository.get_setting("timer.appearance.font_family") == "Press Start 2P"
    assert repository.get_setting("timer.appearance.font_size") == 144
    assert repository.get_setting("timer.appearance.outline_mode") == "white"
    assert repository.get_setting("timer.appearance.outline_width") == 5
    assert repository.get_setting("appearance") == {"text_color": "#111111"}
    assert repository.get_setting("checkin_appearance") == {"name_color": "#222222"}
    assert timer.state()["remaining_seconds"] == before["remaining_seconds"]


def test_timer_api_returns_appearance_event_and_no_store_cache(repository):
    timer = TimerService(repository)
    timer.set_appearance({"text_color": "#A855F7"})
    client = create_overlay_app(repository).test_client()
    response = client.get("/api/timer")
    payload = response.get_json()
    assert response.headers["Cache-Control"].startswith("no-store")
    assert payload["appearance_event"]["type"] == "timer_appearance"
    assert payload["appearance_event"]["appearance"]["text_color"] == "#A855F7"
    assert client.get("/timer").headers["Cache-Control"].startswith("no-store")


def test_timer_view_dirty_save_reset_and_reopen(qapp, repository):
    server = OverlayServer(repository)
    view = TimerView(repository, server, {"start": lambda: None, "stop": lambda: None, "restart": lambda: None})
    assert not view.save_button.isEnabled()
    view.text_color.setText("#A855F7")
    assert view.dirty
    assert view.save_button.isEnabled()
    view.save_appearance()
    assert not view.dirty
    assert not view.save_button.isEnabled()
    assert view.control_message.text() == "Timer appearance settings saved."
    assert TimerService(repository).appearance()["text_color"] == "#A855F7"
    reopened = TimerView(repository, server, {"start": lambda: None, "stop": lambda: None, "restart": lambda: None})
    assert reopened.text_color.text() == "#A855F7"
    reopened.reset_appearance()
    assert TimerService(repository).appearance()["text_color"] == DEFAULT_TIMER_APPEARANCE["text_color"]
