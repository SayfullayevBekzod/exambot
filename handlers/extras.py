"""Study Plan — 30/60/90 kunlik reja + Speed Round + Premium + Translation"""
from datetime import date, timedelta, datetime
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_session, StudyPlan, UserSettings, Subject, Question, UserResult


# === Study Plan ===

STUDY_PLANS = {
    "30": {
        "name": "30 kunlik intensiv",
        "weeks": [
            {"focus": "Vocabulary & Grammar asoslari", "daily": "20 so'z + 10 grammar test"},
            {"focus": "Reading strategiyalari", "daily": "2 ta passage + 15 savol"},
            {"focus": "Listening mashqlari", "daily": "3 ta audio + savollar"},
            {"focus": "Speaking & Writing + Mock", "daily": "1 essay + 1 mock test"},
        ],
    },
    "60": {
        "name": "60 kunlik standart",
        "weeks": [
            {"focus": "Vocabulary kengaytirish", "daily": "10 yangi so'z + flashcards"},
            {"focus": "Grammar chuqurlashtirish", "daily": "15 grammar test"},
            {"focus": "Reading va Listening", "daily": "1 passage + 2 audio"},
            {"focus": "Reading va Vocabulary", "daily": "2 passage + 10 so'z"},
            {"focus": "Listening va Grammar", "daily": "2 audio + grammar mashq"},
            {"focus": "Speaking tayyorlanish", "daily": "3 ta topic + model answers"},
            {"focus": "Writing Task 1 & 2", "daily": "1 essay + analysis"},
            {"focus": "Mock Test hafta", "daily": "Har kuni 1 ta mock test"},
        ],
    },
    "90": {
        "name": "90 kunlik master",
        "weeks": [
            {"focus": "Asosiy vocabulary", "daily": "15 so'z + spaced repetition"},
            {"focus": "Grammar fundamentals", "daily": "Tenses, articles, prepositions"},
            {"focus": "Reading skimming", "daily": "Tez o'qish texnikasi"},
            {"focus": "Reading scanning", "daily": "Kalit so'z izlash"},
            {"focus": "Listening Section 1-2", "daily": "Kundalik dialog va form-filling"},
            {"focus": "Listening Section 3-4", "daily": "Akademik lecture va discussion"},
            {"focus": "Vocabulary ilg'or", "daily": "Academic word list"},
            {"focus": "Grammar ilg'or", "daily": "Complex structures"},
            {"focus": "Writing Task 1", "daily": "Graph description mashq"},
            {"focus": "Writing Task 2", "daily": "Essay writing mashq"},
            {"focus": "Speaking Part 1-2", "daily": "Cue card tayyorlash"},
            {"focus": "Full Mock + Review", "daily": "2 mock + xatolarni tahlil"},
        ],
    },
}


