"""Dedicated viewer and streamer task window with active/finished controls."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
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

        controls = QHBoxLayout()
        self.filter = QComboBox()
        self.filter.addItems(["All", "Active", "Finished"])
        self.filter.currentTextChanged.connect(self.refresh)
        controls.addWidget(QLabel("Filter:"))
        controls.addWidget(self.filter)
        controls.addStretch(1)
        self.reopen_button = QPushButton("Reopen Task")
        self.reopen_button.clicked.connect(self.reopen_selected)
        self.archive_button = QPushButton("Archive Completed Task")
        self.archive_button.clicked.connect(self.archive_selected)
        self.remove_viewer_button = QPushButton("Remove Viewer From Active List")
        self.remove_viewer_button.clicked.connect(self.remove_selected_participant)
        self.clear_finished_button = QPushButton("Clear Finished Tasks")
        self.clear_finished_button.clicked.connect(self.clear_finished)
        for button in (self.reopen_button, self.archive_button, self.remove_viewer_button, self.clear_finished_button):
            controls.addWidget(button)
        layout.addLayout(controls)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Viewer / task", "State", "Created", "Completed"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 360)
        self.tree.setColumnWidth(1, 130)
        self.tree.itemChanged.connect(self.handle_item_changed)
        layout.addWidget(self.tree, 1)
        self.refresh()

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

    def archive_selected(self) -> None:
        data = self.selected_data()
        if "task_id" not in data:
            return
        self.repository.archive_task(data["task_id"])
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

    def closeEvent(self, event) -> None:
        self.settings.setValue("task_window/geometry", self.saveGeometry())
        super().closeEvent(event)
