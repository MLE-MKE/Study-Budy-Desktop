# Import the task functions from task_manager
from app.storage.task_manager import add_task, get_tasks, complete_task, clear_tasks, format_tasks, remove_task

# ---- USERS ALLOWED TO CLEAR OTHER USERS TASKS ----
# what this section does: only these usernames can clear someone else's task list
ALLOWED_CLEAR_USERS = [
    "killer_queen55",
    "killer_queens_jester",
    # "mod_username_here",
]

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
    # Example: !clear 3, !clear all, or !clear @username
    # PURPOSE: Clear one task, my whole list, or another user's list if I am allowed
    # -------------------------------------------------------
    if lower_message == "!clear" or lower_message.startswith("!clear "):

        # Pull anything typed after !clear
        clear_text = message[len("!clear"):].strip()

        # Make a lowercase copy so commands are easier to compare
        clear_text_lower = clear_text.lower()

        # Normalize the person who typed the command
        command_user = user.lower()

        # If no number or target was given, do NOT clear everything by accident
        if not clear_text:
            return "Use !clear 3 to clear one task, !clear all to clear your list, or !clear @user if you are allowed."

        # -------------------------------------------------------
        # COMMAND: !clear @username
        # PURPOSE: Let only approved users clear another user's whole list
        # -------------------------------------------------------
        if clear_text.startswith("@"):

            # Stop regular viewers from clearing other people's task lists
            if command_user not in ALLOWED_CLEAR_USERS:
                return "Only the streamer or mods can clear another user's tasks."

            # Remove the @ symbol and clean the username
            target_user = clear_text[1:].strip().lower()

            # Stop if someone typed only !clear @
            if not target_user:
                return "Use !clear @username to clear another user's tasks."

            # Clear that user's whole task list
            cleared = clear_tasks(target_user)

            # If that user had no tasks stored
            if not cleared:
                return f"{target_user} has no tasks to clear."

            # Success response
            return f"Cleared all tasks for {target_user}."

        # -------------------------------------------------------
        # COMMAND: !clear all
        # PURPOSE: Clear my own whole task list only when I clearly type all
        # -------------------------------------------------------
        if clear_text_lower == "all":

            # Clear the command user's full task list
            cleared = clear_tasks(user)

            # If the user had no tasks stored
            if not cleared:
                return f"{user} has no tasks to clear."

            # Success response
            return f"Cleared all tasks for {user}."

        # -------------------------------------------------------
        # COMMAND: !clear 3
        # PURPOSE: Clear one task from my own task list
        # -------------------------------------------------------
        if clear_text.isdigit():

            # Convert the task number text into an integer
            task_number = int(clear_text)

            # Remove only the chosen task
            removed = remove_task(user, task_number)

            # If the task number does not exist, do not crash the bot
            if removed is None:
                return "That task number does not exist."

            # Pull only the task text out of the dictionary
            removed_text = removed.get("text", "task")

            # Success response for clearing one task
            return f"Cleared task {task_number} for {user}: {removed_text}"

        # If the command did not match any clear format, explain the correct options
        return "Use !clear 3, !clear all, or !clear @username if you are allowed."
    
    # -------------------------------------------------------
    # DEFAULT RESPONSE
    # PURPOSE: Catch unknown commands
    # -------------------------------------------------------
    return None