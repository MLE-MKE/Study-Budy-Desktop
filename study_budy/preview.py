"""Explicit development-mode sample data; never enabled by default."""

from .checkin import CheckInService
from .storage import TaskRepository


def seed_preview_data(repository: TaskRepository) -> None:
    if repository.get_setting("preview_seeded", False):
        return
    samples = {
        "Killer_Queen55": [("Review lecture notes", False), ("Finish math problem set", False), ("Read Chapter 8", True)],
        "Alex": [("Study vocabulary", False), ("Do flashcards", False), ("Watch tutorial", False)],
        "Jamie": [("Read pages 45–60", False), ("Complete quiz", True), ("Practice problems", False)],
        "FlowFox": [("Organize notes", False), ("Write summary", False), ("Review formulas", True)],
    }
    for name, tasks in samples.items():
        kind = "streamer" if name == "Killer_Queen55" else "viewer"
        for text, done in tasks:
            task = repository.add_task(name, text, kind)
            if done:
                repository.set_task_complete(task["id"], True)
    repository.set_setting("preview_mode", True)
    repository.set_setting("preview_bot_name", "killer_queens_jester")
    appearance = repository.get_setting("appearance", {})
    appearance.update({"task_list_title": "My Study Stream", "title_icon": "book", "show_completed": True})
    repository.set_setting("appearance", appearance)
    checkins = CheckInService(repository)
    checkins.checkin("streamer-preview", "Killer_Queen55", is_streamer=True)
    checkins.set_shape("alex-preview", "Alex", "circle")
    checkins.checkin("alex-preview", "Alex")
    checkins.set_shape("jamie-preview", "Jamie", "triangle")
    checkins.checkin("jamie-preview", "Jamie")
    checkins.set_shape("flowfox-preview", "FlowFox", "square")
    checkins.checkin("flowfox-preview", "FlowFox")
    repository.set_setting("preview_seeded", True)
