"""Appearance controls used by the right dashboard column and full page."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from .icons import icon
from .overlay_service import DEFAULT_APPEARANCE
from .storage import TaskRepository
from .theme import Theme


class AppearancePanel(QFrame):
    def __init__(self, repository: TaskRepository, on_save) -> None:
        super().__init__()
        self.repository = repository
        self.on_save = on_save
        self.setObjectName("Card")
        self.setMinimumHeight(560)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        layout.setSpacing(12)
        title = QLabel("Appearance")
        title.setObjectName("H2")
        layout.addWidget(title)

        form = QFormLayout()
        form.setVerticalSpacing(8)
        form.setHorizontalSpacing(10)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.task_list_title = QLineEdit()
        self.title_icon = QComboBox()
        self.title_icon.addItem("Book", "book")
        self.title_icon.addItem("Box", "box")
        self.title_icon.addItem("Star", "star")
        self.title_icon.addItem("Heart", "heart")
        self.font_name = QComboBox()
        self.font_name.addItems(["Comic Sans MS", "Comic Neue", "Segoe Print", "Segoe UI"])
        self.task_size = QSpinBox()
        self.task_size.setRange(10, 48)
        self.task_size.setSuffix(" px")
        self.text_color = QLineEdit()
        self.background_color = QLineEdit()
        self.opacity = QSpinBox()
        self.opacity.setRange(0, 100)
        self.opacity.setSuffix(" %")
        self.layout_mode = QComboBox()
        self.layout_mode.addItem("Cycle everyone", "cycle")
        self.layout_mode.addItem("Streamer on top", "streamer_top")
        self.corner_radius = QSpinBox()
        self.corner_radius.setRange(0, 48)
        self.corner_radius.setSuffix(" px")
        self.show_finished = QCheckBox("Show Finished Tasks")

        for label, field in (
            ("Task List Title", self.task_list_title),
            ("Title Icon", self.title_icon),
            ("Font", self.font_name),
            ("Text size", self.task_size),
            ("Text color", self.text_color),
            ("Background color", self.background_color),
            ("Background opacity", self.opacity),
            ("Layout mode", self.layout_mode),
            ("Corner radius", self.corner_radius),
            ("Finished tasks", self.show_finished),
        ):
            field.setMinimumWidth(150)
            form.addRow(label, field)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        upload = QPushButton("Upload Image")
        upload.setIcon(icon("upload"))
        upload.clicked.connect(self.choose_image)
        save = QPushButton("Save")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self.save)
        buttons.addWidget(upload)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        self.load()

    def load(self) -> None:
        appearance = {**DEFAULT_APPEARANCE, **self.repository.get_setting("appearance", {})}
        self.task_list_title.setText(appearance["task_list_title"])
        icon_index = self.title_icon.findData(appearance["title_icon"])
        self.title_icon.setCurrentIndex(max(icon_index, 0))
        index = self.font_name.findText(appearance["font_family"])
        self.font_name.setCurrentIndex(max(index, 0))
        self.task_size.setValue(int(appearance["task_font_size"]))
        self.text_color.setText(appearance["text_color"])
        self.background_color.setText(appearance["background_color"])
        self.opacity.setValue(int(appearance["background_opacity"]))
        mode = self.layout_mode.findData(appearance["layout_mode"])
        self.layout_mode.setCurrentIndex(max(mode, 0))
        self.corner_radius.setValue(int(appearance["border_radius"]))
        self.show_finished.setChecked(bool(appearance["show_completed"]))

    def save(self) -> None:
        current = {**DEFAULT_APPEARANCE, **self.repository.get_setting("appearance", {})}
        current.update(
            {
                "font_family": self.font_name.currentText(),
                "task_list_title": self.task_list_title.text().strip() or DEFAULT_APPEARANCE["task_list_title"],
                "title_icon": self.title_icon.currentData(),
                "task_font_size": self.task_size.value(),
                "text_color": self.text_color.text().strip() or DEFAULT_APPEARANCE["text_color"],
                "background_color": self.background_color.text().strip() or DEFAULT_APPEARANCE["background_color"],
                "background_opacity": self.opacity.value(),
                "layout_mode": self.layout_mode.currentData(),
                "border_radius": self.corner_radius.value(),
                "show_completed": self.show_finished.isChecked(),
            }
        )
        self.repository.set_setting("appearance", current)
        self.on_save()

    def choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Upload overlay image", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            self.repository.set_setting("last_selected_overlay_image", path)
