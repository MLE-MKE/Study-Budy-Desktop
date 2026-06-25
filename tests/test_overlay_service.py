from study_budy.overlay_service import create_overlay_app
from study_budy.server import OverlayServer, OverlayServerError, choose_available_port
from study_budy.storage import TaskRepository


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
