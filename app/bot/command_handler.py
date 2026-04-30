# Import the task functions from task_manager
from app.storage.task_manager import add_task, get_tasks, complete_task, clear_tasks, format_tasks


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
    if message == "!tasklist":
        return format_task_list(user)
    
    
    # -------------------------------------------------------
    # COMMAND TYPOS: !tasklist
    # PURPOSE: Catch common fast-typing mistakes for !tasklist
    # -------------------------------------------------------

    # Make the command lowercase so !Tasklist and !TASKLIST still work
    lower_message = message.lower()
    
    # These are common ways someone might misspell !tasklist while typing fast
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
        "!tasklisy",
        "!tasklisy",
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
        "!tasklisy",
        "!tasklisy",
        "!tasklistt",
        "!tasklisy",
        "!tasjlist",
        "!tasklisr",
        "!tasklisg",
        "!tasklisf",
        "!tasklisd",
        "!tasklisy",
        "!tasklisu",
        "!tasklisi",
        "!taskliso",
    ]

    # If someone types a typo, tell them the correct command
    if message.lower() in tasklist_typos:
        return "Did you mean !tasklist? you dyslexic bish"


        # -------------------------------------------------------
    # COMMAND: !done
    # Example: !done 2
    # PURPOSE: Mark one numbered task as complete
    # -------------------------------------------------------
    if message.startswith("!done "):

        # Pull the number after !done
        number_text = message[len("!done "):].strip()

        # Make sure the user entered a number
        if not number_text.isdigit():
            return "Use !done followed by a task number."

        # Convert the number text into an integer
        task_number = int(number_text)

        # Mark that task as done
        completed = complete_task(user, task_number)

        # If the task number was invalid
        if completed is None:
            return "That task number does not exist."

        # Return the completed task text without printing the whole dictionary
        completed_text = completed.get("text", "task")
        return f"Completed task for {user}: {completed_text}"
    
    
    # -------------------------------------------------------
    # COMMAND: !clear
    # PURPOSE: Remove all tasks for this user
    # -------------------------------------------------------
    if message == "!clear":

        # Try to clear all tasks for the user
        cleared = clear_tasks(user)

        # If the user had no tasks stored
        if not cleared:
            return f"{user} has no tasks to clear."
  
        # Success response
        return f"Cleared all tasks for {user}."


    # -------------------------------------------------------
    # DEFAULT RESPONSE
    # PURPOSE: Catch unknown commands
    # -------------------------------------------------------
    return None