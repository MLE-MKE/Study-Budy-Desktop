import socket
import urllib.request
import os
from app.bot.command_handler import handle_command

SERVER = "irc.chat.twitch.tv"
PORT = 6667 

# Configuration is supplied at runtime. Never store a Twitch token in source code.
BOT_NICK = os.getenv("STUDY_BUDY_TWITCH_BOT_NICK", "")
TOKEN = os.getenv("STUDY_BUDY_TWITCH_TOKEN", "")
CHANNEL = os.getenv("STUDY_BUDY_TWITCH_CHANNEL", "")

def send_message(sock, message):
    sock.send(f"PRIVMSG {CHANNEL} :{message}\r\n".encode("utf-8"))
    
def parse_message(raw_message):
    """
    Extract username and chat message from a Twitch IRC message.
    """
    try:
        prefix, command_part = raw_message.split(" PRIVMSG ", 1)
        username = prefix.split("!", 1)[0][1:]
        channel_part, message = command_part.split(" :", 1)
        return username, message.strip()
    except ValueError:
        return None, None  
    
def run_bot():
    if not BOT_NICK or not TOKEN or not CHANNEL:
        raise RuntimeError(
            "Twitch is not configured. Use the Study Budy Connections screen or "
            "set the STUDY_BUDY_TWITCH_* environment variables for development."
        )

    sock = socket.socket()
    sock.connect((SERVER, PORT))

    sock.send(f"PASS {TOKEN}\r\n".encode("utf-8"))
    sock.send(f"NICK {BOT_NICK}\r\n".encode("utf-8"))
    sock.send(f"JOIN {CHANNEL}\r\n".encode("utf-8"))

    print(f"Connected to {CHANNEL} as {BOT_NICK}")

    while True:
        response = sock.recv(2048).decode("utf-8", errors="ignore")

        if response.startswith("PING"):
            sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
            continue

        for line in response.split("\r\n"):
            if not line:
                continue

            print(line)

            if "PRIVMSG" in line:
                username, message = parse_message(line)

                if not username or not message:
                    continue

                reply = handle_command(username, message)

                # ---- SET OVERLAY PRIORITY WHEN TASK LIST IS REQUESTED ----
                # PURPOSE: Tell the Flask overlay server which user's tasks should appear first
                # NOTE: This IP should match the computer running app.py
                if message.strip().lower() == "!tasklist":
                    try:
                        urllib.request.urlopen(f"http://127.0.0.1:5000/overlay_priority/{username}")
                    except Exception as error:
                        print(f"Error setting overlay priority: {error}")

                if reply:
                    send_message(sock, reply)

if __name__ == "__main__":
    run_bot()
