"""Dedicated viewer and streamer task window with active/finished filters."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from .storage import TaskRepository


class TaskWindow(QWidget):
    def __init__(self, repository: TaskRepository) -> None:
        super().__init__()
        self.repository = repository
        self.settings = QSettings("Hotkey LLC", "Study Budy")
        self.setWindowTitle("Study Budy — Viewer Task Window")
        self.setMinimumSize(680, 520)
        self.resize(self.settings.value("task_window/size", self.size()))
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h1>Viewer Task Window</h1><p>Active and finished tasks remain grouped under their owner.</p>"))
        controls = QHBoxLayout(); self.filter = QComboBox(); self.filter.addItems(["All", "Active", "Finished"]); self.filter.currentTextChanged.connect(self.refresh); controls.addWidget(QLabel("Show:")); controls.addWidget(self.filter); controls.addStretch(1)
        self.archive = QPushButton("Archive Finished Tasks"); self.archive.clicked.connect(self.archive_finished); controls.addWidget(self.archive); layout.addLayout(controls)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Viewer / task", "State", "Created", "Completed"]); self.tree.setAlternatingRowColors(True); self.tree.setColumnWidth(0, 300); layout.addWidget(self.tree)
        self.refresh()

    def refresh(self) -> None:
        mode = self.filter.currentText(); self.tree.clear()
        for person in self.repository.task_snapshot(include_completed=True):
            tasks = person["tasks"]
            if mode == "Active": tasks = [task for task in tasks if not task["is_complete"]]
            if mode == "Finished": tasks = [task for task in tasks if task["is_complete"]]
            if not tasks: continue
            parent = QTreeWidgetItem([person["display_name"], "Streamer" if person["participant_type"] == "streamer" else "Viewer", "", ""]); self.tree.addTopLevelItem(parent)
            for task in tasks:
                state = "✓ Finished" if task["is_complete"] else "□ Active"
                item = QTreeWidgetItem([task["text"], state, task["created_at"][:16], (task["completed_at"] or "")[:16]])
                if task["is_complete"]:
                    item.setForeground(0, Qt.gray)
                parent.addChild(item)
            parent.setExpanded(True)

    def archive_finished(self) -> None:
        self.repository.archive_completed(); self.refresh()

    def closeEvent(self, event) -> None:
        self.settings.setValue("task_window/geometry", self.saveGeometry())
        super().closeEvent(event)
