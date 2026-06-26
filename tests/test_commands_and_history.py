from study_budy.commands import ChatCommandService
from study_budy.storage import TaskRepository


def repository(tmp_path):
    repo = TaskRepository(tmp_path / "tasks.db")
    repo.initialize()
    return repo


def test_viewer_is_created_from_task_command_and_html_is_stored_as_text(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    assert service.handle("42", "Alex", "!addtask <script>alert(1)</script>") == "Added task 1: <script>alert(1)</script>"
    participant = repo.list_participants()[0]
    assert participant["twitch_user_id"] == "42"
    assert repo.task_snapshot()[0]["tasks"][0]["text"] == "<script>alert(1)</script>"


def test_empty_and_long_commands_are_rejected(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    assert service.handle("1", "Alex", "!addtask ") == "Please include a task. Example: !addtask Finish laundry"
    service._last_seen.clear()
    assert "at most" in service.handle("1", "Alex", "!addtask " + "x" * 281)


def test_required_twitch_command_aliases_route_to_existing_services(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    assert service.handle("42", "Alex", "!addtask Test task") == "Added task 1: Test task"
    service._last_seen.clear()
    assert "1. Test task" in service.handle("42", "Alex", "!tasklist")
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!done 1") == "Completed task 1: Test task"
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!clear 1") == "Cleared task 1: Test task"
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!checkin") == "You are checked in!"
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!dance") == "Your shape is dancing!"
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!checkout") == "You are checked out. See you next time!"
    service._last_seen.clear()
    assert "Only the broadcaster" in service.handle("42", "Alex", "!ttimer start 00:30")


def test_addtask_can_add_multiple_tasks_with_pipe_separator(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    response = service.handle("42", "Alex", "!addtask go ouside | take a nap | eat some food| jump")

    assert response == "Added 4 tasks as 1-4: go ouside | take a nap | eat some food | jump"
    participant = repo.list_participants()[0]
    tasks = repo.list_tasks(participant["id"])
    assert [task["text"] for task in tasks] == ["go ouside", "take a nap", "eat some food", "jump"]


def test_addtask_pipe_separator_ignores_empty_parts(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    response = service.handle("42", "Alex", "!addtask Laundry || Stretch |   | Read")

    assert response == "Added 3 tasks as 1-3: Laundry | Stretch | Read"
    participant = repo.list_participants()[0]
    assert [task["text"] for task in repo.list_tasks(participant["id"])] == ["Laundry", "Stretch", "Read"]


def test_old_conflicting_aliases_are_disabled(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    for command in ("!task Read", "!tasks", "!leave", "!cleardone", "!timer start 30:00", "!shape circle"):
        assert service.handle("42", "Alex", command) is None
        service._last_seen.clear()


def test_task_user_id_survives_display_name_change(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    service.handle("42", "Alex", "!addtask Laundry")
    service._last_seen.clear()
    service.handle("42", "AlexNew", "!addtask Stretch")
    participants = repo.list_participants()
    assert len(participants) == 1
    assert participants[0]["display_name"] == "AlexNew"
    assert len(repo.list_tasks(participants[0]["id"])) == 2


def test_clearall_archives_only_requesting_users_tasks_and_preserves_totals(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    service.handle("42", "Alex", "!addtask Laundry")
    service._last_seen.clear()
    service.handle("42", "Alex", "!addtask Stretch")
    service._last_seen.clear()
    service.handle("99", "Jamie", "!addtask Read")
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!done 2") == "Completed task 2: Stretch"
    assert repo.lifetime_completed() == 1
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!clearall") == "Your task list has been cleared."
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!tasklist") == "Your task list is empty. Add one with !addtask"
    service._last_seen.clear()
    assert "1. Read" in service.handle("99", "Jamie", "!tasklist")
    assert repo.lifetime_completed() == 1


def test_invalid_task_numbers_have_useful_messages(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    service.handle("42", "Alex", "!addtask Laundry")
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!done") == "Use a task number. Example: !done 2"
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!done abc") == "Use a task number. Example: !done 2"
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!done 99") == "Task 99 was not found. Use !tasklist to see your task numbers."
    service._last_seen.clear()
    assert service.handle("42", "Alex", "!clear abc") == "Use a task number. Example: !clear 2"


def test_commands_are_case_insensitive_and_preserve_task_capitalization(tmp_path):
    repo = repository(tmp_path)
    service = ChatCommandService(repo)
    assert service.handle("42", "Alex", "!ADDTASK Fold The Purple Towels") == "Added task 1: Fold The Purple Towels"
    service._last_seen.clear()
    assert "1. Fold The Purple Towels" in service.handle("42", "Alex", "!TaskList")


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
