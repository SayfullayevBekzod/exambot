"""Audio Listening — TTS orqali eshitib tushunish"""
import os
import tempfile
from gtts import gTTS

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_session, Subject, Question
from keyboards.inline import answer_keyboard
import random


async def audio_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/audio buyrug'i"""
    from handlers.payment import require_premium
    if not await require_premium(update, "🎧 Audio Listening"):
        return
    session = get_session()
    try:
        # Listening bo'limini topish
        subject = session.query(Subject).filter_by(name="Listening").first()
        if not subject:
            await update.message.reply_text("❌ Listening bo'limi topilmadi!")
            return

        questions = session.query(Question).filter_by(subject_id=subject.id).all()
        if not questions:
            await update.message.reply_text("❌ Listening savollari topilmadi!")
            return

        q = random.choice(questions)
        options = q.get_options()

        # Audio yaratish
        await update.message.reply_text("🎧 <b>Audio tayyorlanmoqda...</b>", parse_mode="HTML")

        # Savolni audio qilish
        audio_text = q.text.replace("You hear:", "").replace("You hear a conversation:", "").replace("You hear a lecture:", "").strip()
        audio_text = audio_text.split("?")[0] if "?" in audio_text else audio_text
        # Faqat dialog/matn qismini olish
        if "'" in audio_text:
            parts = audio_text.split("'")
            if len(parts) >= 3:
                audio_text = parts[1]

        tts = gTTS(text=audio_text, lang="en", slow=False)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tts.save(f.name)
            temp_path = f.name

        # Audio yuborish
        with open(temp_path, "rb") as audio_file:
            await update.message.reply_voice(
                voice=audio_file,
                caption="🎧 Diqqat bilan eshiting!"
            )

        # Tozalash
        os.unlink(temp_path)

        # Savol va variantlar
        # Savolning so'roq qismini olish
        question_part = q.text.split("?")[-1].strip() if "?" in q.text else q.text
        if not question_part:
            question_part = q.text.split("'")[-1].strip().rstrip("?").strip()
            question_part = question_part + "?" if question_part else q.text

        # Savol matni
        text = (
            f"🎧 <b>Audio Listening</b>\n\n"
            f"❓ {q.text.split('?')[-2].split('.')[-1].strip() + '?' if '?' in q.text else q.text}\n\n"
            f"🅰️ <b>A)</b> {options['a']}\n"
            f"🅱️ <b>B)</b> {options['b']}\n"
            f"🅲 <b>C)</b> {options['c']}\n"
            f"🅳 <b>D)</b> {options['d']}"
        )

        # Javob uchun context saqlash
        context.user_data["audio_question"] = {
            "question_id": q.id,
            "correct": q.correct_answer,
        }

        kb = answer_keyboard(q.id)
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)

    except Exception as e:
        await update.message.reply_text(f"❌ Audio xatolik: {str(e)[:100]}")
    finally:
        session.close()
