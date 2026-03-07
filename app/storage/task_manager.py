import os
import json

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