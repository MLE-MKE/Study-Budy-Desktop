import os
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# go from app/storage → app → project root
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))

# path to data folder
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# path to tasks file
TASK_FILE = os.path.join(DATA_DIR, "tasks.json")

# ensure data folder exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# ensure tasks.json exists
if not os.path.exists(TASK_FILE):
    with open(TASK_FILE, "w") as f:
        json.dump({}, f)
        
# ----- LOAD TASK DEFINITION ----
def load_tasks():
    with open(TASK_FILE, "r") as f:
        tasks = json.load(f)
    return tasks 

# ----SAVE TASK DEFINITION ----
def save_tasks(tasks):
    with open(TASK_FILE, "w") as f:
        json.dump(tasks, f, indent=4)

# ----GET TASK----        
def get_tasks(user):
    tasks = load_tasks()
    return tasks.get(user, [])

# ----ADD TASK----
def add_task(user, task):
    tasks = load_tasks()

    if user not in tasks:
        tasks[user] = []

    tasks[user].append(task)
    save_tasks(tasks)

    return tasks[user]

# ---- COMPLETE TASK ----
def complete_task(user, task_number):
    tasks = load_tasks()

    if user not in tasks:
        return None

    if task_number < 1 or task_number > len(tasks[user]):
        return None

    completed_task = tasks[user].pop(task_number - 1)

    save_tasks(tasks)

    return completed_task

# ---- NO TASK FOUND CATCH ----
def format_tasks(user):
    user_tasks = get_tasks(user)

    if not user_tasks:
        return "No tasks found."

    lines = []
    for i, task in enumerate(user_tasks, start=1):
        lines.append(f"{i}. {task}")

    return "\n".join(lines)