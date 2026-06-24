"""Native Windows desktop shell for Study Budy."""

from __future__ import annotations

import logging
import webbrowser
from html import escape
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QSpinBox, QStackedWidget, QTextBrowser, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from .overlay_service import DEFAULT_APPEARANCE
from .paths import prepare_user_data_dir
from .server import OverlayServer, OverlayServerError
from .storage import TaskRepository, ValidationError

LOG = logging.getLogger(__name__)


class StudyBudyWindow(QMainWindow):
    def __init__(self, repository: TaskRepository, overlay_server: OverlayServer) -> None:
        super().__init__()
        self.repository, self.overlay_server = repository, overlay_server
        self.settings = QSettings("Hotkey LLC", "Study Budy")
        self.setWindowTitle("Study Budy Desktop")
        self.setWindowIcon(QIcon(str(Path(__file__).with_name("assets") / "study-budy-icon.svg")))
        self.setMinimumSize(980, 640)
        self.resize(self.settings.value("window/size", self.size()))
        self._build_menu()
        self._build_pages()
        self.restoreGeometry(self.settings.value("window/geometry", b""))
        self.refresh_all()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("Start task system", self.start_overlay)
        file_menu.addAction("Stop task system", self.stop_overlay)
        file_menu.addSeparator()
        file_menu.addAction("Export tasks…", self.export_tasks)
        file_menu.addAction("Import tasks…", self.import_tasks)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        view_menu = self.menuBar().addMenu("&View")
        for index, name in enumerate(("Dashboard", "Tasks", "Connections", "Appearance", "Help")):
            view_menu.addAction(name, lambda checked=False, page=index: self.pages.setCurrentIndex(page))
        view_menu.addAction("Refresh overlay", self.restart_overlay)
        view_menu.addAction("Reset window layout", self.reset_window)
        settings_menu = self.menuBar().addMenu("&Settings")
        settings_menu.addAction("General settings", lambda: self.pages.setCurrentIndex(0))
        settings_menu.addAction("Twitch settings", lambda: self.pages.setCurrentIndex(2))
        settings_menu.addAction("OBS and Streamlabs settings", lambda: self.pages.setCurrentIndex(2))
        settings_menu.addAction("Storage settings", self.open_data_folder)
        settings_menu.addAction("Appearance settings", lambda: self.pages.setCurrentIndex(3))
        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction("Setup instructions", lambda: self.pages.setCurrentIndex(4))
        help_menu.addAction("OBS setup instructions", lambda: self.pages.setCurrentIndex(4))
        help_menu.addAction("Streamlabs setup instructions", lambda: self.pages.setCurrentIndex(4))
        help_menu.addAction("Twitch command instructions", lambda: self.pages.setCurrentIndex(4))
        help_menu.addAction("Contact support", lambda: QDesktopServices.openUrl(QUrl("mailto:hotkeyllc@outlook.com?subject=Study%20Budy%20Support%20Request")))
        help_menu.addAction("Open logs folder", self.open_logs_folder)
        help_menu.addAction("About Study Budy", lambda: QMessageBox.about(self, "About Study Budy", "Study Budy Desktop\nVersion 0.1.0"))

    def _build_pages(self) -> None:
        central = QWidget(); layout = QHBoxLayout(central); layout.setContentsMargins(0, 0, 0, 0)
        rail = QFrame(); rail.setFixedWidth(180); rail_layout = QVBoxLayout(rail)
        rail_layout.addWidget(QLabel("<h2>Study Budy</h2><p>STREAM TASK CONTROL</p>"))
        self.pages = QStackedWidget()
        for index, name in enumerate(("Dashboard", "Tasks", "Connections", "Appearance", "Help")):
            button = QPushButton(name); button.clicked.connect(lambda checked=False, page=index: self.pages.setCurrentIndex(page)); rail_layout.addWidget(button)
        rail_layout.addStretch(1)
        self.status_label = QLabel("Offline")
        rail_layout.addWidget(self.status_label)
        layout.addWidget(rail); layout.addWidget(self.pages, 1); self.setCentralWidget(central)
        self.pages.addWidget(self._dashboard_page()); self.pages.addWidget(self._tasks_page())
        self.pages.addWidget(self._connections_page()); self.pages.addWidget(self._appearance_page()); self.pages.addWidget(self._help_page())

    def _dashboard_page(self) -> QWidget:
        page = QWidget(); outer = QHBoxLayout(page); main = QVBoxLayout(); side = QVBoxLayout(); outer.addLayout(main, 3); outer.addLayout(side, 1)
        heading = QHBoxLayout(); heading.addWidget(QLabel("<h1>◴  Dashboard</h1>")); heading.addStretch(1); self.dashboard_status = QLabel(); self.dashboard_status.setObjectName("liveBadge"); heading.addWidget(self.dashboard_status); main.addLayout(heading)
        cards = QGridLayout(); self.twitch_card = self._status_card("▣  Twitch"); self.obs_card = self._status_card("◉  OBS"); self.overlay_card = self._status_card("▤  Overlay Server"); self.session_card = self._status_card("⌁  Session Status")
        for index, card in enumerate((self.twitch_card, self.obs_card, self.overlay_card, self.session_card)): cards.addWidget(card, 0, index)
        main.addLayout(cards)
        url_card = QFrame(); url_card.setObjectName("card"); url_box = QVBoxLayout(url_card); url_box.addWidget(QLabel("⌁  Overlay URL")); url_line = QHBoxLayout(); self.overlay_url = QLineEdit(); self.overlay_url.setReadOnly(True); url_line.addWidget(self.overlay_url, 1)
        for title, callback in (("Copy URL", self.copy_overlay_url), ("Preview Overlay", self.open_preview), ("Refresh", self.restart_overlay)):
            button = QPushButton(title); button.clicked.connect(callback); url_line.addWidget(button)
        url_box.addLayout(url_line); main.addWidget(url_card)
        lower = QHBoxLayout(); setup_card = QFrame(); setup_card.setObjectName("card"); setup = QVBoxLayout(setup_card); setup.addWidget(QLabel("<h3>▣  OBS Setup (Quick Steps)</h3>")); setup.addWidget(QLabel("①  Add Browser Source\n②  Paste overlay URL\n③  Set 1920 × 1080, 30 FPS\n④  Position on scene")); lower.addWidget(setup_card)
        control_card = QFrame(); control_card.setObjectName("card"); controls = QVBoxLayout(control_card); controls.addWidget(QLabel("<h3>Controls</h3>")); actions = QHBoxLayout()
        for title, callback in (("Copy Overlay URL", self.copy_overlay_url), ("Open Overlay Preview", self.open_preview), ("Start", self.start_overlay), ("Stop", self.stop_overlay), ("Restart", self.restart_overlay)):
            if title.startswith("Copy") or title.startswith("Open"): continue
            button = QPushButton(title); button.clicked.connect(callback); actions.addWidget(button)
        controls.addLayout(actions); lower.addWidget(control_card); main.addLayout(lower)
        self.session_stats = QLabel(); self.session_stats.setObjectName("stats"); main.addWidget(self.session_stats); main.addStretch(1)
        preview_card = QFrame(); preview_card.setObjectName("card"); preview_box = QVBoxLayout(preview_card); preview_box.addWidget(QLabel("<h3>◉  Overlay Preview</h3>")); self.overlay_preview = QTextBrowser(); self.overlay_preview.setMinimumWidth(290); self.overlay_preview.setMinimumHeight(320); preview_box.addWidget(self.overlay_preview); side.addWidget(preview_card); side.addWidget(QLabel("<h3>◉  Appearance</h3><p>Use the Appearance section for fonts, colors, opacity, layout, and images.</p>")); side.addStretch(1)
        return page

    def _status_card(self, title: str) -> QFrame:
        card = QFrame(); card.setObjectName("card"); layout = QVBoxLayout(card); label = QLabel(title); value = QLabel("Disconnected"); value.setObjectName("cardValue"); layout.addWidget(label); layout.addWidget(value); card.value_label = value; return card

    def _tasks_page(self) -> QWidget:
        page = QWidget(); box = QVBoxLayout(page); box.addWidget(QLabel("<h1>Tasks</h1>"))
        controls = QHBoxLayout(); self.task_search = QLineEdit(); self.task_search.setPlaceholderText("Search tasks"); self.task_search.textChanged.connect(self.refresh_tasks); controls.addWidget(self.task_search)
        for title, callback in (("Add task", self.add_task), ("Edit", self.edit_task), ("Complete / reopen", self.toggle_task), ("Delete", self.delete_task), ("Move up", lambda: self.move_task(-1)), ("Move down", lambda: self.move_task(1)), ("Remove participant", self.remove_participant)):
            button = QPushButton(title); button.clicked.connect(callback); controls.addWidget(button)
        box.addLayout(controls); self.task_tree = QTreeWidget(); self.task_tree.setHeaderLabels(["Participant / task", "Status", "Created"]); self.task_tree.setColumnWidth(0, 460); box.addWidget(self.task_tree); return page

    def _connections_page(self) -> QWidget:
        page = QWidget(); box = QVBoxLayout(page); box.addWidget(QLabel("<h1>Connections</h1>"))
        self.twitch_status = QLabel(); box.addWidget(self.twitch_status)
        setup = QPushButton("Configure Twitch channel"); setup.clicked.connect(self.configure_twitch); box.addWidget(setup)
        test = QPushButton("Add safe test viewer task"); test.clicked.connect(self.add_test_task); box.addWidget(test)
        box.addWidget(QLabel("OBS and Streamlabs Desktop work through the Browser Source URL. OBS WebSocket is optional and is not required for the overlay."))
        box.addStretch(1); return page

    def _appearance_page(self) -> QWidget:
        page = QWidget(); box = QVBoxLayout(page); box.addWidget(QLabel("<h1>Appearance</h1><p>Changes are saved and used by the live overlay.</p>"))
        form = QFormLayout(); self.layout_mode = QComboBox(); self.layout_mode.addItem("Cycle everyone", "cycle"); self.layout_mode.addItem("Streamer on top", "streamer_top")
        self.cycle_seconds = QSpinBox(); self.cycle_seconds.setRange(3, 300); self.cycle_seconds.setSuffix(" seconds")
        self.font_name = QLineEdit(); self.text_color = QLineEdit(); self.background_color = QLineEdit(); self.opacity = QSpinBox(); self.opacity.setRange(0, 100); self.opacity.setSuffix(" %")
        for label, field in (("Layout", self.layout_mode), ("Cycle duration", self.cycle_seconds), ("Font family", self.font_name), ("Text color", self.text_color), ("Background color", self.background_color), ("Background opacity", self.opacity)): form.addRow(label, field)
        box.addLayout(form); save = QPushButton("Save appearance and refresh overlay"); save.clicked.connect(self.save_appearance); box.addWidget(save); preview = QPushButton("Open live preview"); preview.clicked.connect(self.open_preview); box.addWidget(preview); box.addStretch(1); return page

    def _help_page(self) -> QWidget:
        page = QWidget(); box = QVBoxLayout(page); help_text = QTextBrowser(); help_text.setHtml("""
<h1>Study Budy setup</h1><ol><li>Configure your Twitch channel in Connections.</li><li>Start the task system on Dashboard.</li><li>Copy the Overlay URL.</li><li>In OBS Studio: choose a scene, click <b>+</b> under Sources, choose <b>Browser</b>, create a source, paste the URL, set 1920 × 1080 and 30 FPS, then position it.</li><li>In Streamlabs Desktop: add a Browser Source, paste the same URL, set 1920 × 1080, and position it.</li></ol><h2>Commands</h2><p><code>!addtask task one | task two</code><br><code>!tasklist</code><br><code>!done 2</code><br><code>!clear 2</code> or <code>!clear all</code></p><h2>Privacy and backups</h2><p>Tasks and settings live in your local Study Budy data folder. Use File → Export tasks for a readable backup. The Browser Source server is local-only by default.</p>"""); box.addWidget(help_text); return page

    def refresh_all(self) -> None:
        self.refresh_dashboard(); self.refresh_tasks(); self.load_appearance(); self.refresh_connections()

    def refresh_dashboard(self) -> None:
        status = "Live — overlay service running" if self.overlay_server.running else "Offline — overlay service stopped"
        self.status_label.setText(status); self.dashboard_status.setText(status); self.overlay_url.setText(self.overlay_server.url)
        participants = self.repository.task_snapshot(); incomplete = sum(not task["is_complete"] for person in participants for task in person["tasks"]); completed = sum(task["is_complete"] for person in participants for task in person["tasks"])
        self.session_stats.setText(f"Active participants: {len(participants)}   •   Incomplete tasks: {incomplete}   •   Completed tasks: {completed}")
        self.twitch_card.value_label.setText("Connected" if self.repository.get_setting("twitch_channel", "") else "Not configured")
        self.obs_card.value_label.setText("Browser Source ready")
        self.overlay_card.value_label.setText("Live" if self.overlay_server.running else "Offline")
        self.session_card.value_label.setText("Live" if self.overlay_server.running else "Offline")
        preview = "<h2>📚 STUDY BUDY</h2>"
        for person in participants[:3]:
            preview += f"<h3>{escape(person['display_name'])}</h3>" + "".join(f"<p>{'☑' if task['is_complete'] else '☐'} {escape(task['text'])}</p>" for task in person['tasks'][:4])
        self.overlay_preview.setHtml(preview or "<p>Waiting for tasks…</p>")

    def refresh_tasks(self) -> None:
        if not hasattr(self, "task_tree"): return
        query = self.task_search.text().casefold(); self.task_tree.clear()
        for person in self.repository.task_snapshot():
            matching = [task for task in person["tasks"] if not query or query in task["text"].casefold() or query in person["display_name"].casefold()]
            if not matching: continue
            parent = QTreeWidgetItem([person["display_name"], f"{person['incomplete_count'] or 0} active", ""]); parent.setData(0, Qt.UserRole, {"participant_id": person["id"]}); self.task_tree.addTopLevelItem(parent)
            for task in matching:
                child = QTreeWidgetItem([task["text"], "Complete" if task["is_complete"] else "Incomplete", task["created_at"][:10]]); child.setData(0, Qt.UserRole, {"task_id": task["id"], "complete": task["is_complete"]}); parent.addChild(child)
            parent.setExpanded(True)

    def selected_data(self) -> dict:
        item = self.task_tree.currentItem(); return item.data(0, Qt.UserRole) if item else {}

    def add_task(self) -> None:
        name, ok = QInputDialog.getText(self, "Participant", "Participant name:")
        if not ok: return
        text, ok = QInputDialog.getText(self, "Add task", "Task description:")
        if ok:
            try: self.repository.add_task(name, text, "streamer" if name.casefold() == "streamer" else "viewer")
            except ValidationError as exc: self.error(str(exc)); return
            self.refresh_all()

    def edit_task(self) -> None:
        data = self.selected_data()
        if "task_id" not in data: return self.error("Select a task to edit.")
        text, ok = QInputDialog.getText(self, "Edit task", "Task description:")
        if ok:
            try: self.repository.update_task(data["task_id"], text)
            except (ValidationError, KeyError) as exc: self.error(str(exc)); return
            self.refresh_all()

    def toggle_task(self) -> None:
        data = self.selected_data()
        if "task_id" not in data: return self.error("Select a task first.")
        self.repository.set_task_complete(data["task_id"], not data["complete"]); self.refresh_all()

    def delete_task(self) -> None:
        data = self.selected_data()
        if "task_id" not in data: return self.error("Select a task to delete.")
        if QMessageBox.question(self, "Delete task", "Delete this task permanently?") == QMessageBox.Yes: self.repository.delete_task(data["task_id"]); self.refresh_all()

    def move_task(self, direction: int) -> None:
        data = self.selected_data()
        if "task_id" not in data: return self.error("Select a task to move.")
        self.repository.reorder_task(data["task_id"], direction); self.refresh_all()

    def remove_participant(self) -> None:
        data = self.selected_data()
        if "participant_id" not in data: return self.error("Select a participant heading to remove them.")
        if QMessageBox.question(self, "Remove participant", "Hide this participant and preserve their stored tasks?") == QMessageBox.Yes: self.repository.remove_participant(data["participant_id"]); self.refresh_all()

    def start_overlay(self) -> None:
        try: self.overlay_server.start()
        except OverlayServerError as exc: return self.error(str(exc))
        self.refresh_dashboard()
    def stop_overlay(self) -> None: self.overlay_server.stop(); self.refresh_dashboard()
    def restart_overlay(self) -> None:
        try: self.overlay_server.restart()
        except OverlayServerError as exc: return self.error(str(exc))
        self.refresh_dashboard()
    def copy_overlay_url(self) -> None: QApplication.clipboard().setText(self.overlay_server.url)
    def open_preview(self) -> None:
        if not self.overlay_server.running: self.start_overlay()
        if self.overlay_server.running: webbrowser.open(self.overlay_server.url)
    def configure_twitch(self) -> None:
        channel, ok = QInputDialog.getText(self, "Twitch channel", "Twitch channel name:", text=self.repository.get_setting("twitch_channel", ""))
        if ok and channel.strip(): self.repository.set_setting("twitch_channel", channel.strip().lstrip("#")); self.refresh_connections()
    def refresh_connections(self) -> None:
        channel = self.repository.get_setting("twitch_channel", "")
        self.twitch_status.setText(f"Twitch channel: {channel}" if channel else "Twitch: Not configured. Configure a channel to prepare chat connection.")
    def load_appearance(self) -> None:
        appearance = {**DEFAULT_APPEARANCE, **self.repository.get_setting("appearance", {})}; self.layout_mode.setCurrentIndex(self.layout_mode.findData(appearance["layout_mode"])); self.cycle_seconds.setValue(appearance["cycle_seconds"]); self.font_name.setText(appearance["font_family"]); self.text_color.setText(appearance["text_color"]); self.background_color.setText(appearance["background_color"]); self.opacity.setValue(appearance["background_opacity"])
    def save_appearance(self) -> None:
        current = {**DEFAULT_APPEARANCE, **self.repository.get_setting("appearance", {})}; current.update({"layout_mode": self.layout_mode.currentData(), "cycle_seconds": self.cycle_seconds.value(), "font_family": self.font_name.text().strip() or "Segoe UI", "text_color": self.text_color.text().strip() or "#ffffff", "background_color": self.background_color.text().strip() or "#000000", "background_opacity": self.opacity.value()}); self.repository.set_setting("appearance", current); self.restart_overlay() if self.overlay_server.running else self.refresh_dashboard()
    def export_tasks(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export tasks", "study-budy-tasks.json", "JSON files (*.json)")
        if path: self.repository.export_json(path)
    def import_tasks(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import tasks", "", "JSON files (*.json)")
        if not path: return
        try: count = self.repository.import_json(path)
        except ValidationError as exc: return self.error(str(exc))
        self.refresh_all(); QMessageBox.information(self, "Import complete", f"Imported {count} tasks.")
    def add_test_task(self) -> None:
        self.repository.add_task("Test viewer", "Try the Study Budy overlay"); self.refresh_all()
    def open_data_folder(self) -> None: QDesktopServices.openUrl(QUrl.fromLocalFile(str(prepare_user_data_dir())))
    def open_logs_folder(self) -> None: QDesktopServices.openUrl(QUrl.fromLocalFile(str(prepare_user_data_dir() / "logs")))
    def reset_window(self) -> None: self.resize(1180, 760); self.move(80, 80)
    def error(self, message: str) -> None: QMessageBox.warning(self, "Study Budy", message)
    def closeEvent(self, event) -> None:
        self.settings.setValue("window/geometry", self.saveGeometry()); self.overlay_server.stop(); super().closeEvent(event)


def run_desktop() -> int:
    data_dir = prepare_user_data_dir(); logging.basicConfig(filename=data_dir / "logs" / "study-budy.log", level=logging.INFO)
    repository = TaskRepository(data_dir / "study-budy.db"); repository.initialize()
    repository.migrate_legacy_json(Path.cwd() / "data" / "tasks.json")
    server = OverlayServer(repository, port=repository.get_setting("overlay_port", 5155))
    app = QApplication([]); app.setApplicationName("Study Budy")
    app.setStyleSheet("""
        QMainWindow, QWidget { background: #11151a; color: #f1eff6; font-family: 'Segoe UI'; font-size: 14px; }
        QMenuBar { background: #15191f; border-bottom: 1px solid #2d333d; padding: 4px; }
        QMenuBar::item { padding: 6px 12px; } QMenuBar::item:selected, QMenu { background: #252035; }
        QFrame#card { background: #191e25; border: 1px solid #303742; border-radius: 9px; padding: 8px; }
        QLabel#cardValue { color: #21d35d; font-weight: 700; font-size: 15px; }
        QLabel#liveBadge { background: #078a28; border: 1px solid #21d35d; border-radius: 8px; padding: 8px 15px; font-weight: 700; }
        QLabel#stats { background: #191e25; border: 1px solid #6734c5; border-radius: 9px; padding: 22px; font-size: 16px; }
        QPushButton { background: #1b2028; border: 1px solid #3b4350; border-radius: 7px; padding: 10px 14px; }
        QPushButton:hover { border-color: #9b5cff; background: #292034; } QPushButton:pressed { background: #5920af; }
        QLineEdit, QComboBox, QSpinBox, QTreeWidget, QTextBrowser { background: #12161c; border: 1px solid #353d48; border-radius: 6px; padding: 7px; selection-background-color: #6d2ed0; }
        QTreeWidget::item:selected { background: #5423a7; } QScrollBar:vertical { background: #11151a; width: 10px; }
    """)
    window = StudyBudyWindow(repository, server); window.show(); return app.exec()
