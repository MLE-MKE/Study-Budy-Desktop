from app.bot.command_handler import handle_command
from app.storage.task_manager import TASK_FILE

user = "Emily"

print("Task file is:")
print(TASK_FILE)
print()

print(handle_command(user, "!addtask Edit video"))
print(handle_command(user, "!addtask Clean desk"))
print(handle_command(user, "!addtask Plan stream"))

print()
print("Current tasks:")
print(handle_command(user, "!tasklist"))

print()
print(handle_command(user, "!done 2"))

print()
print("Tasks after completion:")
print(handle_command(user, "!tasklist"))