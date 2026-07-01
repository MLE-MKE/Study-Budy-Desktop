import time

import pytest
from PySide6.QtWidgets import QApplication

from study_budy.dashboard import DashboardView
from study_budy.overlay_clients import (
    CHECKIN_OVERLAY_CLIENT,
    TIMER_OVERLAY_CLIENT,
    clear_overlay_heartbeats,
    is_overlay_client_connected,
    record_overlay_heartbeat,
)
from study_budy.overlay_service import create_overlay_app
from study_budy.storage import TaskRepository


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def repository(tmp_path):
    repo = TaskRepository(tmp_path / "study-budy.db")
    repo.initialize()
    clear_overlay_heartbeats()
    return repo


class FakeOverlayServer:
    host = "127.0.0.1"
    port = 5155
    url = "http://127.0.0.1:5155/overlay"
    running = True


def callbacks():
    return {
        "appearance": lambda: None,
        "help": lambda: None,
        "copy_url": lambda: None,
        "preview": lambda: None,
        "restart": lambda: None,
        "start": lambda: None,
        "stop": lambda: None,
        "task_window": lambda: None,
        "appearance_saved": lambda: None,
    }


def test_overlay_heartbeat_tracks_real_timer_and_checkin_clients(repository):
    assert not is_overlay_client_connected(TIMER_OVERLAY_CLIENT)
    assert not is_overlay_client_connected(CHECKIN_OVERLAY_CLIENT)

    client = create_overlay_app(repository).test_client()
    assert client.post("/api/overlay-clients/timer/heartbeat").get_json()["client"] == TIMER_OVERLAY_CLIENT
    assert client.post("/api/overlay-clients/checkin/heartbeat").get_json()["client"] == CHECKIN_OVERLAY_CLIENT

    assert is_overlay_client_connected(TIMER_OVERLAY_CLIENT)
    assert is_overlay_client_connected(CHECKIN_OVERLAY_CLIENT)


def test_overlay_heartbeat_expires_disconnected_clients(repository):
    record_overlay_heartbeat(TIMER_OVERLAY_CLIENT)
    time.sleep(0.02)
    assert not is_overlay_client_connected(TIMER_OVERLAY_CLIENT, timeout_seconds=0.001)


def test_dashboard_replaces_twitch_obs_cards_with_overlay_status(qapp, repository):
    view = DashboardView(repository, FakeOverlayServer(), callbacks())
    view.refresh_overlay_connection_status()

    titles = [card.title_label.text() for card in view.status_cards]
    assert "Twitch" not in titles
    assert "OBS" not in titles
    assert "Timer Overlay" in titles
    assert "Check-In Overlay" in titles
    assert view.timer_card.value_label.text() == "Timer Disconnected"
    assert view.checkin_card.value_label.text() == "Check-In Disconnected (Beta)"

    record_overlay_heartbeat(TIMER_OVERLAY_CLIENT)
    record_overlay_heartbeat(CHECKIN_OVERLAY_CLIENT)
    view.refresh_overlay_connection_status()

    assert view.timer_card.value_label.text() == "Timer Connected"
    assert view.checkin_card.value_label.text() == "Check-In Connected (Beta)"
