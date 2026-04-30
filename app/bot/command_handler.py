# Import the task functions from task_manager
from app.storage.task_manager import add_task, get_tasks, complete_task, clear_tasks, format_tasks, remove_task


# ---- FORMAT TASK LIST FOR CHAT ----
def format_task_list(user):

    task_text = format_tasks(user)

    if task_text == "No tasks found.":
        return f"{user} has no tasks."

    return f"{user}'s tasks: {task_text}"

# -----------------------------------------------------------
# FUNCTION: handle_command
# PURPOSE: Interpret a chat message and decide what to do
# -----------------------------------------------------------
def handle_command(user, message):

    # Remove extra spaces before and after the message
    message = message.strip()

    # Make the message lowercase for easier command matching
    lower_message = message.lower()
    
    # Ignore anything that is not a command
    if not message.startswith("!"):
        return None


    # -------------------------------------------------------
    # COMMAND: !addtask
    # Example: !addtask Edit video | Clean desk | Plan stream
    # -------------------------------------------------------
    if message.startswith("!addtask "):

        # Remove the command text and keep only the task text
        task_text = message[len("!addtask "):].strip()

        # Stop if the user did not actually include a task
        if not task_text:
            return "You need to provide a task."

        # Split multiple tasks using the | symbol
        raw_tasks = task_text.split("|")

        # Store cleaned tasks here
        cleaned_tasks = []

        # Remove extra spaces from each task
        for task in raw_tasks:
            cleaned_task = task.strip()

            # Only keep non-empty tasks
            if cleaned_task:
                cleaned_tasks.append(cleaned_task)

        # If no valid tasks remain, return an error message
        if not cleaned_tasks:
            return "You need to provide at least one valid task."

        # Add each cleaned task to the user's list
        for task in cleaned_tasks:
            add_task(user, task)

        # Return a different response for one task vs many tasks
        if len(cleaned_tasks) == 1:
            return f"Task added for {user}: {cleaned_tasks[0]}"

        return f"Added {len(cleaned_tasks)} tasks for {user}."


       # -------------------------------------------------------
    # COMMAND: !tasklist
    # PURPOSE: Show the user's current tasks
    # -------------------------------------------------------
    if lower_message == "!tasklist":
        return format_task_list(user)


    # -------------------------------------------------------
    # COMMAND TYPOS: !tasklist
    # PURPOSE: Catch common fast-typing mistakes for !tasklist
    # -------------------------------------------------------
    tasklist_typos = [
        "!tasklsit",
        "!taslkist",
        "!tasklst",
        "!tasklis",
        "!tasklits",
        "!tasklit",
        "!taskslist",
        "!tasklisk",
        "!tasklost",
        "!tasklust",
        "!taskliest",
        "!takslist",
        "!taklist",
        "!taslist",
        "!taskist",
        "!taskl",
        "!taskli",
        "!tasklisst",
        "!taskllist",
        "!taskklist",
        "!taasklist",
        "!tsklist",
        "!tastlist",
        "!tasklistt",
        "!tasjlist",
        "!tasklisr",
        "!tasklisg",
        "!tasklisf",
        "!tasklisd",
        "!tasklisu",
        "!tasklisi",
        "!taskliso",
    ]

    if lower_message in tasklist_typos:
        return "Did you mean !tasklist? you dyslexic bish"


    # -------------------------------------------------------
    # COMMAND: !done
    # Example: !done 2
    # PURPOSE: Mark one numbered task as complete
    # -------------------------------------------------------
    if lower_message.startswith("!done "):

        number_text = message[len("!done "):].strip()

        if not number_text.isdigit():
            return "Use !done followed by a task number."

        task_number = int(number_text)

        completed = complete_task(user, task_number)

        if completed is None:
            return "That task number does not exist."

        completed_text = completed.get("text", "task")
        return f"Completed task for {user}: {completed_text}"


    # -------------------------------------------------------
    # COMMAND: !clear
    # Example: !clear or !clear 3
    # PURPOSE: Clear either one task or the whole task list
    # -------------------------------------------------------
    if lower_message == "!clear" or lower_message.startswith("!clear "):

        print(f"DEBUG CLEAR COMMAND: user={user}, message={message}, lower_message={lower_message}")

        clear_text = message[len("!clear"):].strip()

        print(f"DEBUG CLEAR TEXT: clear_text={clear_text}")

        if not clear_text:

            cleared = clear_tasks(user)

            if not cleared:
                return f"{user} has no tasks to clear."

            return f"Cleared all tasks for {user}."

        if not clear_text.isdigit():
            return "Use !clear by itself to clear all tasks, or !clear followed by a task number."

        task_number = int(clear_text)

        removed = remove_task(user, task_number)

        print(f"DEBUG REMOVED TASK: removed={removed}")

        if removed is None:
            return "That task number does not exist."

        removed_text = removed.get("text", "task")

        return f"Cleared task {task_number} for {user}: {removed_text}"


    # -------------------------------------------------------
    # DEFAULT RESPONSE
    # PURPOSE: Catch unknown commands
    # -------------------------------------------------------
    return None