"""Dedicated viewer and streamer task window with active/finished controls."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .icons import icon
from .storage import TaskRepository
from .theme import Theme


class TaskWindow(QWidget):
    def __init__(self, repository: TaskRepository, on_change=None) -> None:
        super().__init__()
        self.repository = repository
        self.on_change = on_change or (lambda: None)
        self.settings = QSettings("Hotkey LLC", "Study Budy")
        self._loading = False
        self.setWindowTitle("Study Budy — Viewer Task Window")
        self.setWindowIcon(icon("window"))
        self.setMinimumSize(760, 560)
        if geometry := self.settings.value("task_window/geometry", b""):
            self.restoreGeometry(geometry)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(Theme.SECTION_SPACING)
        title = QLabel("Viewer Task Window")
        title.setObjectName("H1")
        layout.addWidget(title)
        description = QLabel("Streamer and viewer tasks, grouped by owner. Finished tasks can be reopened or archived.")
        description.setObjectName("Muted")
        description.setWordWrap(True)
        layout.addWidget(description)

        controls = QVBoxLayout()
        filter_controls = QHBoxLayout()
        self.filter = QComboBox()
        self.filter.addItems(["All", "Active", "Finished"])
        self.filter.currentTextChanged.connect(self.refresh)
        filter_controls.addWidget(QLabel("Filter:"))
        filter_controls.addWidget(self.filter)
        filter_controls.addStretch(1)
        controls.addLayout(filter_controls)

        selected_task_actions = QHBoxLayout()
        selected_task_actions.setSpacing(10)
        # ---- TASK WINDOW ACTION BUTTONS ----
        # This section contains the task actions I still use.
        self.reopen_button = QPushButton("Reopen Task")
        self.reopen_button.clicked.connect(self.reopen_selected)
        self.remove_viewer_button = QPushButton("Remove Viewer From List")
        self.remove_viewer_button.clicked.connect(self.remove_selected_participant)
        for button in (self.reopen_button, self.remove_viewer_button):
            self._style_task_action_button(button)
            selected_task_actions.addWidget(button)
        selected_task_actions.addStretch(1)
        controls.addLayout(selected_task_actions)
        layout.addLayout(controls)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Viewer / task", "State", "Created", "Completed"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 360)
        self.tree.setColumnWidth(1, 130)
        self.tree.itemChanged.connect(self.handle_item_changed)
        layout.addWidget(self.tree, 1)

        # ---- COMPLETED TASK ACTION BUTTONS ----
        # These buttons let me delete or archive my completed tasks.
        # peepeepoo poo, my completed-task buttons finally sit together.
        completed_actions = QHBoxLayout()
        completed_actions.setSpacing(10)
        completed_actions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # This button deletes my finished tasks from the list.
        self.clear_finished_button = QPushButton("Delete Completed Tasks")
        self.clear_finished_button.clicked.connect(self.clear_finished)
        self.archive_completed_button = QPushButton("Archive Completed Tasks")
        self.archive_completed_button.clicked.connect(self.archive_completed)
        for button in (self.clear_finished_button, self.archive_completed_button):
            self._style_task_action_button(button)
            completed_actions.addWidget(button, 1, Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(completed_actions)
        self.refresh()

    def _style_task_action_button(self, button: QPushButton) -> None:
        # ---- TASK WINDOW ACTION BUTTONS ----
        # This keeps my longer Task window labels from getting chopped off.
        # peepeepoo poo, the buttons can finally breathe.
        button.setObjectName("TaskActionButton")
        button.setMinimumWidth(220)
        button.setMaximumWidth(420)
        button.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)

    def refresh(self) -> None:
        self._loading = True
        mode = self.filter.currentText()
        self.tree.clear()
        for person in self.repository.task_snapshot(include_completed=True):
            tasks = person["tasks"]
            if mode == "Active":
                tasks = [task for task in tasks if not task["is_complete"]]
            elif mode == "Finished":
                tasks = [task for task in tasks if task["is_complete"]]
            if not tasks:
                continue
            parent = QTreeWidgetItem(
                [
                    person["display_name"],
                    "Streamer" if person["participant_type"] == "streamer" else "Viewer",
                    "",
                    "",
                ]
            )
            parent.setData(0, Qt.ItemDataRole.UserRole, {"participant_id": person["id"]})
            self.tree.addTopLevelItem(parent)
            for task in tasks:
                state = "Finished" if task["is_complete"] else "Active"
                item = QTreeWidgetItem([task["text"], state, task["created_at"][:16], (task["completed_at"] or "")[:16]])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Checked if task["is_complete"] else Qt.CheckState.Unchecked)
                item.setData(0, Qt.ItemDataRole.UserRole, {"task_id": task["id"], "complete": task["is_complete"]})
                if task["is_complete"]:
                    item.setForeground(0, Qt.GlobalColor.gray)
                    item.setForeground(1, Qt.GlobalColor.gray)
                parent.addChild(item)
            parent.setExpanded(True)
        self._loading = False

    def handle_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._loading or column != 0:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        task_id = data.get("task_id")
        if not task_id:
            return
        self.repository.set_task_complete(task_id, item.checkState(0) == Qt.CheckState.Checked)
        self.refresh()
        self.on_change()

    def selected_data(self) -> dict:
        item = self.tree.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item else {}

    def reopen_selected(self) -> None:
        data = self.selected_data()
        if "task_id" not in data:
            return
        self.repository.set_task_complete(data["task_id"], False)
        self.refresh()
        self.on_change()

    def remove_selected_participant(self) -> None:
        data = self.selected_data()
        if "participant_id" not in data:
            QMessageBox.information(self, "Study Budy", "Select a viewer or streamer heading first.")
            return
        if QMessageBox.question(self, "Remove viewer", "Remove this person from the active list while preserving stored task data?") == QMessageBox.StandardButton.Yes:
            self.repository.remove_participant(data["participant_id"])
            self.refresh()
            self.on_change()

    def clear_finished(self) -> None:
        self.repository.archive_completed()
        self.refresh()
        self.on_change()

    def archive_completed(self) -> None:
        self.repository.archive_completed()
        self.refresh()
        self.on_change()

    def closeEvent(self, event) -> None:
        self.settings.setValue("task_window/geometry", self.saveGeometry())
        super().closeEvent(event)
