from telegram import Update
from telegram.ext import ContextTypes

from database import get_session, Subject
from keyboards.inline import subjects_keyboard
from keyboards.reply import main_menu_keyboard


WELCOME_TEXT = """
🎓 <b>IELTS Preparation Bot</b>ga xush kelibsiz!

IELTS imtihoniga tayyorlanish uchun eng yaxshi bot.

📚 <b>Asosiy imkoniyatlar:</b>
📝 5 ta bo'lim — Reading, Listening, Grammar, Vocabulary, Speaking
🎯 3 qiyinlik darajasi — Easy, Medium, Hard
📋 Mock Test — 40 savollik to'liq simulyatsiya
⏱️ Timer — har bir savol uchun 30 soniya
❌ Xatolar mashqi — noto'g'ri javoblarni qayta yechish
📈 Band Score tracker — natijalar tarixi
🏅 12 ta achievement — yutuqlar tizimi

🌟 <b>Premium imkoniyatlar:</b>
🎧 Audio Listening — eshitib tushunish mashqlari
📊 PDF Sertifikat — natijani PDF sifatida yuklab olish
🧠 Spaced Repetition — ilmiy takrorlash tizimi (SM-2)
🗂️ Flashcards — so'z kartochkalari
📅 Study Plan — 30/60/90 kunlik shaxsiy reja
🎮 Speed Round — tezlik raqobati
🌐 Tarjima rejimi — savollarni o'zbekchada ko'rish
👑 Premium obuna — barcha funksiyalar

Quyidagi bo'limlardan birini tanlang! 👇
"""

HELP_TEXT = """
ℹ️ <b>IELTS Preparation Bot — Yordam</b>

📋 <b>Buyruqlar:</b>
• /start — Bosh sahifa
• /bolimlar — IELTS bo'limlari
• /natijalarim — Shaxsiy natijalar
• /reyting — Top 10 reyting
• /xatolar — Xatolarni qayta yechish
• /yutuqlar — Achievement badges
• /kunlik_soz — Bugungi IELTS so'z
• /tips — Tips & Tricks
• /writing — Writing bo'limi
• /audio — Audio listening test
• /sertifikat — PDF sertifikat olish
• /takrorlash — Spaced repetition
• /flashcards — So'z kartochkalari
• /reja — Study plan
• /speed — Speed round
• /tarjima — Tarjima rejimi
• /premium — Premium obuna
• /webapp — Mini App
• /challenge — Do'stni challenge qilish
• /eslatma — Kundalik eslatma
• /help — Yordam

🏆 <b>IELTS Band tizimi:</b>
• 90-100% → Band 8.0-9.0 🏆
• 75-89%  → Band 6.5-7.5 🥇
• 60-74%  → Band 5.5-6.0 🥈
• 40-59%  → Band 4.5-5.0 🥉
• 0-39%   → Band 3.0-4.0 📖
"""

NO_SUBJECTS_TEXT = "\n😔 Hozircha bo'limlar qo'shilmagan."


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⌨️ Menyu tayyor!", reply_markup=main_menu_keyboard())
    kb = subjects_keyboard()
    if kb:
        await update.message.reply_text(WELCOME_TEXT, parse_mode="HTML", reply_markup=kb)
    else:
        await update.message.reply_text(WELCOME_TEXT + NO_SUBJECTS_TEXT, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="HTML")


async def subjects_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = subjects_keyboard()
    if kb:
        await update.message.reply_text(
            "📚 <b>IELTS bo'limlari:</b>\n\nBo'limni tanlang va testni boshlang! 👇",
            parse_mode="HTML", reply_markup=kb,
        )
    else:
        await update.message.reply_text(NO_SUBJECTS_TEXT, parse_mode="HTML")


async def back_to_subjects_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    kb = subjects_keyboard()
    if kb:
        await query.edit_message_text(
            "📚 <b>IELTS bo'limlari:</b>\n\nBo'limni tanlang va testni boshlang! 👇",
            parse_mode="HTML", reply_markup=kb,
        )
    else:
        await query.edit_message_text(NO_SUBJECTS_TEXT, parse_mode="HTML")
