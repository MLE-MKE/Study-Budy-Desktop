import os
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Go from app folder to project root
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

# Path to data folder
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Path to tasks file
TASK_FILE = os.path.join(DATA_DIR, "tasks.json")

# Ensure data folder exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Ensure tasks.json exists
if not os.path.exists(TASK_FILE):
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=4)


# ---- LOAD TASKS ----
def load_tasks():
    try:
        with open(TASK_FILE, "r", encoding="utf-8") as f:
            tasks = json.load(f)

        if not isinstance(tasks, dict):
            return {}

        return tasks

    except (json.JSONDecodeError, FileNotFoundError):
        return {}


# ---- SAVE TASKS ----
def save_tasks(tasks):
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4)


# ---- GET TASKS FOR ONE USER ----
def get_tasks(user):
    tasks = load_tasks()
    return tasks.get(user, [])


# ---- ADD TASK FOR ONE USER ----
def add_task(user, task):
    tasks = load_tasks()

    if user not in tasks:
        tasks[user] = []

    tasks[user].append(task)
    save_tasks(tasks)

    return tasks[user]


# ---- COMPLETE TASK FOR ONE USER ----
def complete_task(user, task_number):
    tasks = load_tasks()

    if user not in tasks:
        return None

    if task_number < 1 or task_number > len(tasks[user]):
        return None

    completed_task = tasks[user].pop(task_number - 1)
    save_tasks(tasks)

    return completed_task


# ---- CLEAR ALL TASKS FOR ONE USER ----
def clear_tasks(user):
    tasks = load_tasks()

    if user not in tasks:
        return False

    del tasks[user]
    save_tasks(tasks)

    return True


# ---- FORMAT TASKS FOR DISPLAY ----
def format_tasks(user):
    user_tasks = get_tasks(user)

    if not user_tasks:
        return "No tasks found."

    lines = []
    for i, task in enumerate(user_tasks, start=1):
        lines.append(f"{i}. {task}")

    return "\n".join(lines)