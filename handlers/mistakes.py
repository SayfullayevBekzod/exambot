"""Xatolar ro'yxati — noto'g'ri javoblarni qayta yechish"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_session, WrongAnswer, Question, Subject
from keyboards.inline import answer_keyboard


async def mistakes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/xatolar buyrug'i"""
    user_id = update.effective_user.id
    session = get_session()
    try:
        wrongs = (
            session.query(WrongAnswer)
            .filter_by(user_id=user_id, reviewed=False)
            .order_by(WrongAnswer.answered_at.desc())
            .all()
        )
        if not wrongs:
            await update.message.reply_text(
                "✅ <b>Ajoyib!</b> Sizda ko'rib chiqilmagan xatolar yo'q!\n\n"
                "Yangi test yechib, bilimingizni sinab ko'ring 💪",
                parse_mode="HTML",
            )
            return

        # Subject bo'yicha guruhlash
        subject_counts = {}
        for w in wrongs:
            q = session.query(Question).get(w.question_id)
            if q:
                s = session.query(Subject).get(q.subject_id)
                key = s.id if s else 0
                if key not in subject_counts:
                    subject_counts[key] = {"name": f"{s.emoji} {s.name}" if s else "?", "count": 0}
                subject_counts[key]["count"] += 1

        text = f"❌ <b>Xatolar ro'yxati</b>\n\nJami: <b>{len(wrongs)}</b> ta ko'rib chiqilmagan xato\n\n"
        for sid, info in subject_counts.items():
            text += f"  {info['name']}: {info['count']} ta\n"
        text += "\n👇 Xatolarni qayta yechish uchun bosing:"

        keyboard = [
            [InlineKeyboardButton("🔄 Xatolarni qayta yechish", callback_data="review_mistakes")],
            [InlineKeyboardButton("🗑️ Hammasini o'chirish", callback_data="clear_mistakes")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
        ]
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()


async def review_mistakes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xatolarni qayta yechish"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    session = get_session()
    try:
        wrongs = (
            session.query(WrongAnswer)
            .filter_by(user_id=user_id, reviewed=False)
            .limit(10)
            .all()
        )
        if not wrongs:
            await query.edit_message_text("✅ Barcha xatolar ko'rib chiqilgan!")
            return

        # Xatolar quiz boshlash
        context.user_data["mistake_review"] = {
            "wrong_ids": [w.id for w in wrongs],
            "question_ids": [w.question_id for w in wrongs],
            "current_index": 0,
            "corrected": 0,
            "total": len(wrongs),
        }

        await _send_mistake_question(query, context, session)
    finally:
        session.close()


async def _send_mistake_question(query, context, session):
    """Xato savolni ko'rsatish"""
    review = context.user_data.get("mistake_review")
    if not review:
        return

    idx = review["current_index"]
    qid = review["question_ids"][idx]
    q = session.query(Question).get(qid)
    if not q:
        return

    s = session.query(Subject).get(q.subject_id)
    options = q.get_options()

    text = (
        f"🔄 <b>Xato #{idx + 1}/{review['total']}</b>\n"
        f"Bo'lim: {s.emoji} {s.name}\n\n"
        f"❓ {q.text}\n\n"
        f"🅰️ <b>A)</b> {options['a']}\n"
        f"🅱️ <b>B)</b> {options['b']}\n"
        f"🅲 <b>C)</b> {options['c']}\n"
        f"🅳 <b>D)</b> {options['d']}"
    )

    kb = answer_keyboard(q.id)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


async def mistake_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xato savolga javob"""
    query = update.callback_query
    review = context.user_data.get("mistake_review")
    if not review:
        return False  # Not a mistake review

    parts = query.data.split("_")
    question_id = int(parts[1])

    if question_id not in review["question_ids"]:
        return False  # Not part of mistake review

    user_answer = parts[2]
    await query.answer()

    session = get_session()
    try:
        q = session.query(Question).get(question_id)
        is_correct = user_answer == q.correct_answer

        if is_correct:
            review["corrected"] += 1
            # Xatoni "reviewed" deb belgilash
            idx = review["question_ids"].index(question_id)
            wrong_id = review["wrong_ids"][idx]
            wrong = session.query(WrongAnswer).get(wrong_id)
            if wrong:
                wrong.reviewed = True
                session.commit()

        review["current_index"] += 1

        if review["current_index"] < review["total"]:
            correct_text = q.get_options()[q.correct_answer]
            if is_correct:
                result = "✅ <b>To'g'ri!</b> Xatoni tuzatdingiz! 🎉"
            else:
                result = f"❌ <b>Yana noto'g'ri!</b>\n✅ To'g'ri javob: {q.correct_answer.upper()}) {correct_text}"

            next_qid = review["question_ids"][review["current_index"]]
            next_q = session.query(Question).get(next_qid)
            s = session.query(Subject).get(next_q.subject_id)
            next_opts = next_q.get_options()

            text = (
                f"{result}\n\n{'─' * 25}\n\n"
                f"🔄 <b>Xato #{review['current_index'] + 1}/{review['total']}</b>\n"
                f"Bo'lim: {s.emoji} {s.name}\n\n"
                f"❓ {next_q.text}\n\n"
                f"🅰️ <b>A)</b> {next_opts['a']}\n"
                f"🅱️ <b>B)</b> {next_opts['b']}\n"
                f"🅲 <b>C)</b> {next_opts['c']}\n"
                f"🅳 <b>D)</b> {next_opts['d']}"
            )
            kb = answer_keyboard(next_q.id)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        else:
            corrected = review["corrected"]
            total = review["total"]
            text = (
                f"🔄 <b>Xatolar ko'rib chiqildi!</b>\n\n"
                f"✅ Tuzatildi: {corrected}/{total}\n"
                f"❌ Hali xato: {total - corrected}\n"
            )
            keyboard = [[InlineKeyboardButton("🔙 Bosh sahifa", callback_data="back_subjects")]]
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            context.user_data.pop("mistake_review", None)

        return True
    finally:
        session.close()


async def clear_mistakes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha xatolarni o'chirish"""
    query = update.callback_query
    await query.answer("🗑️ Xatolar tozalandi!")
    user_id = query.from_user.id

    session = get_session()
    try:
        session.query(WrongAnswer).filter_by(user_id=user_id).update({"reviewed": True})
        session.commit()
        await query.edit_message_text("🗑️ Barcha xatolar tozalandi!\n\nYangi test yechishni boshlang 💪")
    finally:
        session.close()
