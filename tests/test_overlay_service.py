from study_budy.overlay_service import create_overlay_app
from study_budy.server import OverlayServer, OverlayServerError, choose_available_port
from study_budy.storage import TaskRepository
from study_budy.twitch.chat import BOT_METADATA_KEY, STREAMER_METADATA_KEY


def test_overlay_snapshot_escapes_data_by_returning_json(tmp_path):
    repository = TaskRepository(tmp_path / "tasks.db")
    repository.initialize()
    repository.add_task("<viewer>", "<script>alert(1)</script>")
    response = create_overlay_app(repository).test_client().get("/api/overlay")
    assert response.status_code == 200
    assert response.json["participants"][0]["tasks"][0]["text"] == "<script>alert(1)</script>"
    # The browser template renders task strings through TextNode, never innerHTML.
    html = create_overlay_app(repository).test_client().get("/overlay").get_data(as_text=True)
    assert "safeText" in html and "innerHTML" not in html


def test_overlay_cycle_duration_is_at_least_eight_seconds(tmp_path):
    repository = TaskRepository(tmp_path / "tasks.db")
    repository.initialize()
    repository.set_setting("appearance", {"cycle_seconds": 3})
    response = create_overlay_app(repository).test_client().get("/api/overlay")
    assert response.status_code == 200
    assert response.json["appearance"]["cycle_seconds"] == 8


def test_overlay_list_mode_pins_connected_streamer_and_keeps_others_below(tmp_path):
    repository = TaskRepository(tmp_path / "tasks.db")
    repository.initialize()
    repository.set_setting("appearance", {"layout_mode": "list"})
    repository.set_setting(STREAMER_METADATA_KEY, {"login": "killer_queen55", "display_name": "Killer_Queen55", "user_id": "streamer-id"})
    repository.set_setting(BOT_METADATA_KEY, {"login": "study_bot", "display_name": "Study Bot", "user_id": "bot-id"})
    repository.add_task("Study Bot", "Bot task", twitch_user_id="bot-id")
    repository.add_task("Killer_Queen55", "Streamer task", twitch_user_id="streamer-id")
    repository.add_task("Alex", "Read chapter")
    client = create_overlay_app(repository).test_client()
    response = client.get("/api/overlay")
    participants = response.json["participants"]

    assert participants[0]["display_name"] == "Killer_Queen55"
    assert participants[0]["participant_type"] == "streamer"
    assert participants[0]["tasks"][0]["text"] == "Streamer task"
    assert [item["display_name"] for item in participants[1:]] == ["Alex", "Study Bot"]

    html = client.get("/overlay").get_data(as_text=True)
    assert "settings.layout_mode === 'list'" in html
    assert "AUTOMATIC LIST SCROLLING" in html
    assert "content.scrollHeight - viewport.clientHeight" in html
    assert "requestAnimationFrame" in html
    assert "streamer_top" not in html
    assert "Math.max(8" in html


def test_overlay_list_mode_combines_duplicate_streamer_records_and_excludes_archived(tmp_path):
    repository = TaskRepository(tmp_path / "tasks.db")
    repository.initialize()
    repository.set_setting("appearance", {"layout_mode": "list"})
    repository.set_setting(STREAMER_METADATA_KEY, {"login": "killer_queen55", "display_name": "Killer_Queen55", "user_id": "streamer-id"})
    repository.add_task("Streamer", "Manual streamer task", "streamer")
    chat_task = repository.add_task("Killer_Queen55", "Chat streamer task", twitch_user_id="streamer-id")
    archived = repository.add_task("Killer_Queen55", "Archived streamer task", twitch_user_id="streamer-id")
    repository.archive_task(archived["id"])
    repository.add_task("Jamie", "Viewer task")

    payload = create_overlay_app(repository).test_client().get("/api/overlay").get_json()
    participants = payload["participants"]

    assert [item["display_name"] for item in participants] == ["Killer_Queen55", "Jamie"]
    assert [task["text"] for task in participants[0]["tasks"]] == ["Manual streamer task", chat_task["text"]]
    assert all(task["text"] != "Archived streamer task" for participant in participants for task in participant["tasks"])


def test_overlay_migrates_old_streamer_top_layout_value_to_list(tmp_path):
    repository = TaskRepository(tmp_path / "tasks.db")
    repository.initialize()
    repository.set_setting("appearance", {"layout_mode": "Streamer on Top"})

    payload = create_overlay_app(repository).test_client().get("/api/overlay").get_json()

    assert payload["appearance"]["layout_mode"] == "list"


def test_overlay_reports_port_conflict(tmp_path):
    repository = TaskRepository(tmp_path / "tasks.db")
    repository.initialize()
    first = OverlayServer(repository, port=5167)
    second = OverlayServer(repository, port=5167)
    first.start()
    try:
        try:
            second.start()
        except OverlayServerError:
            pass
        else:
            raise AssertionError("Expected an overlay port conflict")
    finally:
        first.stop()


def test_port_choice_moves_on_when_preferred_port_is_busy(tmp_path):
    repository = TaskRepository(tmp_path / "tasks.db")
    repository.initialize()
    first = OverlayServer(repository, port=5168)
    first.start()
    try:
        assert choose_available_port("127.0.0.1", 5168) != 5168
    finally:
        first.stop()
