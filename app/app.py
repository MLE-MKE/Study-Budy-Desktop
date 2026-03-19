# Import Flask tools
from flask import Flask, jsonify, render_template_string

# Import your task manager functions (these handle JSON storage)
from storage.task_manager import get_tasks, add_task, clear_tasks   

# Create the Flask server
app = Flask(__name__)

# Default user (this is who the overlay will display for now)
# Later this will be replaced with Twitch usernames
DEFAULT_USER = "stream"


# OBS overlay HTML (this is what shows on your stream)
OVERLAY_HTML = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>Study Budy Overlay</title>

    <style>
        /* Remove default spacing and make background transparent for OBS */
        body {
            margin: 0;
            background: transparent;
            color: white;
            font-family: Arial, sans-serif;
        }

        /* Main container box for tasks */
        .box {
            padding: 20px;
            margin: 20px;
            background: rgba(0, 0, 0, 0.6);
            border-radius: 12px;
            width: 400px;
        }

        /* Title styling */
        h1 {
            margin-top: 0;
            font-size: 28px;
        }

        /* Each task item */
        li {
            font-size: 22px;
            margin-bottom: 10px;
        }
    </style>
</head>

<body>
    <div class="box">
        <h1>PEE PEE POO POO test confirmation</h1>

        <!-- Tasks will be inserted here dynamically -->
        <ul id="task-list"></ul>
    </div>

    <script>
        // Function to fetch tasks from Flask server
        async function loadTasks() {
            try {
                // Call backend /tasks route
                const response = await fetch('/tasks');

                // Convert response to JSON
                const data = await response.json();

                // Grab task list element
                const list = document.getElementById('task-list');

                // Clear old tasks before updating
                list.innerHTML = '';

                // Add each task to the list
                data.tasks.forEach(task => {
                    const li = document.createElement('li');
                    li.textContent = task;
                    list.appendChild(li);
                });

            } catch (error) {
                // If server is unreachable or fails
                console.error('Failed to load tasks:', error);
            }
        }

        // Run once when page loads
        loadTasks();

        // Refresh every 2 seconds for live updates
        setInterval(loadTasks, 2000);
    </script>
</body>
</html>
"""


# -------------------------
# ROUTES (your API endpoints)
# -------------------------

# Basic route to confirm server is running
@app.route("/")
def home():
    return "Study Budy server is running."


# Serves the overlay HTML to OBS/browser
@app.route("/overlay")
def overlay():
    return render_template_string(OVERLAY_HTML)


# Returns tasks for DEFAULT_USER from JSON file
@app.route("/tasks")
def tasks_route():
    return jsonify({"tasks": get_tasks(DEFAULT_USER)})


# Adds a task for DEFAULT_USER and saves it to JSON
# Example: /add/Do%20Homework
@app.route("/add/<task>")
def add_task_route(task):
    updated_tasks = add_task(DEFAULT_USER, task)
    return jsonify({"success": True, "tasks": updated_tasks})


# Clears all tasks for DEFAULT_USER
@app.route("/clear")
def clear_tasks_route():
    success = clear_tasks(DEFAULT_USER)
    return jsonify({"success": success, "tasks": get_tasks(DEFAULT_USER)})


# -------------------------
# START SERVER
# -------------------------

if __name__ == "__main__":
    # host="0.0.0.0" allows other devices (like OBS PC) to connect
    # port=5000 is where your server runs
    # debug=True auto-restarts server when you edit code
    app.run(host="0.0.0.0", port=5000, debug=True)