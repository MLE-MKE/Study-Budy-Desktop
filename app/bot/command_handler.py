from app.storage.task_manager import add_task, get_tasks, complete_task


# ---- GET TASK AND CTAHC IF EMPTY ---
def format_task_list(user):
    tasks = get_tasks(user)

    if not tasks:
        return f"{user} has no tasks."

    lines = []
    for i, task in enumerate(tasks, start=1):
        lines.append(f"{i}. {task}")

    return "\n".join(lines)

# ---- CHAT COMMANDS ----
def handle_command(user, message):
    message = message.strip()

    if not message.startswith("!"):
        return None

    if message.startswith("!addtask "):
        task_text = message[len("!addtask "):].strip()

        if not task_text:
            return "You need to provide a task."

        add_task(user, task_text)
        return f"Task added for {user}: {task_text}"

    if message == "!tasklist":
        return format_task_list(user)

    if message.startswith("!done "):
        number_text = message[len("!done "):].strip()

        if not number_text.isdigit():
            return "Use !done followed by a task number."

        task_number = int(number_text)
        completed = complete_task(user, task_number)

        if completed is None:
            return "That task number does not exist."

        return f"Completed task for {user}: {completed}"

    return "Unknown command."