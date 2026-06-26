"""Local-only Browser Source overlay service."""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request, send_from_directory

from .checkin import CheckInService
from .resources import resource_path
from .storage import TaskRepository
from .timer.service import TimerService

DEFAULT_APPEARANCE = {
    "task_list_title": "My Study Stream", "title_icon": "book",
    "layout_mode": "cycle", "cycle_seconds": 15, "show_completed": False,
    "hide_empty": True, "font_family": "Comic Sans MS", "participant_font_size": 26,
    "task_font_size": 18, "text_color": "#ffffff", "completed_text_color": "#a9a9a9",
    "background_color": "#000000", "background_opacity": 60, "card_color": "#1f1830",
    "card_opacity": 85, "border_color": "#9f7aea", "border_radius": 12, "padding": 20,
}


def create_overlay_app(repository: TaskRepository) -> Flask:
    app = Flask(__name__, template_folder=str(resource_path("templates")))
    checkins = CheckInService(repository)
    timer = TimerService(repository)
    overlay_dir = resource_path("overlay")

    @app.after_request
    def no_cache_timer(response):
        if request.path.startswith(("/timer", "/api/timer")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @app.get("/health")
    def health():
        return jsonify({"status": "running"})

    @app.get("/api/overlay")
    def overlay_data():
        appearance = {**DEFAULT_APPEARANCE, **repository.get_setting("appearance", {})}
        try:
            appearance["cycle_seconds"] = max(8, int(appearance.get("cycle_seconds") or 8))
        except (TypeError, ValueError):
            appearance["cycle_seconds"] = DEFAULT_APPEARANCE["cycle_seconds"]
        participants = repository.task_snapshot(include_completed=appearance["show_completed"])
        if appearance["hide_empty"]:
            participants = [item for item in participants if item["tasks"]]
        return jsonify({"participants": participants, "appearance": appearance})

    @app.get("/api/checkin")
    def checkin_data():
        return jsonify(checkins.snapshot())

    @app.get("/api/timer")
    def timer_data():
        return jsonify(timer.snapshot())

    @app.get("/overlay")
    def overlay():
        return render_template("overlay.html")

    @app.get("/checkin")
    def checkin():
        return send_from_directory(overlay_dir, "checkin.html")

    @app.get("/timer")
    def timer_overlay():
        return send_from_directory(overlay_dir, "timer.html")

    @app.get("/checkin/<path:filename>")
    def checkin_asset(filename: str):
        return send_from_directory(overlay_dir, filename)

    @app.get("/timer/<path:filename>")
    def timer_asset(filename: str):
        return send_from_directory(overlay_dir, filename)

    @app.get("/timer/fonts/<path:filename>")
    def timer_font(filename: str):
        return send_from_directory(resource_path("assets") / "fonts", filename)

    return app
