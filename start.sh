#!/bin/bash
# Start the web server in the background
python webapp_server.py &

# Start the bot
python bot.py
