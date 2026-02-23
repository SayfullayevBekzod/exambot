"""Quiz handler — difficulty, timer, mock test + spaced/speed intercept"""
import random
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import QUESTIONS_PER_QUIZ
from database import get_session, Subject, Question, UserResult, WrongAnswer
from keyboards.inline import answer_keyboard, quiz_complete_keyboard, back_to_subjects_keyboard


async def subject_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_id = int(query.data.split("_")[1])
    context.user_data["selected_subject_id"] = subject_id

    keyboard = [
        [InlineKeyboardButton("🟢 Easy", callback_data=f"diff_{subject_id}_easy")],
        [InlineKeyboardButton("🟡 Medium", callback_data=f"diff_{subject_id}_medium")],
        [InlineKeyboardButton("🔴 Hard", callback_data=f"diff_{subject_id}_hard")],
        [InlineKeyboardButton("🎯 Barcha", callback_data=f"diff_{subject_id}_all")],
        [InlineKeyboardButton("📋 Mock Test (40 savol)", callback_data=f"mock_{subject_id}")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
    ]

    session = get_session()
    try:
        subject = session.query(Subject).get(subject_id)
        if not subject:
            await query.edit_message_text("❌ Bo'lim topilmadi!")
            return

        easy = session.query(Question).filter_by(subject_id=subject_id, difficulty=1).count()
        medium = session.query(Question).filter_by(subject_id=subject_id, difficulty=2).count()
        hard = session.query(Question).filter_by(subject_id=subject_id, difficulty=3).count()
        total = easy + medium + hard

        text = (
            f"{subject.emoji} <b>{subject.name}</b>\n\n"
            f"📊 Savollar: {total} ta\n"
            f"🟢 {easy} | 🟡 {medium} | 🔴 {hard}\n\n"
            f"Qiyinlikni tanlang:"
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()


async def difficulty_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    subject_id = int(parts[1])
    difficulty = parts[2]
    await _start_quiz(query, context, subject_id, difficulty, is_mock=False)


async def mock_test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_id = int(query.data.split("_")[1])
    await _start_quiz(query, context, subject_id, "all", is_mock=True)


async def _start_quiz(query, context, subject_id, difficulty, is_mock=False):
    session = get_session()
    try:
        subject = session.query(Subject).get(subject_id)
        if not subject:
            await query.edit_message_text("❌ Bo'lim topilmadi!")
            return

        q_query = session.query(Question).filter_by(subject_id=subject_id)
        if difficulty != "all":
            diff_map = {"easy": 1, "medium": 2, "hard": 3}
            q_query = q_query.filter_by(difficulty=diff_map.get(difficulty, 1))

        questions = q_query.all()
        if not questions:
            await query.edit_message_text(
                f"😔 Savollar topilmadi.",
                reply_markup=back_to_subjects_keyboard(),
            )
            return

        count = min(40 if is_mock else QUESTIONS_PER_QUIZ, len(questions))
        selected = random.sample(questions, count)

        context.user_data["quiz"] = {
            "subject_id": subject_id,
            "subject_name": subject.name,
            "subject_emoji": subject.emoji,
            "questions": [q.id for q in selected],
            "current_index": 0,
            "score": 0,
            "total": count,
            "answers": [],
            "difficulty": difficulty,
            "is_mock": is_mock,
        }

        test_type = "📋 MOCK TEST" if is_mock else "📝 Test"
        diff_labels = {"easy": "🟢 Easy", "medium": "🟡 Medium", "hard": "🔴 Hard", "all": "🎯 Barcha"}

        await query.edit_message_text(
            f"{test_type} boshlanmoqda!\n\n"
            f"Bo'lim: {subject.emoji} <b>{subject.name}</b>\n"
            f"Daraja: <b>{diff_labels.get(difficulty, difficulty)}</b>\n"
            f"Savollar: <b>{count}</b>\n"
            f"⏱️ Har bir savol: <b>30 soniya</b>",
            parse_mode="HTML",
        )

        await _send_quiz_question(query, context)
    finally:
        session.close()


async def _send_quiz_question(query, context):
    quiz = context.user_data.get("quiz")
    if not quiz:
        return

    idx = quiz["current_index"]
    qid = quiz["questions"][idx]

    session = get_session()
    try:
        q = session.query(Question).get(qid)
        if not q:
            return

        options = q.get_options()
        diff_emoji = {1: "🟢", 2: "🟡", 3: "🔴"}.get(q.difficulty, "⭐")

        text = (
            f"📌 <b>Savol {idx + 1}/{quiz['total']}</b> {diff_emoji}\n"
            f"⏱️ 30 soniya\n\n"
            f"❓ {q.text}\n\n"
            f"🅰️ <b>A)</b> {options['a']}\n"
            f"🅱️ <b>B)</b> {options['b']}\n"
            f"🅲 <b>C)</b> {options['c']}\n"
            f"🅳 <b>D)</b> {options['d']}"
        )

        # Tarjima rejimi
        from database import UserSettings
        user_id = query.from_user.id if hasattr(query, 'from_user') else 0
        settings = session.query(UserSettings).filter_by(user_id=user_id).first()
        if settings and settings.translation_mode and q.text_uz:
            text += f"\n\n🌐 <i>{q.text_uz}</i>"

        kb = answer_keyboard(q.id)
        await query.message.reply_text(text, parse_mode="HTML", reply_markup=kb)

        # Timer
        if context.job_queue:
            jobs = context.job_queue.get_jobs_by_name(f"timer_{user_id}")
            for job in jobs:
                job.schedule_removal()
            context.job_queue.run_once(
                _timer_expired, 30,
                data={"user_id": user_id, "question_id": qid, "chat_id": query.message.chat_id, "message_id": None},
                name=f"timer_{user_id}",
            )
    finally:
        session.close()


async def _timer_expired(context: ContextTypes.DEFAULT_TYPE):
    try:
        data = context.job.data
        if data.get("chat_id"):
            await context.bot.send_message(
                chat_id=data["chat_id"],
                text="⏱️ <b>Vaqt tugadi!</b> Keyingi savolga o'ting.",
                parse_mode="HTML",
            )
    except Exception:
        pass


async def answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Spaced repetition tekshirish
    if context.user_data.get("spaced"):
        from handlers.spaced import spaced_answer_callback
        handled = await spaced_answer_callback(update, context)
        if handled:
            return

    # Speed round tekshirish
    if context.user_data.get("speed"):
        from handlers.extras import speed_answer_callback
        handled = await speed_answer_callback(update, context)
        if handled:
            return

    # Mistakes review tekshirish
    if context.user_data.get("mistake_review"):
        from handlers.mistakes import mistake_answer_callback
        handled = await mistake_answer_callback(update, context)
        if handled:
            return

    quiz = context.user_data.get("quiz")
    if not quiz:
        await query.answer("⚠️ Aktiv test topilmadi. /start ni bosing.", show_alert=True)
        return

    parts = query.data.split("_")
    question_id = int(parts[1])
    user_answer = parts[2]

    if any(a["question_id"] == question_id for a in quiz.get("answers", [])):
        await query.answer("⚠️ Bu savolga allaqachon javob berdingiz!", show_alert=True)
        return

    # Timer bekor
    if context.job_queue:
        user_id = query.from_user.id
        jobs = context.job_queue.get_jobs_by_name(f"timer_{user_id}")
        for job in jobs:
            job.schedule_removal()

    session = get_session()
    try:
        q = session.query(Question).get(question_id)
        if not q:
            await query.answer("❌ Savol topilmadi!")
            return

        is_correct = user_answer == q.correct_answer
        correct_text = q.get_options()[q.correct_answer]

        if is_correct:
            quiz["score"] += 1
        else:
            wrong = WrongAnswer(
                user_id=query.from_user.id,
                question_id=question_id,
                user_answer=user_answer,
                correct_answer=q.correct_answer,
            )
            session.add(wrong)
            session.commit()

        quiz["answers"].append({
            "question_id": question_id,
            "user_answer": user_answer,
            "correct_answer": q.correct_answer,
            "is_correct": is_correct,
        })

        await query.answer("✅ To'g'ri!" if is_correct else "❌ Noto'g'ri!")

        if is_correct:
            result_text = "✅ <b>To'g'ri!</b> 🎉"
        else:
            result_text = f"❌ <b>Noto'g'ri!</b>\n✅ To'g'ri: {q.correct_answer.upper()}) {correct_text}"

        quiz["current_index"] += 1

        if quiz["current_index"] < quiz["total"]:
            next_qid = quiz["questions"][quiz["current_index"]]
            next_q = session.query(Question).get(next_qid)
            next_opts = next_q.get_options()
            diff_emoji = {1: "🟢", 2: "🟡", 3: "🔴"}.get(next_q.difficulty, "⭐")

            progress = _progress_bar(quiz["current_index"], quiz["total"])

            text = (
                f"{result_text}\n"
                f"📊 {quiz['score']}/{quiz['current_index']} to'g'ri  {progress}\n"
                f"{'─' * 25}\n\n"
                f"📌 <b>Savol {quiz['current_index'] + 1}/{quiz['total']}</b> {diff_emoji}\n"
                f"⏱️ 30 soniya\n\n"
                f"❓ {next_q.text}\n\n"
                f"🅰️ <b>A)</b> {next_opts['a']}\n"
                f"🅱️ <b>B)</b> {next_opts['b']}\n"
                f"🅲 <b>C)</b> {next_opts['c']}\n"
                f"🅳 <b>D)</b> {next_opts['d']}"
            )

            kb = answer_keyboard(next_q.id)
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

            # Timer
            if context.job_queue:
                context.job_queue.run_once(
                    _timer_expired, 30,
                    data={"user_id": query.from_user.id, "question_id": next_q.id, "chat_id": query.message.chat_id},
                    name=f"timer_{query.from_user.id}",
                )
        else:
            await _finish_quiz(query, context, session)
    finally:
        session.close()


async def _finish_quiz(query, context, session):
    quiz = context.user_data.get("quiz")
    if not quiz:
        return

    score = quiz["score"]
    total = quiz["total"]
    percentage = (score / total * 100) if total > 0 else 0

    user = query.from_user
    result = UserResult(
        user_id=user.id, username=user.username or "", full_name=user.full_name or "",
        subject_id=quiz["subject_id"], score=score, total=total, percentage=percentage,
        difficulty_level=quiz.get("difficulty", "all"), is_mock=quiz.get("is_mock", False),
    )
    session.add(result)
    session.commit()

    from handlers.achievements import update_streak, check_and_award_achievements
    update_streak(user.id)
    await check_and_award_achievements(user.id, context)

    if percentage >= 90:
        grade_emoji, band, grade_text = "🏆", "8.0-9.0", "Mukammal daraja!"
    elif percentage >= 75:
        grade_emoji, band, grade_text = "🥇", "6.5-7.5", "Yaxshi daraja!"
    elif percentage >= 60:
        grade_emoji, band, grade_text = "🥈", "5.5-6.0", "O'rtacha daraja"
    elif percentage >= 40:
        grade_emoji, band, grade_text = "🥉", "4.5-5.0", "Ko'proq mashq qiling!"
    else:
        grade_emoji, band, grade_text = "📖", "3.0-4.0", "Tayyorlanish kerak!"

    progress = _progress_bar(score, total)
    test_type = "📋 MOCK TEST" if quiz.get("is_mock") else "📝 Test"
    diff_labels = {"easy": "🟢 Easy", "medium": "🟡 Medium", "hard": "🔴 Hard", "all": "🎯 Barcha"}

    text = (
        f"🏁 <b>{test_type} tugadi!</b>\n\n"
        f"Bo'lim: {quiz['subject_emoji']} <b>{quiz['subject_name']}</b>\n"
        f"Daraja: {diff_labels.get(quiz.get('difficulty', 'all'), 'all')}\n\n"
        f"{grade_emoji} <b>Band {band} — {grade_text}</b>\n\n"
        f"📊 <b>Natija:</b> {score}/{total} ({percentage:.0f}%)\n"
        f"{progress}\n\n"
        f"✅ To'g'ri: {score} | ❌ Noto'g'ri: {total - score}\n\n"
        f"📊 Sertifikat olish: /sertifikat"
    )

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=quiz_complete_keyboard())
    context.user_data.pop("quiz", None)


def _progress_bar(current, total, length=10):
    if total == 0:
        return ""
    filled = round(length * current / total)
    return f"[{'🟩' * filled}{'⬜' * (length - filled)}] {current}/{total}"
