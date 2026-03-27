import socket
from app.bot.command_handler import handle_command

SERVER = "irc.chat.twitch.tv"
PORT = 6667 

#leave commments in for other streamers but take this one out when you package it okay
#DONT FORGET THAT OKAY 
BOT_NICK = "killer_queens_jester"      #replace with your bot username
TOKEN = "oauth:kz619kjicoixwvyqvaq9wz828yk1g0"  # Replace with your Twitch OAuth token
CHANNEL = "#killer_queen55"  # Replace with your Twitch channel

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

                if reply:
                    send_message(sock, reply)


if __name__ == "__main__":
    run_bot()