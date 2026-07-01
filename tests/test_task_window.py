from PySide6.QtWidgets import QApplication, QHBoxLayout

from study_budy.storage import TaskRepository
from study_budy.task_window import TaskWindow


def qapp():
    return QApplication.instance() or QApplication([])


def repository(tmp_path):
    repo = TaskRepository(tmp_path / "task-window.db")
    repo.initialize()
    return repo


def visible_task_rows(window):
    rows = []
    for parent_index in range(window.tree.topLevelItemCount()):
        parent = window.tree.topLevelItem(parent_index)
        for child_index in range(parent.childCount()):
            child = parent.child(child_index)
            rows.append((child.text(0), child.text(1)))
    return rows


def test_task_window_action_buttons_are_not_clipped_and_completed_actions_are_below_tree(tmp_path):
    qapp()
    repo = repository(tmp_path)
    repo.add_task("Alex", "Read chapter")
    repo.add_task("Alex", "Finished task")
    finished = repo.list_tasks()[1]
    repo.set_task_complete(finished["id"], True)

    window = TaskWindow(repo)

    assert window.clear_finished_button.text() == "Delete Completed Tasks"
    assert window.archive_completed_button.text() == "Archive Completed Tasks"
    assert window.remove_viewer_button.text() == "Remove Viewer From List"
    assert not hasattr(window, "archive_button")
    assert not hasattr(window, "archive_selected")
    assert window.clear_finished_button.minimumWidth() >= 220
    assert window.archive_completed_button.minimumWidth() >= 220
    assert window.remove_viewer_button.minimumWidth() >= 220
    bottom_actions = window.layout().itemAt(window.layout().count() - 1).layout()
    assert isinstance(bottom_actions, QHBoxLayout)
    assert window.layout().indexOf(window.tree) < window.layout().count() - 1
    assert bottom_actions.itemAt(0).widget() is window.clear_finished_button
    assert bottom_actions.itemAt(1).widget() is window.archive_completed_button

    window.close()


def test_task_filter_dropdown_contains_archived_in_order(tmp_path):
    qapp()
    repo = repository(tmp_path)
    window = TaskWindow(repo)

    options = [window.filter.itemText(index) for index in range(window.filter.count())]

    assert options == ["All", "Active", "Completed", "Archived"]

    window.close()


def test_task_filters_include_active_completed_and_archived_tasks(tmp_path):
    qapp()
    repo = repository(tmp_path)
    active = repo.add_task("Alex", "Active task")
    completed = repo.add_task("Alex", "Completed task")
    archived = repo.add_task("Alex", "Archived task")
    repo.set_task_complete(completed["id"], True)
    repo.set_task_complete(archived["id"], True)
    repo.archive_task(archived["id"])
    window = TaskWindow(repo)

    window.filter.setCurrentText("All")
    assert visible_task_rows(window) == [
        ("Active task", "Active"),
        ("Completed task", "Completed"),
        ("Archived task", "Archived"),
    ]
    assert window.filter_summary.text() == "3 All Tasks"

    window.filter.setCurrentText("Active")
    assert visible_task_rows(window) == [("Active task", "Active")]
    assert window.filter_summary.text() == "1 Active Task"

    window.filter.setCurrentText("Completed")
    assert visible_task_rows(window) == [("Completed task", "Completed")]
    assert window.filter_summary.text() == "1 Completed Task"

    window.filter.setCurrentText("Archived")
    assert visible_task_rows(window) == [("Archived task", "Archived")]
    assert window.filter_summary.text() == "1 Archived Task"

    window.close()


def test_archive_completed_moves_task_from_completed_to_archived_filter(tmp_path):
    qapp()
    repo = repository(tmp_path)
    finished = repo.add_task("Alex", "Finished task")
    repo.set_task_complete(finished["id"], True)
    window = TaskWindow(repo)

    window.filter.setCurrentText("Completed")
    assert visible_task_rows(window) == [("Finished task", "Completed")]

    window.archive_completed()
    assert visible_task_rows(window) == []
    assert window.filter.currentText() == "Completed"

    window.filter.setCurrentText("Archived")
    assert visible_task_rows(window) == [("Finished task", "Archived")]

    window.close()


def test_empty_archived_filter_shows_empty_state_without_error(tmp_path):
    qapp()
    repo = repository(tmp_path)
    repo.add_task("Alex", "Active task")
    window = TaskWindow(repo)

    window.filter.setCurrentText("Archived")

    assert visible_task_rows(window) == []
    assert not window.empty_state.isHidden()
    assert window.empty_state.text() == "No archived tasks found."
    assert window.filter_summary.text() == "0 Archived Tasks"

    window.close()
