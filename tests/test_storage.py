import json
import pytest
from study_budy.storage import MAX_TASK_LENGTH, TaskRepository, ValidationError

@pytest.fixture
def repository(tmp_path):
    repo = TaskRepository(tmp_path / "study-budy.db")
    repo.initialize()
    return repo

def test_creates_edits_completes_and_deletes_tasks(repository):
    task = repository.add_task("Streamer", "  Plan   stream  ", "streamer")
    assert task["text"] == "Plan stream"
    assert repository.update_task(task["id"], "Plan stream intro")["text"] == "Plan stream intro"
    assert repository.set_task_complete(task["id"], True)["is_complete"] is True
    repository.delete_task(task["id"])
    assert repository.list_tasks() == []

def test_persists_task_order_and_participant_removal(repository):
    first = repository.add_task("luna", "Read")
    second = repository.add_task("luna", "Write")
    repository.reorder_task(second["id"], -1)
    assert [task["text"] for task in repository.list_tasks()] == ["Write", "Read"]
    person = repository.list_participants()[0]
    repository.remove_participant(person["id"])
    assert repository.list_participants() == []
    assert len(repository.list_tasks()) == 2

def test_settings_and_export_persist(repository, tmp_path):
    repository.add_task("luna", "Study")
    repository.set_setting("appearance", {"layout_mode": "streamer_top"})
    assert repository.get_setting("appearance")["layout_mode"] == "streamer_top"
    export = repository.export_json(tmp_path / "tasks.json")
    data = json.loads(export.read_text(encoding="utf-8"))
    assert data["participants"][0]["tasks"][0]["text"] == "Study"

@pytest.mark.parametrize("text", ["", "   ", "x" * (MAX_TASK_LENGTH + 1)])
def test_rejects_invalid_task_input(repository, text):
    with pytest.raises(ValidationError):
        repository.add_task("luna", text)
