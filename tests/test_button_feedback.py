import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from study_budy.button_feedback import CLICK_FEEDBACK_STYLESHEET, run_with_click_feedback
from study_budy.checkin_view import CheckInView
from study_budy.connections_view import BOT_METADATA_KEY, STREAMER_METADATA_KEY, ConnectionsView
from study_budy.dashboard import DashboardView
from study_budy.storage import TaskRepository
from study_budy.timer_view import TimerView


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def repository(tmp_path):
    repo = TaskRepository(tmp_path / "button-feedback.db")
    repo.initialize()
    return repo


class FakeOverlayServer:
    running = True
    url = "http://127.0.0.1:5155/overlay"
    timer_url = "http://127.0.0.1:5155/timer"
    checkin_url = "http://127.0.0.1:5155/checkin"


def find_button(widget, text):
    matches = [button for button in widget.findChildren(QPushButton) if button.text() == text]
    assert matches, f"Could not find button with text {text!r}"
    return matches[0]


def dashboard_callbacks():
    return {
        "appearance": lambda: None,
        "help": lambda: None,
        "copy_url": lambda: QApplication.clipboard().setText(FakeOverlayServer.url),
        "preview": lambda: None,
        "restart": lambda: None,
        "start": lambda: None,
        "stop": lambda: None,
        "task_window": lambda: None,
        "appearance_saved": lambda: None,
    }


def overlay_callbacks():
    return {"start": lambda: None, "stop": lambda: None, "restart": lambda: None}


def test_click_feedback_runs_action_and_restores_original_style(qapp):
    button = QPushButton("Copy URL")
    button.setStyleSheet("background: #123456; color: white;")
    calls = []

    run_with_click_feedback(button, lambda: calls.append("copied"), delay_ms=25)

    assert calls == ["copied"]
    assert button.styleSheet() == CLICK_FEEDBACK_STYLESHEET
    QTest.qWait(40)
    assert button.styleSheet() == "background: #123456; color: white;"


def test_click_feedback_ignores_disabled_buttons(qapp):
    button = QPushButton("Copy URL")
    button.setEnabled(False)
    calls = []

    run_with_click_feedback(button, lambda: calls.append("copied"), delay_ms=25)

    assert calls == []
    assert button.styleSheet() == ""


def test_click_feedback_does_not_overwrite_newer_loading_style(qapp):
    button = QPushButton("Reconnect Streamer Account")

    def action():
        button.setText("Connecting...")
        button.setStyleSheet("background: #111111; color: white;")

    run_with_click_feedback(button, action, delay_ms=25)
    QTest.qWait(40)

    assert button.text() == "Connecting..."
    assert button.styleSheet() == "background: #111111; color: white;"


def test_dashboard_copy_url_keeps_action_and_click_feedback(qapp, repository):
    view = DashboardView(repository, FakeOverlayServer(), dashboard_callbacks())
    button = find_button(view, "Copy URL")

    button.click()

    assert QApplication.clipboard().text() == FakeOverlayServer.url
    assert button.styleSheet() == CLICK_FEEDBACK_STYLESHEET
    QTest.qWait(450)
    assert button.styleSheet() == ""


def test_timer_and_checkin_copy_url_buttons_keep_correct_actions(qapp, repository):
    timer = TimerView(repository, FakeOverlayServer(), overlay_callbacks())
    checkin = CheckInView(repository, FakeOverlayServer(), overlay_callbacks())

    timer_button = find_button(timer, "Copy URL")
    checkin_button = find_button(checkin, "Copy URL")

    timer_button.click()
    assert QApplication.clipboard().text() == FakeOverlayServer.timer_url
    assert timer_button.styleSheet() == CLICK_FEEDBACK_STYLESHEET
    QTest.qWait(450)
    assert timer_button.styleSheet() == ""

    checkin_button.click()
    assert QApplication.clipboard().text() == FakeOverlayServer.checkin_url
    assert checkin_button.styleSheet() == CLICK_FEEDBACK_STYLESHEET
    QTest.qWait(450)
    assert checkin_button.styleSheet() == ""


def test_reconnect_account_buttons_keep_actions_and_feedback(qapp, repository):
    repository.set_setting(STREAMER_METADATA_KEY, {"login": "streamer", "display_name": "Streamer", "user_id": "1"})
    repository.set_setting(BOT_METADATA_KEY, {"login": "bot", "display_name": "Bot", "user_id": "2"})
    view = ConnectionsView(repository, lambda: None)
    calls = []
    view.connect_account = lambda role: calls.append(role)
    view.refresh()

    streamer_button = find_button(view, "Reconnect Streamer Account")
    bot_button = find_button(view, "Reconnect Bot Account")

    streamer_button.click()
    bot_button.click()

    assert calls == ["streamer", "bot"]
    assert streamer_button.styleSheet() == CLICK_FEEDBACK_STYLESHEET
    assert bot_button.styleSheet() == CLICK_FEEDBACK_STYLESHEET
    QTest.qWait(450)
    assert streamer_button.styleSheet() == ""
    assert bot_button.styleSheet() == ""
