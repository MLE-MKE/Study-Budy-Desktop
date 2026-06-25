from study_budy.commands import ChatCommandService
from study_budy.storage import TaskRepository


def repository(tmp_path):
    repo = TaskRepository(tmp_path / "tasks.db")
    repo.initialize()
    return repo


def test_viewer_is_created_from_task_command_and_html_is_stored_as_text(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    assert service.handle("42", "Alex", "!task <script>alert(1)</script>") == "Task added for Alex."
    participant = repo.list_participants()[0]
    assert participant["twitch_user_id"] == "42"
    assert repo.task_snapshot()[0]["tasks"][0]["text"] == "<script>alert(1)</script>"


def test_empty_and_long_commands_are_rejected(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    assert service.handle("1", "Alex", "!task ") == "Enter a task description."
    service._last_seen.clear()
    assert "at most" in service.handle("1", "Alex", "!task " + "x" * 281)


def test_reopen_and_archive_do_not_reduce_lifetime_completed(tmp_path):
    repo = repository(tmp_path)
    task = repo.add_task("Alex", "Study")
    repo.set_task_complete(task["id"], True)
    assert repo.lifetime_completed() == 1
    repo.set_task_complete(task["id"], False)
    repo.set_task_complete(task["id"], True)
    assert repo.lifetime_completed() == 2
    repo.archive_completed()
    assert repo.lifetime_completed() == 2
    assert repo.task_snapshot()[0]["tasks"] == []


def test_active_finished_and_all_data_sets(tmp_path):
    repo = repository(tmp_path)
    active = repo.add_task("Alex", "Read")
    finished = repo.add_task("Alex", "Write")
    repo.set_task_complete(finished["id"], True)
    all_tasks = repo.list_tasks()
    assert len(all_tasks) == 2
    assert [task["id"] for task in repo.list_tasks(include_completed=False)] == [active["id"]]
    assert [task["id"] for task in all_tasks if task["is_complete"]] == [finished["id"]]
