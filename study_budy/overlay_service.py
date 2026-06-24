"""Local-only Browser Source overlay service."""

from __future__ import annotations

from flask import Flask, jsonify, render_template

from .storage import TaskRepository

DEFAULT_APPEARANCE = {
    "layout_mode": "cycle", "cycle_seconds": 15, "show_completed": False,
    "hide_empty": True, "font_family": "Segoe UI", "participant_font_size": 26,
    "task_font_size": 18, "text_color": "#ffffff", "completed_text_color": "#a9a9a9",
    "background_color": "#000000", "background_opacity": 60, "card_color": "#1f1830",
    "card_opacity": 85, "border_color": "#9f7aea", "border_radius": 12, "padding": 20,
}


def create_overlay_app(repository: TaskRepository) -> Flask:
    app = Flask(__name__, template_folder="templates")

    @app.get("/health")
    def health():
        return jsonify({"status": "running"})

    @app.get("/api/overlay")
    def overlay_data():
        appearance = {**DEFAULT_APPEARANCE, **repository.get_setting("appearance", {})}
        participants = repository.task_snapshot(include_completed=appearance["show_completed"])
        if appearance["hide_empty"]:
            participants = [item for item in participants if item["tasks"]]
        return jsonify({"participants": participants, "appearance": appearance})

    @app.get("/overlay")
    def overlay():
        return render_template("overlay.html")

    return app
