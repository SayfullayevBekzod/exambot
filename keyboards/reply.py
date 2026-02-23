from telegram import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard():
    """Asosiy menyu tugmalari"""
    keyboard = [
        [KeyboardButton("📚 Bo'limlar"), KeyboardButton("📝 Test boshlash")],
        [KeyboardButton("📊 Natijalarim"), KeyboardButton("🏆 Reyting")],
        [KeyboardButton("❌ Xatolarim"), KeyboardButton("🏅 Yutuqlar")],
        [KeyboardButton("💡 Kunlik so'z"), KeyboardButton("📖 Tips")],
        [KeyboardButton("✍️ Writing"), KeyboardButton("🎧 Audio Test")],
        [KeyboardButton("🗂️ Flashcards"), KeyboardButton("🧠 Takrorlash")],
        [KeyboardButton("📅 Study Plan"), KeyboardButton("🎮 Speed Round")],
        [KeyboardButton("📊 Sertifikat"), KeyboardButton("👑 Premium")],
        [KeyboardButton("🌐 Tarjima"), KeyboardButton("🔔 Eslatma")],
        [KeyboardButton("👥 Challenge"), KeyboardButton("🎤 Speaking")],
        [KeyboardButton("⚙️ Admin"), KeyboardButton("ℹ️ Yordam")],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        input_field_placeholder="Tugmani tanlang..."
    )
