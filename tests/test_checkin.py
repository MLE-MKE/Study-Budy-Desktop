from study_budy.checkin import CheckInService, STREAMER_SHAPE, VIEWER_SHAPES
from study_budy.commands import ChatCommandService
from study_budy.overlay_service import create_overlay_app
from study_budy.storage import TaskRepository


def repository(tmp_path):
    repo = TaskRepository(tmp_path / "checkin.db")
    repo.initialize()
    return repo


def test_checkin_adds_one_viewer_and_duplicates_do_not_duplicate(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    assert "checked in" in service.handle("42", "Alex", "!checkin")
    service._last_seen.clear()
    assert "checked in" in service.handle("42", "Alex", "!checkin")
    active = CheckInService(repo).active_checkins()
    assert len(active) == 1
    assert active[0]["shape"] in VIEWER_SHAPES


def test_streamer_shape_is_octagon_and_viewer_cannot_select_octagon(tmp_path):
    repo = repository(tmp_path)
    checkins = CheckInService(repo)
    streamer = checkins.checkin("streamer", "Killer_Queen55", is_streamer=True)
    assert streamer["shape"] == STREAMER_SHAPE
    service = ChatCommandService(repo)
    assert service.handle("42", "Alex", "!shape octagon") == "The octagon is reserved for the streamer."


def test_shape_command_changes_and_persists_preference(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    assert service.handle("42", "Alex", "!shape triangle") == "Alex's shape is now triangle."
    service._last_seen.clear()
    service.handle("42", "Alex", "!checkin")
    active = CheckInService(repo).active_checkins()
    assert active[0]["shape"] == "triangle"
    reloaded = TaskRepository(repo.path)
    reloaded.initialize()
    assert CheckInService(reloaded).preferred_shape("42") == "triangle"


def test_leave_emits_portal_event(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    service.handle("42", "Alex", "!checkin")
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!leave") == "Alex left the Check-In overlay."
    events = CheckInService(repo).events_since()
    assert any(event["type"] == "checkin_left" and event["animation"] == "black_portal" for event in events)
    assert CheckInService(repo).active_checkins() == []


def test_successful_task_events_emit_reactions_but_failures_do_not(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    assert service.handle("42", "Alex", "!task Read") == "Task added for Alex."
    events = CheckInService(repo).events_since()
    assert any(event["type"] == "task_added" for event in events)
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!done 1") == "Task completed."
    events = CheckInService(repo).events_since()
    assert any(event["type"] == "task_completed" for event in events)
    before = len(events)
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!done 99") == "Use !done followed by a valid task number."
    assert len(CheckInService(repo).events_since()) == before
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!task ") == "Enter a task description."
    assert len(CheckInService(repo).events_since()) == before


def test_checkin_overlay_route_is_separate_and_escapes_with_text_nodes(tmp_path):
    repo = repository(tmp_path)
    CheckInService(repo).checkin("evil", "<script>alert(1)</script>")
    client = create_overlay_app(repo).test_client()
    task_html = client.get("/overlay").get_data(as_text=True)
    checkin_html = client.get("/checkin").get_data(as_text=True)
    checkin_js = client.get("/checkin/checkin.js").get_data(as_text=True)
    assert client.get("/api/checkin").status_code == 200
    assert task_html != checkin_html
    assert "safeText" in checkin_js
    assert "innerHTML" not in checkin_js
    payload = client.get("/api/checkin").get_json()
    assert payload["active"][0]["display_name"] == "<script>alert(1)</script>"


def test_session_reset_clears_active_checkins_but_keeps_history(tmp_path):
    repo = repository(tmp_path)
    checkins = CheckInService(repo)
    checkins.checkin("42", "Alex")
    checkins.reset_for_session_end()
    assert checkins.active_checkins() == []
    assert checkins.all_users()[0]["total_checkins"] == 1


def test_checkin_settings_persist_and_api_exposes_no_secrets(tmp_path):
    repo = repository(tmp_path)
    repo.set_setting("checkin_appearance", {"viewer_shape_size": 84})
    payload = create_overlay_app(repo).test_client().get("/api/checkin").get_json()
    assert payload["appearance"]["viewer_shape_size"] == 84
    assert "token" not in str(payload).casefold()
    assert "password" not in str(payload).casefold()
