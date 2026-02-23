"""Flashcards — so'z kartochkalari"""
import json
import os
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_session, Flashcard


def _load_default_cards():
    """Default kartochkalarni yuklash"""
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "daily_words.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f).get("words", [])


async def flashcards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/flashcards buyrug'i"""
    from handlers.payment import require_premium
    if not await require_premium(update, "🗂️ Flashcards"):
        return
    user_id = update.effective_user.id
    session = get_session()
    try:
        total = session.query(Flashcard).filter_by(user_id=user_id).count()
        mastered = session.query(Flashcard).filter_by(user_id=user_id, mastered=True).count()
        learning = total - mastered

        keyboard = [
            [InlineKeyboardButton("🎴 Kartochka ko'rish", callback_data="fc_study")],
            [InlineKeyboardButton("➕ Default kartalar yuklash", callback_data="fc_load_defaults")],
            [InlineKeyboardButton("📊 Statistika", callback_data="fc_stats")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
        ]

        await update.message.reply_text(
            f"🗂️ <b>Flashcards</b>\n\n"
            f"📊 Jami kartalar: <b>{total}</b>\n"
            f"📗 O'rganilgan: <b>{mastered}</b>\n"
            f"📙 O'rganilmoqda: <b>{learning}</b>\n\n"
            f"Kartochkalarni ko'rish va o'rganish uchun bosing:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    finally:
        session.close()


async def load_defaults_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Default kartalarni yuklash"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    session = get_session()
    try:
        existing = session.query(Flashcard).filter_by(user_id=user_id).count()
        if existing > 0:
            await query.edit_message_text(
                "✅ Kartalar allaqachon yuklangan!\n\n"
                "🎴 Kartochka ko'rish uchun quyidagini bosing:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎴 Boshlash", callback_data="fc_study")
                ]]),
            )
            return

        words = _load_default_cards()
        for w in words:
            card = Flashcard(
                user_id=user_id,
                front=w["word"],
                back=w["meaning"],
                example=w.get("example", ""),
                category="vocabulary",
            )
            session.add(card)
        session.commit()

        await query.edit_message_text(
            f"✅ <b>{len(words)}</b> ta kartochka yuklandi!\n\n"
            f"🎴 Kartochka ko'rish uchun bosing:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🎴 Boshlash", callback_data="fc_study")
            ]]),
        )
    finally:
        session.close()


async def study_flashcard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kartochka ko'rsatish"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    session = get_session()
    try:
        # O'rganilmagan kartalardan tasodifiy
        cards = session.query(Flashcard).filter_by(user_id=user_id, mastered=False).all()
        if not cards:
            cards = session.query(Flashcard).filter_by(user_id=user_id).all()

        if not cards:
            await query.edit_message_text(
                "❌ Kartalar topilmadi! Avval kartalar yuklang.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Yuklash", callback_data="fc_load_defaults")
                ]]),
            )
            return

        card = random.choice(cards)
        context.user_data["current_flashcard_id"] = card.id

        text = (
            f"🎴 <b>Flashcard</b>\n\n"
            f"🔤 <b>{card.front}</b>\n\n"
            f"❓ Ma'nosini bilasizmi?\n\n"
            f"👇 Ko'rish uchun bosing:"
        )

        keyboard = [
            [InlineKeyboardButton("👀 Javobni ko'rish", callback_data=f"fc_reveal_{card.id}")],
            [InlineKeyboardButton("⏭️ Keyingi", callback_data="fc_study")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
        ]

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()


async def reveal_flashcard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kartochka javobini ko'rsatish"""
    query = update.callback_query
    await query.answer()

    card_id = int(query.data.split("_")[2])
    session = get_session()
    try:
        card = session.query(Flashcard).get(card_id)
        if not card:
            await query.edit_message_text("❌ Kartochka topilmadi!")
            return

        text = (
            f"🎴 <b>Flashcard</b>\n\n"
            f"🔤 <b>{card.front}</b>\n\n"
            f"📖 <b>Ma'nosi:</b> {card.back}\n"
        )
        if card.example:
            text += f"📝 <b>Misol:</b> <i>{card.example}</i>\n"

        text += "\n❓ Bilganmi edingiz?"

        keyboard = [
            [
                InlineKeyboardButton("✅ Bildim", callback_data=f"fc_knew_{card.id}"),
                InlineKeyboardButton("❌ Bilmadim", callback_data=f"fc_didnt_{card.id}"),
            ],
            [InlineKeyboardButton("⏭️ Keyingi", callback_data="fc_study")],
        ]

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()


async def flashcard_response_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bildim/Bilmadim javob"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    knew = parts[1] == "knew"
    card_id = int(parts[2])

    session = get_session()
    try:
        card = session.query(Flashcard).get(card_id)
        if card and knew:
            card.mastered = True
            session.commit()

        if knew:
            text = "✅ <b>Ajoyib!</b> Kartochka o'rganildi deb belgilandi.\n\n⏭️ Keyingisiga o'tamiz!"
        else:
            text = "📖 Xavotir olmang, mashq qilsangiz o'rganasiz!\n\n⏭️ Keyingisiga o'tamiz!"

        keyboard = [
            [InlineKeyboardButton("🎴 Keyingi kartochka", callback_data="fc_study")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
        ]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()


async def flashcard_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Flashcard statistikasi"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    session = get_session()
    try:
        total = session.query(Flashcard).filter_by(user_id=user_id).count()
        mastered = session.query(Flashcard).filter_by(user_id=user_id, mastered=True).count()
        learning = total - mastered
        pct = (mastered / total * 100) if total > 0 else 0

        filled = round(10 * pct / 100)
        bar = "🟩" * filled + "⬜" * (10 - filled)

        text = (
            f"🗂️ <b>Flashcard Statistika</b>\n\n"
            f"📊 Jami: <b>{total}</b>\n"
            f"✅ O'rganilgan: <b>{mastered}</b>\n"
            f"📙 O'rganilmoqda: <b>{learning}</b>\n\n"
            f"[{bar}] {pct:.0f}%"
        )
        keyboard = [
            [InlineKeyboardButton("🎴 Davom etish", callback_data="fc_study")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
        ]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()
