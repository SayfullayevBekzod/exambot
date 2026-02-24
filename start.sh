#!/bin/bash

# Ensure we have the right port
PORT="${PORT:-8080}"
echo "🚀 Starting services on port $PORT..."

# Use gunicorn to run the web server in the background
# We don't use --daemon here to let the shell manage it 
# but we append & to put it in background
gunicorn webapp_server:app --bind 0.0.0.0:$PORT &

# Wait a bit for the port to bind
sleep 5

# Start the bot as the primary foreground process
echo "🤖 Starting Telegram Bot..."
python3 bot.py
