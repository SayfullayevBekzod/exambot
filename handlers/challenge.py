"""Do'stlar bilan raqobat — Challenge tizimi"""
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_session, Subject, UserResult
from sqlalchemy import func, desc


async def challenge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/challenge buyrug'i"""
    session = get_session()
    try:
        subjects = session.query(Subject).all()
        if not subjects:
            await update.message.reply_text("❌ Bo'limlar topilmadi!")
            return

        text = (
            "👥 <b>Do'stni challenge qilish</b>\n\n"
            "Do'stingizga bu botni ulashing va kim ko'proq ball olishini ko'ring!\n\n"
            "📊 <b>Solishtirish uchun:</b>\n"
            "Har ikkalangiz bir xil bo'limdan test yeching va /reyting orqali natijalarni solishtiring.\n\n"
            "📎 <b>Botni ulashish:</b>\n"
        )

        # Bot username olish
        bot_info = await context.bot.get_me()
        share_url = f"https://t.me/{bot_info.username}"
        share_text = "🎓 IELTS Preparation Bot bilan birga tayyorlanamiz! Qani, kim ko'proq ball oladi?"

        keyboard = [
            [InlineKeyboardButton("📤 Do'stga yuborish", url=f"https://t.me/share/url?url={share_url}&text={share_text}")],
            [InlineKeyboardButton("🏆 Reyting ko'rish", callback_data="leaderboard")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
        ]
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        session.close()
