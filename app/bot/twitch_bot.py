import socket
from app.bot.command_handler import handle_command

SERVER = "irc.chat.twitch.tv"
PORT = 6667 

#leave commments in for other streamers but take this one out when you package it okay
#DONT FORGET THAT OKAY 
BOT_NICK = "killer_queens_jester"      #replace with your bot username
TOKEN = "oauth:kz619kjicoixwvyqvaq9wz828yk1g0"  # Replace with your Twitch OAuth token
CHANNEL = "#killer_queen55"  # Replace with your Twitch channel