async def studyplan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reja buyrug'i"""
    from handlers.payment import require_premium
    if not await require_premium(update, "📅 Study Plan"):
        return
    user_id = update.effective_user.id
    session = get_session()
    try:
        plan = session.query(StudyPlan).filter_by(user_id=user_id).first()

        if plan and not plan.completed:
            # Mavjud rejani ko'rsatish
            plan_info = STUDY_PLANS.get(plan.plan_type, STUDY_PLANS["30"])
            total_days = int(plan.plan_type)
            weeks_total = len(plan_info["weeks"])
            current_week = min((plan.current_day - 1) // 7, weeks_total - 1)
            week_info = plan_info["weeks"][current_week]

            pct = min(100, plan.current_day / total_days * 100)
            filled = round(10 * pct / 100)
            bar = "🟩" * filled + "⬜" * (10 - filled)

            text = (
                f"📅 <b>{plan_info['name']}</b>\n\n"
                f"📊 Kun: <b>{plan.current_day}/{total_days}</b>\n"
                f"🎯 Maqsad: Band {plan.target_band}\n"
                f"[{bar}] {pct:.0f}%\n\n"
                f"📌 <b>Haftaning mavzusi:</b>\n"
                f"🔹 {week_info['focus']}\n"
                f"📝 Kundalik: {week_info['daily']}\n"
            )
            keyboard = [
                [InlineKeyboardButton("✅ Bugungi vazifani bajarildi", callback_data="plan_done_today")],
                [InlineKeyboardButton("🗑️ Rejani o'chirish", callback_data="plan_delete")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
            ]
        else:
            text = (
                "📅 <b>IELTS Study Plan</b>\n\n"
                "Shaxsiy o'qish rejangizni tanlang:\n\n"
                "⚡ <b>30 kun</b> — Intensiv (imtihon yaqin)\n"
                "📚 <b>60 kun</b> — Standart (yetarli vaqt)\n"
                "🎓 <b>90 kun</b> — Master (to'liq tayyorlanish)\n"
            )
            keyboard = [
                [InlineKeyboardButton("⚡ 30 kun", callback_data="plan_create_30")],
                [InlineKeyboardButton("📚 60 kun", callback_data="plan_create_60")],
                [InlineKeyboardButton("🎓 90 kun", callback_data="plan_create_90")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
            ]

        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()


async def plan_create_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reja yaratish"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    plan_type = query.data.split("_")[2]

    session = get_session()
    try:
        # Eski rejani o'chirish
        session.query(StudyPlan).filter_by(user_id=user_id).delete()

        plan = StudyPlan(
            user_id=user_id,
            plan_type=plan_type,
            target_band=6.5,
            start_date=date.today().isoformat(),
            current_day=1,
        )
        session.add(plan)
        session.commit()

        plan_info = STUDY_PLANS[plan_type]
        text = (
            f"✅ <b>{plan_info['name']}</b> rejasi yaratildi!\n\n"
            f"📅 Boshlanish: {date.today().strftime('%d.%m.%Y')}\n"
            f"🏁 Tugash: {(date.today() + timedelta(days=int(plan_type))).strftime('%d.%m.%Y')}\n\n"
            f"📌 <b>Birinchi hafta:</b>\n"
            f"🔹 {plan_info['weeks'][0]['focus']}\n"
            f"📝 {plan_info['weeks'][0]['daily']}\n\n"
            f"Har kuni /reja buyrug'ini bosib, vazifangizni tekshiring!"
        )
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")]]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()


async def plan_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bugungi vazifani bajarish"""
    query = update.callback_query
    await query.answer("✅ Bugungi vazifa bajarildi!")
    user_id = query.from_user.id

    session = get_session()
    try:
        plan = session.query(StudyPlan).filter_by(user_id=user_id).first()
        if plan:
            plan.current_day += 1
            if plan.current_day > int(plan.plan_type):
                plan.completed = True
            session.commit()

            if plan.completed:
                text = "🎉 <b>Tabriklaymiz!</b> Reja to'liq tugatildi! 🏆"
            else:
                text = f"✅ Kun {plan.current_day - 1} bajarildi! Ertaga davom eting 💪"

        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")]]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()


async def plan_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🗑️ Reja o'chirildi!")
    user_id = query.from_user.id
    session = get_session()
    try:
        session.query(StudyPlan).filter_by(user_id=user_id).delete()
        session.commit()
        await query.edit_message_text("🗑️ Reja o'chirildi. /reja orqali yangi reja yarating.")
    finally:
        session.close()


# === Speed Round ===

async def speed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/speed buyrug'i"""
    from handlers.payment import require_premium
    if not await require_premium(update, "🎮 Speed Round"):
        return
    session = get_session()
    try:
        subjects = session.query(Subject).all()
        if not subjects:
            await update.message.reply_text("❌ Bo'limlar topilmadi!")
            return

        # Barcha fanlardan 15 ta tasodifiy savol
        all_questions = session.query(Question).all()
        if len(all_questions) < 5:
            await update.message.reply_text("❌ Yetarli savol yo'q!")
            return

        selected = random.sample(all_questions, min(15, len(all_questions)))

        context.user_data["speed"] = {
            "questions": [q.id for q in selected],
            "current_index": 0,
            "score": 0,
            "total": len(selected),
            "start_time": datetime.utcnow().isoformat(),
            "times": [],
        }

        text = (
            "🎮 <b>SPEED ROUND!</b>\n\n"
            f"⚡ {len(selected)} ta savol — eng tez javob bering!\n"
            "⏱️ Vaqtingiz hisoblanadi!\n\n"
            "Tayyor? 👇"
        )
        keyboard = [[InlineKeyboardButton("🚀 BOSHLASH!", callback_data="speed_start")]]
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()


async def speed_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    speed = context.user_data.get("speed")
    if not speed:
        return

    speed["q_start_time"] = datetime.utcnow().isoformat()
    session = get_session()
    try:
        await _send_speed_question(query, context, session)
    finally:
        session.close()


async def _send_speed_question(query, context, session):
    speed = context.user_data.get("speed")
    idx = speed["current_index"]
    qid = speed["questions"][idx]
    q = session.query(Question).get(qid)
    options = q.get_options()

    from keyboards.inline import answer_keyboard
    text = (
        f"⚡ <b>Speed #{idx + 1}/{speed['total']}</b>\n\n"
        f"❓ {q.text}\n\n"
        f"🅰️ <b>A)</b> {options['a']}\n"
        f"🅱️ <b>B)</b> {options['b']}\n"
        f"🅲 <b>C)</b> {options['c']}\n"
        f"🅳 <b>D)</b> {options['d']}"
    )
    kb = answer_keyboard(q.id)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    speed["q_start_time"] = datetime.utcnow().isoformat()


async def speed_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Speed round javob"""
    query = update.callback_query
    speed = context.user_data.get("speed")
    if not speed:
        return False

    parts = query.data.split("_")
    question_id = int(parts[1])
    if question_id not in speed["questions"]:
        return False

    user_answer = parts[2]
    await query.answer()

    # Vaqt hisoblash
    q_start = datetime.fromisoformat(speed.get("q_start_time", datetime.utcnow().isoformat()))
    elapsed = (datetime.utcnow() - q_start).total_seconds()
    speed["times"].append(elapsed)

    session = get_session()
    try:
        q = session.query(Question).get(question_id)
        is_correct = user_answer == q.correct_answer
        if is_correct:
            speed["score"] += 1

        speed["current_index"] += 1

        if speed["current_index"] < speed["total"]:
            await _send_speed_question(query, context, session)
        else:
            # Tugadi
            total_time = sum(speed["times"])
            avg_time = total_time / len(speed["times"])
            score = speed["score"]
            total = speed["total"]

            text = (
                f"🏁 <b>Speed Round tugadi!</b>\n\n"
                f"⏱️ Umumiy vaqt: <b>{total_time:.1f}s</b>\n"
                f"⚡ O'rtacha: <b>{avg_time:.1f}s</b> / savol\n\n"
                f"✅ To'g'ri: {score}/{total}\n"
                f"📊 Aniqlik: {score/total*100:.0f}%\n\n"
            )

            if avg_time < 5:
                text += "🏆 Chaqmoq tezligida! Ajoyib!"
            elif avg_time < 10:
                text += "⚡ Juda tez! Yaxshi natija!"
            elif avg_time < 20:
                text += "👍 Yaxshi tezlik!"
            else:
                text += "🐢 Yaxshi mashq qiling. Tezlikni oshiring!"

            keyboard = [
                [InlineKeyboardButton("🔄 Yana o'ynash", callback_data="speed_restart")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
            ]
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            context.user_data.pop("speed", None)

        return True
    finally:
        session.close()


# === Translation Mode ===

async def translation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tarjima buyrug'i"""
    from handlers.payment import require_premium
    if not await require_premium(update, "🌐 Tarjima rejimi"):
        return
    user_id = update.effective_user.id
    session = get_session()
    try:
        settings = session.query(UserSettings).filter_by(user_id=user_id).first()
        current = settings.translation_mode if settings else False
        status = "✅ Yoqilgan" if current else "❌ O'chirilgan"

        keyboard = [
            [InlineKeyboardButton("✅ Yoqish", callback_data="translate_on")],
            [InlineKeyboardButton("❌ O'chirish", callback_data="translate_off")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
        ]
        await update.message.reply_text(
            f"🌐 <b>Tarjima rejimi</b>\n\n"
            f"Holati: {status}\n\n"
            f"Yoqilganda, test savollarining pastida o'zbek tarjimasi ko'rsatiladi.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    finally:
        session.close()


async def translation_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    enable = "on" in query.data

    session = get_session()
    try:
        settings = session.query(UserSettings).filter_by(user_id=user_id).first()
        if not settings:
            settings = UserSettings(user_id=user_id)
            session.add(settings)
        settings.translation_mode = enable
        session.commit()

        status = "✅ Yoqildi" if enable else "❌ O'chirildi"
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")]]
        await query.edit_message_text(f"🌐 Tarjima rejimi: {status}", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()



# === Mini App ===

async def miniapp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/webapp buyrug'i"""
    text = (
        "📱 <b>IELTS Mini App</b>\n\n"
        "Telegram Mini App orqali qulay interfeys!\n\n"
        "🔹 Barcha bo'limlar bir joyda\n"
        "🔹 Tez test yechish\n"
        "🔹 Natijalar grafigi\n"
        "🔹 Flashcards swipe\n"
        "🔹 Premium obuna\n\n"
        "🌐 Lokal server: <code>python webapp_server.py</code>\n"
        "📍 http://localhost:8080\n\n"
        "💡 <i>Deploy qilgandan keyin BotFather orqali WebApp URL ni sozlang</i>"
    )
    keyboard = [
        [InlineKeyboardButton("📚 Bo'limlar", callback_data="back_subjects")],
        [InlineKeyboardButton("🗂️ Flashcards", callback_data="fc_study")],
    ]
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

