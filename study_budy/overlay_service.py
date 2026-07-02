"""Local-only Browser Source overlay service."""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request, send_from_directory

from .checkin import CheckInService
from .overlay_clients import CHECKIN_OVERLAY_CLIENT, TIMER_OVERLAY_CLIENT, record_overlay_heartbeat
from .resources import resource_path
from .storage import TaskRepository
from .timer.service import TimerService
from .twitch.chat import MONITORED_CHANNEL_KEY, STREAMER_METADATA_KEY

DEFAULT_APPEARANCE = {
    "task_list_title": "My Study Stream", "title_icon": "book",
    "layout_mode": "cycle", "cycle_seconds": 15, "show_completed": False,
    "hide_empty": True, "font_family": "Comic Sans MS", "participant_font_size": 26,
    "task_font_size": 18, "text_color": "#ffffff", "completed_text_color": "#a9a9a9",
    "background_color": "#000000", "background_opacity": 60, "card_color": "#1f1830",
    "card_opacity": 85, "border_color": "#9f7aea", "border_radius": 12, "padding": 20,
}

LAYOUT_MODE_CYCLE = "cycle"
LAYOUT_MODE_LIST = "list"
OLD_STREAMER_TOP_LAYOUT_VALUES = {"streamer_top", "Streamer on Top", "Streamer on top", "streamer on top"}


def normalize_layout_mode(value: object) -> str:
    # ---- LAYOUT MODE SETTING MIGRATION ----
    # This changes my old Streamer on Top setting into the new List layout.
    if value in OLD_STREAMER_TOP_LAYOUT_VALUES:
        return LAYOUT_MODE_LIST
    if value == LAYOUT_MODE_LIST:
        return LAYOUT_MODE_LIST
    return LAYOUT_MODE_CYCLE


def connected_streamer(repository: TaskRepository) -> dict[str, str]:
    # ---- CONNECTED STREAMER LOOKUP ----
    # This section uses the currently connected stream channel as my streamer.
    streamer = repository.get_setting(STREAMER_METADATA_KEY, None) or {}
    channel = repository.get_setting(MONITORED_CHANNEL_KEY, "") or streamer.get("login", "")
    login = str(channel or streamer.get("login", "")).strip().lstrip("#").casefold()
    display_name = str(streamer.get("display_name") or streamer.get("login") or login or "").strip()
    user_id = str(streamer.get("user_id") or "").strip()
    return {"login": login, "display_name": display_name, "user_id": user_id}


def order_participants_for_list_layout(participants: list[dict], streamer: dict[str, str]) -> list[dict]:
    # ---- LIST LAYOUT MODE ----
    # This layout puts the connected streamer's to-do list at the top.
    if not streamer.get("login") and not streamer.get("user_id"):
        return participants
    names = {streamer.get("login", "").casefold(), streamer.get("display_name", "").casefold()} - {""}
    user_id = streamer.get("user_id", "")
    streamer_matches, other_participants = [], []
    for participant in participants:
        display_name = str(participant.get("display_name", "")).casefold()
        twitch_user_id = str(participant.get("twitch_user_id") or "")
        is_match = bool(user_id and twitch_user_id == user_id) or display_name in names or participant.get("participant_type") == "streamer"
        (streamer_matches if is_match else other_participants).append(participant)
    if not streamer_matches:
        return participants

    streamer_section = {**streamer_matches[0]}
    if streamer.get("display_name"):
        streamer_section["display_name"] = streamer["display_name"]
    streamer_section["participant_type"] = "streamer"
    combined_tasks, seen_task_ids = [], set()
    for participant in streamer_matches:
        for task in participant.get("tasks", []):
            if task["id"] in seen_task_ids:
                continue
            seen_task_ids.add(task["id"])
            combined_tasks.append(task)
    streamer_section["tasks"] = combined_tasks
    return [streamer_section, *other_participants]


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
        appearance["layout_mode"] = normalize_layout_mode(appearance.get("layout_mode"))
        try:
            appearance["cycle_seconds"] = max(8, int(appearance.get("cycle_seconds") or 8))
        except (TypeError, ValueError):
            appearance["cycle_seconds"] = DEFAULT_APPEARANCE["cycle_seconds"]
        participants = repository.task_snapshot(include_completed=appearance["show_completed"])
        if appearance["hide_empty"]:
            participants = [item for item in participants if item["tasks"]]
        streamer = connected_streamer(repository)
        if appearance["layout_mode"] == LAYOUT_MODE_LIST:
            participants = order_participants_for_list_layout(participants, streamer)
        return jsonify({"participants": participants, "appearance": appearance, "connected_streamer": streamer})

    @app.get("/api/checkin")
    def checkin_data():
        return jsonify(checkins.snapshot())

    @app.get("/api/timer")
    def timer_data():
        return jsonify(timer.snapshot())

    @app.post("/api/overlay-clients/<client_id>/heartbeat")
    def overlay_client_heartbeat(client_id: str):
        if client_id not in {TIMER_OVERLAY_CLIENT, CHECKIN_OVERLAY_CLIENT}:
            return jsonify({"error": "unknown overlay client"}), 404
        record_overlay_heartbeat(client_id)
        return jsonify({"status": "connected", "client": client_id})

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
