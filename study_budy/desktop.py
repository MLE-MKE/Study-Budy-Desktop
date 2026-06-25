"""Native Windows desktop shell for Study Budy."""

from __future__ import annotations

import logging
import webbrowser
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .appearance_panel import AppearancePanel
from .connections_view import ConnectionsView
from .dashboard import DashboardView
from .icons import LOGO_PATH, icon
from .overlay_preview import OverlayPreview
from .paths import prepare_user_data_dir
from .preview import seed_preview_data
from .server import OverlayServer, OverlayServerError, choose_available_port
from .sidebar import Sidebar
from .storage import TaskRepository, ValidationError
from .task_window import TaskWindow
from .theme import Theme, app_stylesheet

LOG = logging.getLogger(__name__)


class StudyBudyWindow(QMainWindow):
    def __init__(self, repository: TaskRepository, overlay_server: OverlayServer) -> None:
        super().__init__()
        self.repository = repository
        self.overlay_server = overlay_server
        self.settings = QSettings("Hotkey LLC", "Study Budy")
        self.task_window: TaskWindow | None = None
        self.setWindowTitle("Study Budy Desktop")
        self.setWindowIcon(QIcon(str(LOGO_PATH)))
        self.setMinimumSize(Theme.MIN_WINDOW_WIDTH, Theme.MIN_WINDOW_HEIGHT)
        self.resize(Theme.DEFAULT_WINDOW_WIDTH, Theme.DEFAULT_WINDOW_HEIGHT)
        if geometry := self.settings.value("window/geometry", b""):
            self.restoreGeometry(geometry)

        self._build_menu()
        self._build_shell()
        self.refresh_all()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("Start task system", self.start_overlay)
        file_menu.addAction("Stop task system", self.stop_overlay)
        file_menu.addSeparator()
        file_menu.addAction("Export tasks", self.export_tasks)
        file_menu.addAction("Import tasks", self.import_tasks)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        view_menu = self.menuBar().addMenu("&View")
        for index, name in enumerate(("Dashboard", "Tasks", "Connections", "Appearance", "Help")):
            view_menu.addAction(name, self.open_task_window if name == "Tasks" else lambda checked=False, page=index: self.go_to_page(page))
        view_menu.addAction("Refresh overlay", self.restart_overlay)
        view_menu.addAction("Reset window layout", self.reset_window)

        settings_menu = self.menuBar().addMenu("&Settings")
        settings_menu.addAction("General settings", lambda: self.go_to_page(0))
        settings_menu.addAction("Twitch settings", lambda: self.go_to_page(2))
        settings_menu.addAction("OBS and Streamlabs settings", lambda: self.go_to_page(4))
        settings_menu.addAction("Storage settings", self.open_data_folder)
        settings_menu.addAction("Appearance settings", lambda: self.go_to_page(3))

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction("Setup instructions", lambda: self.go_to_page(4))
        help_menu.addAction("OBS setup instructions", lambda: self.go_to_page(4))
        help_menu.addAction("Streamlabs setup instructions", lambda: self.go_to_page(4))
        help_menu.addAction("Twitch command instructions", lambda: self.go_to_page(4))
        help_menu.addAction("Contact support", lambda: QDesktopServices.openUrl(QUrl("mailto:hotkeyllc@outlook.com?subject=Study%20Budy%20Support%20Request")))
        help_menu.addAction("Open logs folder", self.open_logs_folder)
        help_menu.addAction("About Study Budy", self.about_study_budy)

    def _build_shell(self) -> None:
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.sidebar = Sidebar()
        self.sidebar.navigate.connect(self.handle_sidebar_navigation)
        self.pages = QStackedWidget()
        layout.addWidget(self.sidebar)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(central)

        callbacks = {
            "start": self.start_overlay,
            "stop": self.stop_overlay,
            "restart": self.restart_overlay,
            "copy_url": self.copy_overlay_url,
            "preview": self.open_preview,
            "task_window": self.open_task_window,
            "appearance": lambda: self.go_to_page(3),
            "help": lambda: self.go_to_page(4),
            "appearance_saved": self.appearance_saved,
        }
        self.dashboard = DashboardView(self.repository, self.overlay_server, callbacks)
        self.connections = ConnectionsView(self.repository, self.refresh_all)
        self.appearance_page = self._appearance_page()
        self.help_page = self._help_page()

        self.pages.addWidget(self.dashboard)
        self.pages.addWidget(self._tasks_page())
        self.pages.addWidget(self.connections)
        self.pages.addWidget(self.appearance_page)
        self.pages.addWidget(self.help_page)
        self.pages.currentChanged.connect(self.sidebar.set_active)

    def _tasks_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)
        title = QLabel("Tasks")
        title.setObjectName("H1")
        layout.addWidget(title)
        copy = QLabel(
            "Task management now opens in its own focused window so the dashboard stays clean. "
            "Use Twitch chat activity, stored task data, or streamer-created tasks to populate viewer records."
        )
        copy.setObjectName("Muted")
        copy.setWordWrap(True)
        layout.addWidget(copy)
        button = QPushButton("Open Task Window")
        button.setObjectName("PrimaryButton")
        button.setIcon(icon("window"))
        button.clicked.connect(self.open_task_window)
        layout.addWidget(button)
        layout.addStretch(1)
        return page

    def _appearance_page(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(Theme.SECTION_SPACING)
        left = QVBoxLayout()
        title = QLabel("Appearance")
        title.setObjectName("H1")
        left.addWidget(title)
        note = QLabel("Tune the Browser Source overlay and preview it with the same task data used by OBS and Streamlabs Desktop.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        left.addWidget(note)
        self.full_overlay_preview = OverlayPreview(self.repository)
        left.addWidget(self.full_overlay_preview, 1)
        root.addLayout(left, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(Theme.RIGHT_PANEL_WIDTH)
        self.full_appearance_panel = AppearancePanel(self.repository, self.appearance_saved)
        scroll.setWidget(self.full_appearance_panel)
        root.addWidget(scroll)
        return page

    def _help_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel("Help")
        title.setObjectName("H1")
        layout.addWidget(title)
        browser = QTextBrowser()
        browser.setHtml(
            """
            <h2>First-run setup</h2>
            <ol>
              <li>Open Connections and enable Preview Mode or prepare Twitch OAuth.</li>
              <li>Start the task system from Dashboard.</li>
              <li>Copy the Overlay URL.</li>
              <li>In OBS Studio, add a Browser Source and paste the URL.</li>
              <li>Use 1920 × 1080 at 30 FPS, then resize the overlay in your scene.</li>
              <li>Use Appearance to adjust colors, opacity, finished tasks, and layout mode.</li>
            </ol>
            <h2>Streamlabs Desktop</h2>
            <p>Add a Browser Source, paste the same Study Budy overlay URL, set the recommended dimensions, and position it in your scene.</p>
            <h2>Twitch commands</h2>
            <p><code>!task Read chapter 8</code><br><code>!tasks</code><br><code>!done 2</code><br><code>!undo 2</code><br><code>!cleardone</code></p>
            <h2>Privacy</h2>
            <p>Task data and settings are stored locally. The overlay server binds to localhost by default. Do not share local databases or logs if they include private stream notes.</p>
            """
        )
        layout.addWidget(browser, 1)
        return page

    def handle_sidebar_navigation(self, index: int) -> None:
        if index == 1:
            self.open_task_window()
        else:
            self.go_to_page(index)

    def go_to_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)

    def refresh_all(self) -> None:
        self.dashboard.refresh()
        self.connections.refresh()
        self.full_overlay_preview.refresh()
        self.full_appearance_panel.load()
        live = self.overlay_server.running
        self.sidebar.set_system_status("All Systems Operational" if live else "Task System Offline", live)

    def start_overlay(self) -> None:
        try:
            self.overlay_server.start()
        except OverlayServerError:
            try:
                self.overlay_server.port = choose_available_port(self.overlay_server.host, self.overlay_server.port + 1)
                self.repository.set_setting("overlay_port", self.overlay_server.port)
                self.overlay_server.start()
            except OverlayServerError as exc:
                return self.error(str(exc))
        self.repository.start_session()
        self.refresh_all()

    def stop_overlay(self) -> None:
        self.overlay_server.stop()
        self.repository.end_session()
        self.refresh_all()

    def restart_overlay(self) -> None:
        try:
            if self.overlay_server.running:
                self.overlay_server.restart()
            else:
                self.start_overlay()
                return
        except OverlayServerError as exc:
            return self.error(str(exc))
        self.refresh_all()

    def appearance_saved(self) -> None:
        if self.overlay_server.running:
            try:
                self.overlay_server.restart()
            except OverlayServerError as exc:
                return self.error(str(exc))
        self.refresh_all()

    def copy_overlay_url(self) -> None:
        QApplication.clipboard().setText(self.overlay_server.url)

    def open_preview(self) -> None:
        if not self.overlay_server.running:
            self.start_overlay()
        if self.overlay_server.running:
            webbrowser.open(self.overlay_server.url)

    def export_tasks(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export tasks", "study-budy-tasks.json", "JSON files (*.json)")
        if path:
            self.repository.export_json(path)

    def import_tasks(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import tasks", "", "JSON files (*.json)")
        if not path:
            return
        try:
            count = self.repository.import_json(path)
        except ValidationError as exc:
            return self.error(str(exc))
        self.refresh_all()
        QMessageBox.information(self, "Import complete", f"Imported {count} tasks.")

    def open_task_window(self) -> None:
        if self.task_window is None:
            self.task_window = TaskWindow(self.repository, self.refresh_all)
        self.task_window.refresh()
        self.task_window.show()
        self.task_window.raise_()
        self.task_window.activateWindow()

    def open_data_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(prepare_user_data_dir())))

    def open_logs_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(prepare_user_data_dir() / "logs")))

    def reset_window(self) -> None:
        self.resize(Theme.DEFAULT_WINDOW_WIDTH, Theme.DEFAULT_WINDOW_HEIGHT)
        self.move(60, 40)

    def error(self, message: str) -> None:
        QMessageBox.warning(self, "Study Budy", message)

    def about_study_budy(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("About Study Budy")
        box.setIconPixmap(QPixmap(str(LOGO_PATH)).scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        box.setText("Study Budy Desktop")
        box.setInformativeText("Version 1.2.0\nStreamer task control and OBS Browser Source overlay.")
        box.exec()

    def closeEvent(self, event) -> None:
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.overlay_server.stop()
        super().closeEvent(event)


def run_desktop(preview: bool = False) -> int:
    data_dir = prepare_user_data_dir()
    logging.basicConfig(filename=data_dir / "logs" / "study-budy.log", level=logging.INFO)
    repository = TaskRepository(data_dir / "study-budy.db")
    repository.initialize()
    repository.migrate_legacy_json(Path.cwd() / "data" / "tasks.json")
    if preview:
        seed_preview_data(repository)
    server = OverlayServer(repository, port=repository.get_setting("overlay_port", 5155))
    app = QApplication([])
    app.setApplicationName("Study Budy")
    app.setWindowIcon(QIcon(str(LOGO_PATH)))
    app.setStyleSheet(app_stylesheet())
    window = StudyBudyWindow(repository, server)
    window.show()
    return app.exec()
