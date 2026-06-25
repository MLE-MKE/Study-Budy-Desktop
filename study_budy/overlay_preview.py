"""Shared overlay preview widget for the dashboard and appearance screens."""

from __future__ import annotations

from html import escape

from PySide6.QtWidgets import QFrame, QLabel, QTextBrowser, QVBoxLayout

from .icons import icon
from .storage import TaskRepository
from .theme import Theme

TITLE_ICONS = {
    "book": "▰",
    "box": "▣",
    "star": "☆",
    "heart": "♡",
}


class OverlayPreview(QFrame):
    def __init__(self, repository: TaskRepository, compact: bool = False) -> None:
        super().__init__()
        self.repository = repository
        self.compact = compact
        self.setObjectName("Card")
        self.setMinimumHeight(300 if compact else 390)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING, Theme.CARD_PADDING)
        title = QLabel("Overlay Preview")
        title.setObjectName("H2")
        layout.addWidget(title)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        layout.addWidget(self.browser, 1)
        self.refresh()

    def refresh(self) -> None:
        appearance = self.repository.get_setting("appearance", {})
        title = appearance.get("task_list_title", "My Study Stream")
        title_icon = TITLE_ICONS.get(appearance.get("title_icon", "book"), "📖")
        show_completed = bool(appearance.get("show_completed", True))
        participants = [p for p in self.repository.task_snapshot(include_completed=show_completed) if p["tasks"]]
        if not participants:
            participants = [
                {
                    "display_name": "Killer_Queen55",
                    "participant_type": "streamer",
                    "tasks": [
                        {"text": "Review lecture notes", "is_complete": True},
                        {"text": "Finish math problem set", "is_complete": False},
                        {"text": "Read Chapter 8", "is_complete": False},
                    ],
                },
                {
                    "display_name": "Alex",
                    "participant_type": "viewer",
                    "tasks": [
                        {"text": "Study vocab", "is_complete": False},
                        {"text": "Do flashcards", "is_complete": True},
                    ],
                },
                {
                    "display_name": "Jamie",
                    "participant_type": "viewer",
                    "tasks": [{"text": "Complete quiz", "is_complete": False}],
                },
            ]

        streamer = next((p for p in participants if p.get("participant_type") == "streamer"), participants[0])
        viewers = [p for p in participants if p is not streamer][:3]
        html = f"""
        <style>
          body {{ background:#090817; color:#fff; font-family: Comic Sans MS, Segoe UI, sans-serif; }}
          .wrap {{ border:1px solid #8a39ff; border-radius:10px; padding:14px; background:#0f0d22; }}
          h2 {{ color:#bd75ff; text-align:center; margin:0 0 14px 0; letter-spacing:1px; }}
          h3 {{ margin:6px 0; color:#fff; }}
          .streamer {{ border-left:3px solid #ffd84f; padding-left:10px; margin-bottom:10px; }}
          .viewer {{ border:1px solid #372757; border-radius:8px; padding:8px; margin:7px 0; }}
          .task {{ margin:5px 0; font-size:13px; }}
          .done {{ color:#9b95a8; text-decoration: line-through; }}
        </style>
        <div class="wrap"><h2>{escape(title_icon)} {escape(title)}</h2>
        <div class="streamer"><h3>♛ {escape(streamer["display_name"])}</h3>
        {self._tasks(streamer["tasks"][:4])}</div>
        """
        for viewer in viewers:
            html += f'<div class="viewer"><h3>{escape(viewer["display_name"])}</h3>{self._tasks(viewer["tasks"][:3])}</div>'
        html += "</div>"
        self.browser.setHtml(html)

    @staticmethod
    def _tasks(tasks: list[dict]) -> str:
        lines = []
        for task in tasks:
            checked = "☑" if task.get("is_complete") else "☐"
            klass = "task done" if task.get("is_complete") else "task"
            lines.append(f'<div class="{klass}">{checked} {escape(task["text"])}</div>')
        return "".join(lines)
