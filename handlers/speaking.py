"""IELTS Speaking Practice — Bot sherik bo'lib speaking mashq qilish"""
import os
import random
import tempfile
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# === IELTS Speaking savollar bazasi ===

SPEAKING_PART1 = {
    "home": {
        "topic": "🏠 Home & Accommodation",
        "questions": [
            "Do you live in a house or an apartment?",
            "What is your favorite room in your home? Why?",
            "How long have you been living in your current home?",
            "What would you change about your home if you could?",
            "Do you plan to live there for a long time?",
            "Is the area where you live quiet or noisy?",
        ]
    },
    "work": {
        "topic": "💼 Work & Studies",
        "questions": [
            "What do you do? Do you work or study?",
            "Why did you choose this job or field of study?",
            "What do you like most about your work or studies?",
            "Would you like to change your job in the future?",
            "Do you prefer working alone or in a team?",
            "What is the most challenging part of your work?",
        ]
    },
    "hobbies": {
        "topic": "🎨 Hobbies & Free Time",
        "questions": [
            "What do you enjoy doing in your free time?",
            "Have you always had the same hobbies?",
            "Do you prefer indoor or outdoor activities?",
            "How much time do you spend on your hobbies each week?",
            "Would you like to try any new hobbies?",
            "Is there a hobby you used to enjoy but no longer do?",
        ]
    },
    "travel": {
        "topic": "✈️ Travel & Tourism",
        "questions": [
            "Do you enjoy traveling? Why or why not?",
            "What was the last place you visited?",
            "Do you prefer traveling alone or with others?",
            "What kind of places do you like to visit?",
            "Have you ever been abroad?",
            "What is your dream travel destination?",
        ]
    },
    "technology": {
        "topic": "📱 Technology",
        "questions": [
            "How often do you use the internet?",
            "What is your favorite app or website?",
            "Do you think technology has improved our lives?",
            "How do you usually keep in touch with friends?",
            "Do you use social media? Which platforms?",
            "What technology could you not live without?",
        ]
    },
    "food": {
        "topic": "🍽️ Food & Cooking",
        "questions": [
            "What is your favorite food?",
            "Do you enjoy cooking? Why or why not?",
            "How often do you eat out at restaurants?",
            "Have you ever tried foreign cuisine?",
            "Is there any food you dislike?",
            "Do you think eating habits in your country have changed?",
        ]
    },
}

SPEAKING_PART2 = [
    {
        "topic": "An important person in your life",
        "cue_card": (
            "Describe an important person in your life.\n\n"
            "You should say:\n"
            "• who this person is\n"
            "• how you know them\n"
            "• what they do\n"
            "• and explain why this person is important to you."
        ),
    },
    {
        "topic": "A place you would like to visit",
        "cue_card": (
            "Describe a place you would like to visit.\n\n"
            "You should say:\n"
            "• where this place is\n"
            "• how you learned about it\n"
            "• what you would do there\n"
            "• and explain why you want to visit this place."
        ),
    },
    {
        "topic": "A memorable event in your life",
        "cue_card": (
            "Describe a memorable event in your life.\n\n"
            "You should say:\n"
            "• when it happened\n"
            "• where it happened\n"
            "• what happened\n"
            "• and explain why it is memorable for you."
        ),
    },
    {
        "topic": "A skill you would like to learn",
        "cue_card": (
            "Describe a skill you would like to learn.\n\n"
            "You should say:\n"
            "• what the skill is\n"
            "• why you want to learn it\n"
            "• how you would learn it\n"
            "• and explain how this skill would be useful for you."
        ),
    },
    {
        "topic": "A book you recently read",
        "cue_card": (
            "Describe a book you recently read.\n\n"
            "You should say:\n"
            "• what the book was about\n"
            "• why you chose to read it\n"
            "• how long it took you to finish\n"
            "• and explain whether you would recommend it."
        ),
    },
    {
        "topic": "A challenge you overcame",
        "cue_card": (
            "Describe a challenge you overcame.\n\n"
            "You should say:\n"
            "• what the challenge was\n"
            "• when it happened\n"
            "• how you dealt with it\n"
            "• and explain what you learned from this experience."
        ),
    },
]

