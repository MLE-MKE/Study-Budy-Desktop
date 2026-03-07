# Import the task functions we already built in task_manager
# These handle reading/writing the JSON task file
from app.storage.task_manager import add_task, get_tasks, complete_task


# -----------------------------------------------------------
# FUNCTION: format_task_list
# PURPOSE: Convert a user's tasks into a numbered list string
# -----------------------------------------------------------
def format_task_list(user):

    # Get the list of tasks for this user
    tasks = get_tasks(user)

    # If the user has no tasks yet, return a message
    if not tasks:
        return f"{user} has no tasks."

    # This list will hold each numbered line
    lines = []

    # Loop through tasks and number them starting at 1
    for i, task in enumerate(tasks, start=1):
        lines.append(f"{i}. {task}")

    # Join the numbered lines into a single string
    return "\n".join(lines)


# -----------------------------------------------------------
# FUNCTION: handle_command
# PURPOSE: Interpret a chat message and decide what to do
# -----------------------------------------------------------
def handle_command(user, message):

    # Remove any accidental spaces before/after message
    message = message.strip()

    # If the message doesn't start with "!" then ignore it
    if not message.startswith("!"):
        return None


    # -------------------------------------------------------
    # COMMAND: !addtask
    # Example: !addtask Edit video | Clean desk | Plan stream
    # -------------------------------------------------------
    if message.startswith("!addtask "):

        # Remove the command portion from the message
        task_text = message[len("!addtask "):].strip()

        # If the user typed !addtask but didn't include a task
        if not task_text:
            return "You need to provide a task."

        # Split the message into multiple tasks using "|"
        raw_tasks = task_text.split("|")

        # This will store the cleaned tasks
        cleaned_tasks = []

        # Loop through each piece and clean whitespace
        for task in raw_tasks:
            cleaned_task = task.strip()

            # Only keep tasks that actually contain text
            if cleaned_task:
                cleaned_tasks.append(cleaned_task)

        # If nothing valid was provided
        if not cleaned_tasks:
            return "You need to provide at least one valid task."

        # Add each task to the user's task list
        for task in cleaned_tasks:
            add_task(user, task)

        # If only one task was added, return a specific message
        if len(cleaned_tasks) == 1:
            return f"Task added for {user}: {cleaned_tasks[0]}"

        # If multiple tasks were added
        return f"Added {len(cleaned_tasks)} tasks for {user}."


    # -------------------------------------------------------
    # COMMAND: !tasklist
    # Shows the user's current tasks
    # -------------------------------------------------------
    if message == "!tasklist":
        return format_task_list(user)


    # -------------------------------------------------------
    # COMMAND: !done
    # Example: !done 2
    # Marks a numbered task as complete
    # -------------------------------------------------------
    if message.startswith("!done "):

        # Extract the number after !done
        number_text = message[len("!done "):].strip()

        # If the user didn't give a number
        if not number_text.isdigit():
            return "Use !done followed by a task number."

        # Convert text to an integer
        task_number = int(number_text)

        # Attempt to complete that task
        completed = complete_task(user, task_number)

        # If the task number doesn't exist
        if completed is None:
            return "That task number does not exist."

        # Return confirmation message
        return f"Completed task for {user}: {completed}"



    # -------------------------------------------------------
    # DEFAULT RESPONSE
    # If the command wasn't recognized
    # -------------------------------------------------------
    return "Unknown command."