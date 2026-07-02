import pytest
from PySide6.QtWidgets import QApplication, QTextBrowser

from study_budy.appearance_panel import AppearancePanel
from study_budy.dashboard import DashboardView
from study_budy.desktop import StudyBudyWindow
from study_budy.server import OverlayServer
from study_budy.storage import TaskRepository
from study_budy.theme import APPLICATION_THEME_KEY, THEMES, Theme, app_stylesheet, normalize_application_theme


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def repository(tmp_path):
    repo = TaskRepository(tmp_path / "theme.db")
    repo.initialize()
    return repo


class FakeOverlayServer:
    running = False
    url = "http://127.0.0.1:5155/overlay"


def dashboard_callbacks():
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
        "theme_changed": lambda _theme: None,
    }


def test_settings_button_remains_between_live_and_help(qapp, repository):
    view = DashboardView(repository, FakeOverlayServer(), dashboard_callbacks())

    ordered_widgets = [view.header_grid.itemAt(index).widget() for index in range(view.header_grid.count())]
    assert ordered_widgets.index(view.live_badge) < ordered_widgets.index(view.settings_button)
    assert ordered_widgets.index(view.settings_button) < ordered_widgets.index(view.help_button)


def test_application_theme_selector_contains_exact_options(qapp, repository):
    panel = AppearancePanel(repository, lambda: None)

    options = [panel.application_theme.itemText(index) for index in range(panel.application_theme.count())]

    assert options == ["Dark", "Light", "Pastel Pink"]


@pytest.mark.parametrize(
    ("theme_name", "expected_background", "expected_text"),
    [
        ("Dark", "#0f1318", "#f6f3fb"),
        ("Light", "#f4f6fb", "#1d2430"),
        ("Pastel Pink", "#fff1f6", "#2b1d27"),
    ],
)
def test_theme_palettes_apply_readable_colors(theme_name, expected_background, expected_text):
    Theme.apply(theme_name)
    stylesheet = app_stylesheet()

    assert Theme.BACKGROUND == expected_background
    assert Theme.TEXT == expected_text
    assert Theme.GREEN != Theme.RED
    assert "QPushButton" in stylesheet
    assert expected_background in stylesheet
    assert expected_text in stylesheet


def test_invalid_saved_theme_falls_back_to_dark():
    assert normalize_application_theme("Cyber Pickle") == "Dark"


def test_theme_selection_is_saved_and_callback_updates_open_app(qapp, repository):
    repository.set_setting(APPLICATION_THEME_KEY, "Dark")
    applied = []
    panel = AppearancePanel(repository, lambda: None, lambda theme: applied.append(theme))

    panel.application_theme.setCurrentText("Pastel Pink")

    assert repository.get_setting(APPLICATION_THEME_KEY) == "Pastel Pink"
    assert applied == ["Pastel Pink"]


def test_window_applies_saved_theme_and_updates_stylesheet(qapp, repository):
    repository.set_setting(APPLICATION_THEME_KEY, "Light")
    window = StudyBudyWindow(repository, OverlayServer(repository))

    window.apply_application_theme()

    assert repository.get_setting(APPLICATION_THEME_KEY) == "Light"
    assert Theme.CURRENT == "Light"
    assert THEMES["Light"]["BACKGROUND"] in qapp.styleSheet()

    window.apply_application_theme("Pastel Pink")
    assert repository.get_setting(APPLICATION_THEME_KEY) == "Pastel Pink"
    assert THEMES["Pastel Pink"]["BACKGROUND"] in qapp.styleSheet()
    window.close()


def test_help_section_contains_professional_links_and_opens_urls(qapp, repository, monkeypatch):
    window = StudyBudyWindow(repository, OverlayServer(repository))
    opened = []
    monkeypatch.setattr("study_budy.desktop.QDesktopServices.openUrl", lambda url: opened.append(url.toString()) or True)

    browser_text = window.help_page.findChildren(QTextBrowser)[0].toPlainText()
    assert "Study Budy Help" in browser_text
    assert "For step-by-step tutorials, setup instructions, and feature demonstrations" in browser_text
    assert "KillerQueen55 YouTube channel" in browser_text
    assert "follow Killer Queen on Twitch at killer_queen55" in browser_text

    window.open_youtube_tutorials()
    window.open_twitch_channel()

    assert opened == ["https://www.youtube.com/@KillerQueen55", "https://www.twitch.tv/killer_queen55"]
    window.close()


def test_help_link_error_is_handled_without_crash(qapp, repository, monkeypatch):
    window = StudyBudyWindow(repository, OverlayServer(repository))
    messages = []
    monkeypatch.setattr("study_budy.desktop.QDesktopServices.openUrl", lambda _url: False)
    window.error = messages.append

    window.open_youtube_tutorials()

    assert messages == ["Study Budy could not open that link in your default browser."]
    window.close()
