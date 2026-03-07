import os
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
#Where da fu is the project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#path to data folder
DATA_DIR = os.path.join(BASE_DIR, "data")

#path to task file
TASK_FILE = os.path.join(DATA_DIR, "task.json")

#test to make sure it exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    
# Ensure tasks.json exists
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