SPEAKING_PART3 = {
    "people": [
        "What qualities make a good leader?",
        "How have family structures changed in recent years?",
        "Do you think people rely too much on others?",
        "Is it important to have role models? Why?",
        "How do you think relationships between people will change in the future?",
    ],
    "places": [
        "Why do people like to travel to different places?",
        "How has tourism affected local communities?",
        "Do you think it is better to live in a city or in the countryside?",
        "How important is it to preserve historical buildings?",
        "Will virtual travel ever replace real travel?",
    ],
    "education": [
        "How has education changed in your country?",
        "Do you think online learning is as effective as classroom learning?",
        "What are the advantages of learning a foreign language?",
        "Should education be free for everyone?",
        "How important are practical skills compared to academic knowledge?",
    ],
    "technology_society": [
        "How has technology changed the way people communicate?",
        "Do you think social media has more positive or negative effects?",
        "Will artificial intelligence replace human workers?",
        "How can governments ensure people have digital literacy?",
        "Is it important for children to learn about technology at school?",
    ],
}

# === IELTS Speaking band tavsiflovchi ===

def analyze_speaking(text: str) -> dict:
    """Matnni tahlil qilib speaking baholash"""
    if not text or len(text.strip()) < 5:
        return {
            "band": 3.0, "word_count": 0,
            "vocab_score": 0, "grammar_score": 0,
            "fluency_score": 0, "coherence_score": 0,
            "feedback": [], "strengths": [], "tips": [],
        }

    words = text.split()
    word_count = len(words)
    unique_words = set(w.lower().strip(".,!?;:\"'()") for w in words)
    unique_count = len(unique_words)

    # 1. Vocabulary Score (lexical resource)
    vocab_ratio = unique_count / max(word_count, 1)
    advanced_words = [
        "however", "moreover", "furthermore", "nevertheless", "consequently",
        "significant", "essential", "particularly", "approximately", "throughout",
        "beneficial", "fundamental", "effectively", "considerably", "substantial",
        "perspective", "environment", "opportunity", "experience", "development",
        "advantage", "disadvantage", "contribute", "influence", "communication",
        "ultimately", "essentially", "frequently", "occasionally", "tremendously",
    ]
    advanced_count = sum(1 for w in unique_words if w in advanced_words)
    vocab_score = min(9, (vocab_ratio * 10) + (advanced_count * 0.5) + 2)

    # 2. Grammar Score
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    avg_sentence_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)

    complex_patterns = [
        r'\b(if|when|because|although|while|since|unless|whereas)\b',
        r'\b(would|could|should|might|must)\b',
        r'\b(have been|has been|had been|will have)\b',
        r'\b(not only|as well as|in addition|on the other hand)\b',
    ]
    complex_count = sum(
        1 for p in complex_patterns if re.search(p, text, re.IGNORECASE)
    )
    grammar_score = min(9, 4 + (complex_count * 0.8) + min(avg_sentence_len / 5, 2))

    # 3. Fluency Score (response uzunligi va ravonligi)
    if word_count >= 80:
        fluency_score = min(9, 6 + (word_count - 80) / 40)
    elif word_count >= 40:
        fluency_score = 5 + (word_count - 40) / 40
    elif word_count >= 15:
        fluency_score = 3.5 + (word_count - 15) / 25
    else:
        fluency_score = max(2, word_count / 5)

    # 4. Coherence Score
    linking_words = [
        "firstly", "secondly", "finally", "however", "moreover",
        "because", "therefore", "although", "in addition", "for example",
        "such as", "on the other hand", "in my opinion", "i think",
        "i believe", "in conclusion", "to sum up", "as a result",
    ]
    link_count = sum(
        1 for phrase in linking_words if phrase in text.lower()
    )
    coherence_score = min(9, 4 + (link_count * 0.6) + (len(sentences) * 0.3))

    # Band hisoblash
    band = round((vocab_score + grammar_score + fluency_score + coherence_score) / 4 * 2) / 2
    band = max(3.0, min(9.0, band))

    # Feedback
    feedback = []
    strengths = []
    tips = []

    # Strengths
    if word_count >= 60:
        strengths.append("✅ Yetarlicha uzun javob berdingiz")
    if advanced_count >= 2:
        strengths.append(f"✅ {advanced_count} ta ilg'or so'z ishlatdingiz")
    if complex_count >= 2:
        strengths.append("✅ Murakkab grammatik tuzilmalar ishlatdingiz")
    if link_count >= 2:
        strengths.append("✅ Bog'lovchi so'zlarni yaxshi ishlatdingiz")

    # Tips
    if word_count < 40:
        tips.append("📌 Javobni uzunroq qiling — kamida 50-80 so'z aytishga harakat qiling")
    if advanced_count < 2:
        tips.append("📌 Ko'proq ilg'or so'zlar ishlating (however, moreover, significantly...)")
    if complex_count < 2:
        tips.append("📌 Murakkab gaplar tuzing (If..., Although..., Because...)")
    if link_count < 2:
        tips.append("📌 Bog'lovchi so'zlar qo'shing (Firstly, Moreover, For example...)")
    if avg_sentence_len < 6:
        tips.append("📌 Gaplarni uzunroq qiling, tafsilotlar qo'shing")

    return {
        "band": band,
        "word_count": word_count,
        "unique_words": unique_count,
        "vocab_score": round(vocab_score, 1),
        "grammar_score": round(grammar_score, 1),
        "fluency_score": round(fluency_score, 1),
        "coherence_score": round(coherence_score, 1),
        "strengths": strengths,
        "tips": tips,
        "advanced_used": advanced_count,
        "linking_used": link_count,
    }


