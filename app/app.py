# Import Flask tools
from flask import Flask, json, jsonify, render_template

# Import your task manager functions (these handle JSON storage)
from storage.task_manager import get_tasks, add_task, clear_tasks, complete_task, load_tasks    

# Create the Flask serverpy app.py
app = Flask(__name__)

#for list cycling of task lsit per user




# -------------------------
# ROUTES (your API endpoints)
# -------------------------

# Basic route to confirm server is running
@app.route("/")
def home():
    return "Study Budy server is running."

# Route to serve the overlay page for a specific user
@app.route("/overlay/<username>")
def overlay(username):
    return render_template("overlay.html", username=username)

# Get Tasks Function
@app.route("/tasks/<username>")
def tasks_route(username):
    return jsonify({"tasks": get_tasks(username)})

# Add Task Function
@app.route("/add/<username>/<task>")
def add_task_route(username, task):
    updated_tasks = add_task(username, task)
    return jsonify({"success": True, "tasks": updated_tasks})

#Clear Function
@app.route("/clear/<username>")
def clear_tasks_route(username):
    success = clear_tasks(username)
    return jsonify({"success": success, "tasks": get_tasks(username)})

# Complete Task Function
@app.route("/done/<username>/<int:task_number>")
def done_task_route(username, task_number):
    completed = complete_task(username, task_number)

    return jsonify({
        "success": completed is not None,
        "completed": completed,
        "tasks": get_tasks(username)
    })



@app.route("/overlay_priority")
def get_overlay_priority():
    global priority_user
    return jsonify({"priority_user": priority_user})

@app.route("/overlay_priority/clear")
def clear_overlay_priority():
    global priority_user
    priority_user = None
    return jsonify({"success": True})

# -------------------------
# START SERVER
# -------------------------

if __name__ == "__main__":
    # host="0.0.0.0" allows other devices (like OBS PC) to connect
    # port=5000 is where your server runs
    # debug=True auto-restarts server when you edit code
    app.run(host="0.0.0.0", port=5000, debug=True)