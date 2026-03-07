from app.storage.task_manager import TASK_FILE

print("task file is:")
print(TASK_FILE)


from app.storage.task_manager import add_task, get_tasks, complete_task

print("Adding tasks...")
add_task("Emily", "Edit video")
add_task("Emily", "Clean desk")
add_task("Emily", "Plan stream")

print("Emily's tasks:")
print(get_tasks("Emily"))

print("Completing task 2...")
completed = complete_task("Emily", 2)
print("Completed:", completed)

print("Emily's tasks now:")
print(get_tasks("Emily"))