# ==========================================
#  HANDLERS
# ==========================================

async def speaking_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/speaking buyrug'i — IELTS Speaking mashq"""
    keyboard = [
        [InlineKeyboardButton("🎤 Part 1 — Intervyu", callback_data="speak_part1")],
        [InlineKeyboardButton("📋 Part 2 — Cue Card", callback_data="speak_part2")],
        [InlineKeyboardButton("💬 Part 3 — Munozara", callback_data="speak_part3")],
        [InlineKeyboardButton("🎲 Random savol", callback_data="speak_random")],
    ]

    text = (
        "🎤 <b>IELTS Speaking Practice</b>\n\n"
        "Bot sizga IELTS Speaking savol beradi.\n"
        "Siz <b>voice message</b> yoki <b>matn</b> orqali javob bering.\n\n"
        "Bot javobingizni tahlil qilib, band score va tavsiyalar beradi.\n\n"
        "📌 <b>Qismlar:</b>\n"
        "• <b>Part 1</b> — Oddiy savollar (4-5 daqiqa)\n"
        "• <b>Part 2</b> — Cue Card mavzu (1-2 daqiqa)\n"
        "• <b>Part 3</b> — Chuqur munozara (4-5 daqiqa)\n\n"
        "🎯 Qismni tanlang:"
    )

    await update.message.reply_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def speak_part1_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Part 1 mavzularini ko'rsatish"""
    query = update.callback_query
    await query.answer()

    keyboard = []
    for key, data in SPEAKING_PART1.items():
        keyboard.append([InlineKeyboardButton(
            data["topic"], callback_data=f"speak_p1_{key}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="speak_back")])

    await query.edit_message_text(
        "🎤 <b>Part 1 — Mavzuni tanlang:</b>\n\n"
        "Examiner sizga oddiy savollar beradi.\n"
        "Har bir savolga 2-3 gap bilan javob bering.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def speak_p1_topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Part 1 dan savol berish"""
    query = update.callback_query
    await query.answer()

    topic_key = query.data.replace("speak_p1_", "")
    topic_data = SPEAKING_PART1.get(topic_key)
    if not topic_data:
        await query.edit_message_text("❌ Mavzu topilmadi!")
        return

    questions = random.sample(topic_data["questions"], min(3, len(topic_data["questions"])))

    # Session saqlash
    context.user_data["speaking"] = {
        "part": 1,
        "topic": topic_data["topic"],
        "questions": questions,
        "current": 0,
        "answers": [],
    }

    await query.edit_message_text(
        f"🎤 <b>{topic_data['topic']}</b>\n\n"
        f"<b>Examiner:</b>\n"
        f"Let's talk about {topic_key.replace('_', ' ')}.\n\n"
        f"❓ <b>Savol 1/{len(questions)}:</b>\n"
        f"<i>{questions[0]}</i>\n\n"
        "🎙️ <b>Voice message</b> yoki <b>matn</b> yuboring:",
        parse_mode="HTML"
    )


async def speak_part2_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Part 2 — Cue Card"""
    query = update.callback_query
    await query.answer()

    card = random.choice(SPEAKING_PART2)

    context.user_data["speaking"] = {
        "part": 2,
        "topic": card["topic"],
        "cue_card": card["cue_card"],
        "current": 0,
        "answers": [],
    }

    await query.edit_message_text(
        f"📋 <b>Part 2 — Long Turn</b>\n\n"
        f"<b>Examiner:</b>\n"
        f"I'd like you to describe something to you.\n\n"
        f"📝 <b>Cue Card:</b>\n\n"
        f"<i>{card['cue_card']}</i>\n\n"
        "⏱️ Haqiqiy IELTS'da 1-2 daqiqa gapirasiz.\n"
        "Tayyorlaning va javobingizni yuboring:\n\n"
        "🎙️ <b>Voice message</b> yoki <b>matn</b> yuboring:",
        parse_mode="HTML"
    )


async def speak_part3_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Part 3 — Discussion"""
    query = update.callback_query
    await query.answer()

    topic_key = random.choice(list(SPEAKING_PART3.keys()))
    questions = random.sample(SPEAKING_PART3[topic_key], min(3, len(SPEAKING_PART3[topic_key])))

    context.user_data["speaking"] = {
        "part": 3,
        "topic": topic_key.replace("_", " ").title(),
        "questions": questions,
        "current": 0,
        "answers": [],
    }

    await query.edit_message_text(
        f"💬 <b>Part 3 — Discussion</b>\n\n"
        f"<b>Examiner:</b>\n"
        f"Now let's discuss some more general questions.\n\n"
        f"❓ <b>Savol 1/{len(questions)}:</b>\n"
        f"<i>{questions[0]}</i>\n\n"
        "🎙️ <b>Voice message</b> yoki <b>matn</b> yuboring:",
        parse_mode="HTML"
    )


async def speak_random_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Random savol"""
    query = update.callback_query
    await query.answer()

    part = random.choice([1, 2, 3])
    if part == 1:
        topic_key = random.choice(list(SPEAKING_PART1.keys()))
        topic_data = SPEAKING_PART1[topic_key]
        question = random.choice(topic_data["questions"])
        context.user_data["speaking"] = {
            "part": 1, "topic": topic_data["topic"],
            "questions": [question], "current": 0, "answers": [],
        }
        await query.edit_message_text(
            f"🎲 <b>Random — Part 1</b>\n\n"
            f"❓ <i>{question}</i>\n\n"
            "🎙️ Javobingizni yuboring:",
            parse_mode="HTML"
        )
    elif part == 2:
        card = random.choice(SPEAKING_PART2)
        context.user_data["speaking"] = {
            "part": 2, "topic": card["topic"],
            "cue_card": card["cue_card"], "current": 0, "answers": [],
        }
        await query.edit_message_text(
            f"🎲 <b>Random — Part 2</b>\n\n"
            f"📝 <i>{card['cue_card']}</i>\n\n"
            "🎙️ Javobingizni yuboring:",
            parse_mode="HTML"
        )
    else:
        topic_key = random.choice(list(SPEAKING_PART3.keys()))
        question = random.choice(SPEAKING_PART3[topic_key])
        context.user_data["speaking"] = {
            "part": 3, "topic": topic_key.replace("_", " ").title(),
            "questions": [question], "current": 0, "answers": [],
        }
        await query.edit_message_text(
            f"🎲 <b>Random — Part 3</b>\n\n"
            f"❓ <i>{question}</i>\n\n"
            "🎙️ Javobingizni yuboring:",
            parse_mode="HTML"
        )


async def speak_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Orqaga qaytish"""
    query = update.callback_query
    await query.answer()
    # speaking_command ni callback formatida chaqirish
    keyboard = [
        [InlineKeyboardButton("🎤 Part 1 — Intervyu", callback_data="speak_part1")],
        [InlineKeyboardButton("📋 Part 2 — Cue Card", callback_data="speak_part2")],
        [InlineKeyboardButton("💬 Part 3 — Munozara", callback_data="speak_part3")],
        [InlineKeyboardButton("🎲 Random savol", callback_data="speak_random")],
    ]
    await query.edit_message_text(
        "🎤 <b>IELTS Speaking Practice</b>\n\n"
        "Qismni tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==========================================
#  VOICE / TEXT JAVOBNI QABUL QILISH
# ==========================================

async def handle_speaking_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Voice message ni qabul qilib, transkripsiya va tahlil qilish"""
    speaking = context.user_data.get("speaking")
    if not speaking:
        return  # Speaking sessiya yo'q — skip

    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)

    # OGG faylni yuklab olish
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as ogg_f:
        ogg_path = ogg_f.name
        await file.download_to_drive(ogg_path)

    transcript = ""
    try:
        import asyncio
        
        def transcribe_sync(ogg_path_sync):
            # pydub bilan OGG → WAV konvertatsiya (ffmpeg kerak)
            from pydub import AudioSegment
            audio = AudioSegment.from_ogg(ogg_path_sync)
            wav_path_sync = ogg_path_sync.replace(".ogg", ".wav")
            audio.export(wav_path_sync, format="wav")

            # Speech Recognition
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            try:
                with sr.AudioFile(wav_path_sync) as source:
                    audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data, language="en-US")
                    return text
            finally:
                if os.path.exists(wav_path_sync):
                    os.unlink(wav_path_sync)

        # CPU intensive taskni threadga topshirish
        transcript = await asyncio.to_thread(transcribe_sync, ogg_path)

    except FileNotFoundError:
        # ffmpeg o'rnatilmagan
        await update.message.reply_text(
            "🎙️ <b>Voice qabul qilindi!</b>\n\n"
            "⚠️ Hozircha ovozni matnga o'girish imkoni yo'q "
            "(ffmpeg o'rnatilmagan).\n\n"
            "📝 Iltimos, javobingizni <b>ingliz tilida matn</b> "
            "sifatida yuboring — bot baholaydi!",
            parse_mode="HTML"
        )
        return
    except Exception as e:
        transcript = ""
        await update.message.reply_text(
            "⚠️ <b>Ovozni tanib bo'lmadi.</b>\n\n"
            "📝 Iltimos, javobingizni <b>matn</b> sifatida yuboring.\n\n"
            f"<i>Xato: {str(e)[:100]}</i>",
            parse_mode="HTML"
        )
    finally:
        if os.path.exists(ogg_path):
            os.unlink(ogg_path)

    if transcript:
        await process_speaking_answer(update, context, transcript, is_voice=True)


async def handle_speaking_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matn javobni qabul qilish"""
    speaking = context.user_data.get("speaking")
    if not speaking:
        return False  # Speaking sessiya yo'q

    text = update.message.text
    if text.startswith("/"):
        return False  # Command — skip

    # Menyu tugmalarini skrip qilish (agar foydalanuvchi boshqa bo'limga o'tmoqchi bo'lsa)
    text_clean = text.lower().strip()
    
    # Muhim: Tugma matnlarini qisman tekshirish (emoji turli bo'lishi mumkinligi uchun)
    menu_keywords = [
        "bo'lim", "test", "natija", "reyting", "xato", "yutuq", "so'z", "tips",
        "writing", "audio", "flash", "takrorlash", "plan", "speed", "sertifikat",
        "premium", "tarjima", "eslatma", "challenge", "yordam", "speaking", "admin"
    ]
    
    # Agar matn menyu tugmasiga o'xshasa yoki aniq tugma bo'lsa
    if any(kw in text_clean for kw in menu_keywords):
        context.user_data.pop("speaking", None)  # Sessiyani yakunlash
        return False

    await process_speaking_answer(update, context, text, is_voice=False)
    return True


async def process_speaking_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, answer: str, is_voice: bool):
    """Javobni tahlil qilish va natija berish"""
    speaking = context.user_data.get("speaking")
    if not speaking:
        return

    part = speaking["part"]
    current = speaking["current"]

    # Javobni saqlash
    speaking["answers"].append(answer)

    # Tahlil
    analysis = analyze_speaking(answer)

    # Band emoji
    band = analysis["band"]
    if band >= 7.5:
        band_emoji = "🏆"
    elif band >= 6.5:
        band_emoji = "🥇"
    elif band >= 5.5:
        band_emoji = "🎯"
    elif band >= 4.5:
        band_emoji = "📖"
    else:
        band_emoji = "💪"

    # Result text
    voice_marker = "🎙️ " if is_voice else ""
    result = (
        f"📊 <b>{voice_marker}Javob Tahlili</b>\n\n"
        f"{band_emoji} <b>Taxminiy Band: {band}</b>\n\n"
        f"📝 <b>Transkripsiya:</b>\n"
        f"<i>{answer[:500]}{'...' if len(answer) > 500 else ''}</i>\n\n"
        f"📈 <b>Baholash:</b>\n"
        f"• 📚 Vocabulary: <b>{analysis['vocab_score']}/9</b>\n"
        f"• 📖 Grammar: <b>{analysis['grammar_score']}/9</b>\n"
        f"• 🗣️ Fluency: <b>{analysis['fluency_score']}/9</b>\n"
        f"• 🔗 Coherence: <b>{analysis['coherence_score']}/9</b>\n\n"
        f"📊 So'zlar soni: {analysis['word_count']} | "
        f"Turli so'zlar: {analysis.get('unique_words', 0)}\n"
    )

    # Strengths
    if analysis["strengths"]:
        result += "\n<b>💪 Kuchli tomonlar:</b>\n"
        result += "\n".join(analysis["strengths"]) + "\n"

    # Tips
    if analysis["tips"]:
        result += "\n<b>💡 Tavsiyalar:</b>\n"
        result += "\n".join(analysis["tips"]) + "\n"

    # Keyingi savol yoki yakunlash
    questions = speaking.get("questions", [])
    current += 1
    speaking["current"] = current

    if current < len(questions):
        # Keyingi savol
        result += (
            f"\n{'─' * 28}\n\n"
            f"❓ <b>Savol {current + 1}/{len(questions)}:</b>\n"
            f"<i>{questions[current]}</i>\n\n"
            "🎙️ Javobingizni yuboring:"
        )
        await update.message.reply_text(result, parse_mode="HTML")
    else:
        # Session yakunlash
        all_answers = " ".join(speaking["answers"])
        overall = analyze_speaking(all_answers)

        result += (
            f"\n{'─' * 28}\n\n"
            f"🏁 <b>Sessiya yakunlandi!</b>\n\n"
            f"🎯 <b>Umumiy Band: {overall['band']}</b>\n"
            f"📝 Jami so'zlar: {overall['word_count']}\n"
        )

        keyboard = [
            [InlineKeyboardButton("🎤 Yana mashq", callback_data="speak_back")],
            [InlineKeyboardButton("📋 Part 2 sinash", callback_data="speak_part2")],
        ]

        context.user_data.pop("speaking", None)
        await update.message.reply_text(
            result, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
