from app.storage.task_manager import TASK_FILE

print("task file is:")
print(TASK_FILE)

from app.storage.task_manager import TASK_FILE, load_tasks, save_tasks



tasks = load_tasks()

tasks["Emily"] = ["Test task"]

save_tasks(tasks)

print(load_tasks())