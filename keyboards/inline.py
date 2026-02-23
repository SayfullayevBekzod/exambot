from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_session, Subject


def subjects_keyboard():
    """Fanlar ro'yxati uchun inline keyboard"""
    session = get_session()
    try:
        subjects = session.query(Subject).order_by(Subject.name).all()
        keyboard = []
        row = []
        for i, subj in enumerate(subjects):
            btn = InlineKeyboardButton(
                text=f"{subj.emoji} {subj.name}",
                callback_data=f"subject_{subj.id}"
            )
            row.append(btn)
            if len(row) == 2 or i == len(subjects) - 1:
                keyboard.append(row)
                row = []
        return InlineKeyboardMarkup(keyboard) if keyboard else None
    finally:
        session.close()


def answer_keyboard(question_id):
    """A/B/C/D javob tugmalari — faqat harf ko'rsatiladi"""
    keyboard = [[
        InlineKeyboardButton("🅰️ A", callback_data=f"answer_{question_id}_a"),
        InlineKeyboardButton("🅱️ B", callback_data=f"answer_{question_id}_b"),
        InlineKeyboardButton("🅲 C", callback_data=f"answer_{question_id}_c"),
        InlineKeyboardButton("🅳 D", callback_data=f"answer_{question_id}_d"),
    ]]
    return InlineKeyboardMarkup(keyboard)


def back_to_subjects_keyboard():
    """Orqaga qaytish tugmasi"""
    keyboard = [[
        InlineKeyboardButton("🔙 Fanlar ro'yxatiga", callback_data="back_subjects")
    ]]
    return InlineKeyboardMarkup(keyboard)


def quiz_complete_keyboard():
    """Test tugagandan keyin tugmalar"""
    keyboard = [
        [InlineKeyboardButton("📊 Natijalarim", callback_data="my_stats")],
        [InlineKeyboardButton("🏆 Reyting", callback_data="leaderboard")],
        [InlineKeyboardButton("🔄 Yana test yechish", callback_data="back_subjects")],
    ]
    return InlineKeyboardMarkup(keyboard)
