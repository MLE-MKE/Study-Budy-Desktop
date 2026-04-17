from flask import Flask, jsonify, render_template
from storage.task_manager import get_tasks, add_task, clear_tasks, complete_task, load_tasks

app = Flask(__name__)

priority_user = None


@app.route("/")
def home():
    return "Study Budy server is running."


# Main OBS overlay: rotating all users
@app.route("/overlay")
def rotating_overlay():
    return render_template("overlay_rotate.html")


# Optional single user overlay if you still want it for testing
@app.route("/overlay/<username>")
def overlay(username):
    return render_template("overlay.html", username=username)


@app.route("/tasks/<username>")
def tasks_route(username):
    return jsonify({"tasks": get_tasks(username)})


@app.route("/add/<username>/<task>")
def add_task_route(username, task):
    updated_tasks = add_task(username, task)
    return jsonify({"success": True, "tasks": updated_tasks})


@app.route("/clear/<username>")
def clear_tasks_route(username):
    success = clear_tasks(username)
    return jsonify({"success": success, "tasks": get_tasks(username)})


@app.route("/done/<username>/<int:task_number>")
def done_task_route(username, task_number):
    completed = complete_task(username, task_number)
    return jsonify({
        "success": completed is not None,
        "completed": completed,
        "tasks": get_tasks(username)
    })


@app.route("/all_tasks")
def all_tasks_route():
    return jsonify(load_tasks())


@app.route("/overlay_priority/<username>")
def set_overlay_priority(username):
    global priority_user
    priority_user = username
    return jsonify({"success": True, "priority_user": priority_user})


@app.route("/overlay_priority")
def get_overlay_priority():
    global priority_user
    return jsonify({"priority_user": priority_user})


@app.route("/overlay_priority/clear")
def clear_overlay_priority():
    global priority_user
    priority_user = None
    return jsonify({"success": True, "priority_user": priority_user})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)