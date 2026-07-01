from PySide6.QtWidgets import QApplication

from study_budy.storage import TaskRepository
from study_budy.task_window import TaskWindow


def qapp():
    return QApplication.instance() or QApplication([])


def repository(tmp_path):
    repo = TaskRepository(tmp_path / "task-window.db")
    repo.initialize()
    return repo


def test_task_window_action_buttons_are_not_clipped_and_completed_actions_are_below_tree(tmp_path):
    qapp()
    repo = repository(tmp_path)
    repo.add_task("Alex", "Read chapter")
    repo.add_task("Alex", "Finished task")
    finished = repo.list_tasks()[1]
    repo.set_task_complete(finished["id"], True)

    window = TaskWindow(repo)

    assert window.clear_finished_button.text() == "Delete Finished Tasks"
    assert window.archive_completed_button.text() == "Archive Completed Tasks"
    assert window.remove_viewer_button.text() == "Remove Viewer From List"
    assert not hasattr(window, "archive_button")
    assert not hasattr(window, "archive_selected")
    assert window.clear_finished_button.minimumWidth() >= 220
    assert window.archive_completed_button.minimumWidth() >= 220
    assert window.remove_viewer_button.minimumWidth() >= 220
    bottom_actions = window.layout().itemAt(window.layout().count() - 1).layout()
    assert window.layout().indexOf(window.tree) < window.layout().count() - 1
    assert bottom_actions.itemAt(0).widget() is window.clear_finished_button
    assert bottom_actions.itemAt(1).widget() is window.archive_completed_button

    window.close()
