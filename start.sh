#!/bin/bash

# Portni tekshirish
PORT="${PORT:-8080}"
echo "🚀 Starting services on port $PORT..."

# Gunicorn orqali WebApp serverni Production rejimida ishga tushirish (Backgroundda)
# gunicorn webapp_server:app --bind 0.0.0.0:$PORT &
gunicorn webapp_server:app --bind 0.0.0.0:$PORT --daemon

# Botni ishga tushirish (Foregroundda - Render buni nazorat qiladi)
echo "🤖 Starting Telegram Bot..."
python3 bot.py
