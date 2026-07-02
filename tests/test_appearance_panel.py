import pytest
from PySide6.QtWidgets import QApplication

from study_budy.appearance_panel import AppearancePanel
from study_budy.storage import TaskRepository


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def repository(tmp_path):
    repo = TaskRepository(tmp_path / "appearance.db")
    repo.initialize()
    return repo


def test_layout_mode_options_are_cycle_everyone_and_list(qapp, tmp_path):
    panel = AppearancePanel(repository(tmp_path), lambda: None)

    options = [panel.layout_mode.itemText(index) for index in range(panel.layout_mode.count())]

    assert options == ["Cycle Everyone", "List"]
    assert "Streamer on Top" not in options
    assert "Streamer on top" not in options


def test_old_streamer_on_top_setting_loads_as_list_and_saves_new_value(qapp, tmp_path):
    repo = repository(tmp_path)
    repo.set_setting("appearance", {"layout_mode": "streamer_top"})
    panel = AppearancePanel(repo, lambda: None)

    assert panel.layout_mode.currentText() == "List"

    panel.save()
    assert repo.get_setting("appearance")["layout_mode"] == "list"
