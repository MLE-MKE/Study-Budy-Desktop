import os
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Go from app/storage to project root
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))

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


# ---- Normalize user task text ----
def normalize_user_tasks(user_tasks):
    normalized = []

    for item in user_tasks:
        if isinstance(item, dict):
            normalized.append({
                "text": item.get("text", ""),
                "done": bool(item.get("done", False))
            })
        else:
            # old string task support
            normalized.append({
                "text": str(item),
                "done": False
            })

    return normalized

# ---- GET TASKS FOR ALL USERS ----

def get_all_tasks():
    tasks = load_tasks()

    for user in tasks:
        tasks[user] = normalize_user_tasks(tasks[user])

    save_tasks(tasks)
    return tasks



# ---- GET TASKS FOR ONE USER ----
def get_tasks(user):
    tasks = load_tasks()
    user_tasks = tasks.get(user, [])
    normalized = normalize_user_tasks(user_tasks)

    if user in tasks and tasks[user] != normalized:
        tasks[user] = normalized
        save_tasks(tasks)

    return normalized


# ---- ADD TASK FOR ONE USER ----
def add_task(user, task):
    tasks = load_tasks()

    if user not in tasks:
        tasks[user] = []

    tasks[user] = normalize_user_tasks(tasks[user])
    tasks[user].append({
        "text": task,
        "done": False
    })

    save_tasks(tasks)
    return tasks[user]



# ---- COMPLETE TASK FOR ONE USER ----
def complete_task(user, task_number):
    tasks = load_tasks()

    if user not in tasks:
        return None

    tasks[user] = normalize_user_tasks(tasks[user])

    if task_number < 1 or task_number > len(tasks[user]):
        return None

    tasks[user][task_number - 1]["done"] = True
    completed_task = tasks[user][task_number - 1]

    save_tasks(tasks)
    return completed_task


# ---- UNDO COMPLETE TASK FOR ONE USER ----
def undo_task(user, task_number):
    tasks = load_tasks()

    if user not in tasks:
        return None

    tasks[user] = normalize_user_tasks(tasks[user])

    if task_number < 1 or task_number > len(tasks[user]):
        return None

    tasks[user][task_number - 1]["done"] = False
    undone_task = tasks[user][task_number - 1]

    save_tasks(tasks)
    return undone_task

# ---- CLEAR ALL TASKS FOR ONE USER ----
def clear_tasks(user):
    tasks = load_tasks()

    if user not in tasks:
        return False

    del tasks[user]
    save_tasks(tasks)
    return True

# ---- Strike Text ----
def strike_text(text):
    return "".join(char + "\u0336" for char in text)

# ---- FORMAT TASKS FOR DISPLAY ----
# PURPOSE: Format tasks for Twitch chat and other text output
def format_tasks(user):
    user_tasks = get_tasks(user)

    # If no tasks exist, return a simple message
    if not user_tasks:
        return "No tasks found."

    # Store each formatted task line here
    lines = []

    # Loop through all tasks and format them
    for i, task in enumerate(user_tasks, start=1):

        # If the task is marked done, show it with a strike-through effect
        if task["done"]:
            lines.append(f"{i}. {strike_text(task['text'])}")

        # If the task is not done, show normal text
        else:
            lines.append(f"{i}. {task['text']}")

    # Join all tasks into one Twitch-friendly message
    return " | ".join(lines)