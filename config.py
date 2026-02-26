import os
from dotenv import load_dotenv

load_dotenv()

# Bot sozlamalari
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Click to'lov tizimi
CLICK_PROVIDER_TOKEN = os.getenv("CLICK_PROVIDER_TOKEN", "")

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    # SQLAlchemy requires postgresql:// instead of postgres:// if copied from some providers
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    DB_URL = DATABASE_URL
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "exam_bot.db")
    DB_URL = f"sqlite:///{DB_PATH}"

# Admin foydalanuvchilar (Telegram user ID)
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# To'lov ma'lumotlari
PAYMENT_CARD_NUMBER = os.getenv("PAYMENT_CARD_NUMBER", "9860350147502123")
PAYMENT_CARD_HOLDER = os.getenv("PAYMENT_CARD_HOLDER", "Sayfullayev Bekzod")

# Quiz sozlamalari
QUESTIONS_PER_QUIZ = 10  # Har bir testda savollar soni
TIME_PER_QUESTION = 30   # Har bir savol uchun vaqt (soniya)

# Premium narxlar (so'm)
PREMIUM_PLANS = {
    "1_month": {"duration": 30, "price": 29900, "label": "1 oy", "emoji": "📅"},
    "3_months": {"duration": 90, "price": 69900, "label": "3 oy", "emoji": "📆"},
    "6_months": {"duration": 180, "price": 119900, "label": "6 oy", "emoji": "🗓️"},
}

