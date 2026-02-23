"""Spaced Repetition — SM-2 algoritmi bilan takrorlash"""
from datetime import date, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_session, SpacedRepetition, Question, Subject, WrongAnswer
from keyboards.inline import answer_keyboard


def _sm2_update(card, quality):
    """SM-2 algoritmi: quality 0-5 (0=bilmaydi, 5=mukammal)"""
    if quality >= 3:
        if card.repetitions == 0:
            card.interval = 1
        elif card.repetitions == 1:
            card.interval = 6
        else:
            card.interval = round(card.interval * card.easiness_factor)
        card.repetitions += 1
    else:
        card.repetitions = 0
        card.interval = 1

    card.easiness_factor = max(1.3, card.easiness_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    card.last_reviewed = date.today().isoformat()
    card.next_review = (date.today() + timedelta(days=card.interval)).isoformat()


async def spaced_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/takrorlash buyrug'i"""
    from handlers.payment import require_premium
    if not await require_premium(update, "🧠 Spaced Repetition"):
        return
    user_id = update.effective_user.id
    session = get_session()
    try:
        today = date.today().isoformat()

        # Bugun takrorlanishi kerak bo'lgan kartalar
        due_cards = (
            session.query(SpacedRepetition)
            .filter_by(user_id=user_id)
            .filter(SpacedRepetition.next_review <= today)
            .all()
        )

        # Yangi xatolarni qo'shish (hali takrorlash tizimida bo'lmagan)
        wrongs = session.query(WrongAnswer).filter_by(user_id=user_id, reviewed=False).all()
        existing_qids = {c.question_id for c in session.query(SpacedRepetition).filter_by(user_id=user_id).all()}

        new_added = 0
        for w in wrongs:
            if w.question_id not in existing_qids:
                sr = SpacedRepetition(
                    user_id=user_id,
                    question_id=w.question_id,
                    next_review=today,
                    last_reviewed="",
                )
                session.add(sr)
                existing_qids.add(w.question_id)
                new_added += 1
        session.commit()

        if new_added > 0:
            due_cards = (
                session.query(SpacedRepetition)
                .filter_by(user_id=user_id)
                .filter(SpacedRepetition.next_review <= today)
                .all()
            )

        total_cards = session.query(SpacedRepetition).filter_by(user_id=user_id).count()

        if not due_cards:
            next_card = (
                session.query(SpacedRepetition)
                .filter_by(user_id=user_id)
                .filter(SpacedRepetition.next_review > today)
                .order_by(SpacedRepetition.next_review)
                .first()
            )
            next_date = next_card.next_review if next_card else "—"

            await update.message.reply_text(
                f"🧠 <b>Spaced Repetition</b>\n\n"
                f"✅ Bugun takrorlanadigan savol yo'q!\n\n"
                f"📊 Jami kartalar: {total_cards}\n"
                f"📅 Keyingi takrorlash: {next_date}\n\n"
                f"💡 Test yechib xato qilsangiz, savollar avtomatik qo'shiladi.",
                parse_mode="HTML",
            )
            return

        # Takrorlashni boshlash
        context.user_data["spaced"] = {
            "card_ids": [c.id for c in due_cards],
            "question_ids": [c.question_id for c in due_cards],
            "current_index": 0,
            "correct": 0,
            "total": len(due_cards),
        }

        text = (
            f"🧠 <b>Spaced Repetition</b>\n\n"
            f"Bugun takrorlanadigan savollar: <b>{len(due_cards)}</b>\n"
            f"Jami kartalar: {total_cards}\n\n"
            f"Boshlaylik! 👇"
        )

        await update.message.reply_text(text, parse_mode="HTML")
        await _send_spaced_question(update, context, session)
    finally:
        session.close()


async def _send_spaced_question(update_or_query, context, session):
    spaced = context.user_data.get("spaced")
    if not spaced:
        return

    idx = spaced["current_index"]
    qid = spaced["question_ids"][idx]
    q = session.query(Question).get(qid)
    if not q:
        return

    s = session.query(Subject).get(q.subject_id)
    options = q.get_options()

    text = (
        f"🧠 <b>Takrorlash {idx + 1}/{spaced['total']}</b>\n"
        f"Bo'lim: {s.emoji} {s.name}\n\n"
        f"❓ {q.text}\n\n"
        f"🅰️ <b>A)</b> {options['a']}\n"
        f"🅱️ <b>B)</b> {options['b']}\n"
        f"🅲 <b>C)</b> {options['c']}\n"
        f"🅳 <b>D)</b> {options['d']}"
    )

    kb = answer_keyboard(q.id)
    if hasattr(update_or_query, 'message') and update_or_query.message:
        await update_or_query.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await update_or_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


async def spaced_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Spaced repetition javob"""
    query = update.callback_query
    spaced = context.user_data.get("spaced")
    if not spaced:
        return False

    parts = query.data.split("_")
    question_id = int(parts[1])
    if question_id not in spaced["question_ids"]:
        return False

    user_answer = parts[2]
    await query.answer()

    session = get_session()
    try:
        q = session.query(Question).get(question_id)
        is_correct = user_answer == q.correct_answer
        idx = spaced["question_ids"].index(question_id)
        card_id = spaced["card_ids"][idx]
        card = session.query(SpacedRepetition).get(card_id)

        if is_correct:
            spaced["correct"] += 1
            quality = 4  # Yaxshi
        else:
            quality = 1  # Yomon

        if card:
            _sm2_update(card, quality)
            session.commit()

        spaced["current_index"] += 1

        if spaced["current_index"] < spaced["total"]:
            correct_text = q.get_options()[q.correct_answer]
            if is_correct:
                result = f"✅ To'g'ri! Keyingi takrorlash: {card.next_review}"
            else:
                result = f"❌ Noto'g'ri! To'g'ri: {q.correct_answer.upper()}) {correct_text}\nErtaga yana takrorlanadi!"

            await query.edit_message_text(
                f"{result}\n\n⏳ Keyingi savol...",
                parse_mode="HTML",
            )
            await _send_spaced_question(query, context, session)
        else:
            correct = spaced["correct"]
            total = spaced["total"]
            text = (
                f"🧠 <b>Takrorlash tugadi!</b>\n\n"
                f"✅ To'g'ri: {correct}/{total}\n"
                f"📅 Qiyin savollar ertaga yana takrorlanadi\n"
                f"💪 Oson savollar keyinroq takrorlanadi"
            )
            keyboard = [[InlineKeyboardButton("🔙 Bosh sahifa", callback_data="back_subjects")]]
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            context.user_data.pop("spaced", None)

        return True
    finally:
        session.close()
