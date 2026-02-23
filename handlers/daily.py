"""Daily test, daily word, reminders"""
import json
import os
import random
from datetime import datetime, time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, JobQueue

from database import get_session, Subject, Question, UserSettings, DailyStreak


def _load_daily_words():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "daily_words.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f).get("words", [])


# === Daily Word ===

async def daily_word_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/kunlik_soz buyrug'i"""
    words = _load_daily_words()
    if not words:
        await update.message.reply_text("❌ So'zlar topilmadi!")
        return

    # Bugungi kunning raqamiga qarab so'z tanlash
    day_index = datetime.now().timetuple().tm_yday % len(words)
    word = words[day_index]

    text = (
        f"💡 <b>Bugungi IELTS so'z</b>\n\n"
        f"🔤 <b>{word['word']}</b>\n"
        f"📖 Ma'nosi: <i>{word['meaning']}</i>\n\n"
        f"📝 Misol: <i>{word['example']}</i>\n\n"
        f"🔄 Sinonimlari: <code>{word['synonym']}</code>\n\n"
        f"💪 Bu so'zni bugun 3 marta ishlatib ko'ring!"
    )

    keyboard = [
        [InlineKeyboardButton("🎲 Tasodifiy so'z", callback_data="random_word")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
    ]
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def random_word_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tasodifiy so'z"""
    query = update.callback_query
    await query.answer()

    words = _load_daily_words()
    word = random.choice(words)

    text = (
        f"💡 <b>Tasodifiy IELTS so'z</b>\n\n"
        f"🔤 <b>{word['word']}</b>\n"
        f"📖 Ma'nosi: <i>{word['meaning']}</i>\n\n"
        f"📝 Misol: <i>{word['example']}</i>\n\n"
        f"🔄 Sinonimlari: <code>{word['synonym']}</code>"
    )

    keyboard = [
        [InlineKeyboardButton("🎲 Yana boshqa so'z", callback_data="random_word")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
    ]
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


# === Reminders ===

async def reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/eslatma buyrug'i"""
    user_id = update.effective_user.id
    session = get_session()
    try:
        settings = session.query(UserSettings).filter_by(user_id=user_id).first()
        status = "✅ Yoqilgan" if settings and settings.reminder_enabled else "❌ O'chirilgan"

        keyboard = [
            [InlineKeyboardButton("✅ Eslatmani yoqish", callback_data="reminder_on")],
            [InlineKeyboardButton("❌ Eslatmani o'chirish", callback_data="reminder_off")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
        ]
        await update.message.reply_text(
            f"🔔 <b>Kundalik eslatma</b>\n\n"
            f"Holati: {status}\n\n"
            f"Bot sizga har kuni ertalab test yechishni eslatadi.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    finally:
        session.close()


async def reminder_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Eslatmani yoqish/o'chirish"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    action = query.data.replace("reminder_", "")
    enable = action == "on"

    session = get_session()
    try:
        settings = session.query(UserSettings).filter_by(user_id=user_id).first()
        if not settings:
            settings = UserSettings(user_id=user_id)
            session.add(settings)

        settings.reminder_enabled = enable
        settings.daily_word_enabled = enable
        settings.daily_test_enabled = enable
        session.commit()

        if enable:
            text = (
                "✅ <b>Eslatma yoqildi!</b>\n\n"
                "Har kuni sizga:\n"
                "📅 Kundalik test\n"
                "💡 Yangi IELTS so'z\n"
                "🔔 Eslatma xabari\n\nyuboriladi!"
            )
        else:
            text = "❌ <b>Eslatma o'chirildi.</b>\n\nIstagan vaqt qayta yoqishingiz mumkin."

        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")]]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()


# === Scheduled Jobs ===

async def send_daily_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Har kunlik eslatma (JobQueue orqali chaqiriladi)"""
    session = get_session()
    try:
        users = session.query(UserSettings).filter_by(reminder_enabled=True).all()
        words = _load_daily_words()
        day_index = datetime.now().timetuple().tm_yday % len(words)
        word = words[day_index] if words else None

        for user in users:
            try:
                # Eslatma
                text = "🔔 <b>Kundalik eslatma!</b>\n\nBugun IELTS test yechdingizmi? 📝\n\n"

                if word:
                    text += (
                        f"💡 <b>Bugungi so'z:</b> <b>{word['word']}</b>\n"
                        f"📖 {word['meaning']}\n"
                        f"📝 <i>{word['example']}</i>\n\n"
                    )

                text += "Testni boshlash uchun /bolimlar ni bosing!"

                await context.bot.send_message(
                    chat_id=user.user_id,
                    text=text,
                    parse_mode="HTML",
                )
            except Exception:
                pass
    finally:
        session.close()


def setup_daily_jobs(job_queue: JobQueue):
    """Kundalik joblarni o'rnatish"""
    # Har kuni ertalab 9:00 da eslatma
    job_queue.run_daily(
        send_daily_reminders,
        time=time(hour=4, minute=0),  # UTC 4:00 = UZT 9:00
        name="daily_reminders",
    )
