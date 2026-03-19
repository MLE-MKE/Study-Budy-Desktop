# Import Flask tools
from flask import Flask, jsonify, render_template, render_template_string

# Import your task manager functions (these handle JSON storage)
from storage.task_manager import get_tasks, add_task, clear_tasks   

# Create the Flask server
app = Flask(__name__)

# Default user (this is who the overlay will display for now)
# Later this will be replaced with Twitch usernames
username = "stream"




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

# -------------------------
# START SERVER
# -------------------------

if __name__ == "__main__":
    # host="0.0.0.0" allows other devices (like OBS PC) to connect
    # port=5000 is where your server runs
    # debug=True auto-restarts server when you edit code
    app.run(host="0.0.0.0", port=5000, debug=True)