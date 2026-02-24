"""Stats va Band Score Tracker"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import func, desc

from database import get_session, UserResult, Subject, DailyStreak


async def my_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/natijalarim buyrug'i"""
    user_id = update.effective_user.id
    text = await _build_stats_text(user_id)
    keyboard = [
        [InlineKeyboardButton("📈 Band Score tarix", callback_data="band_history")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
    ]
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def my_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stats callback"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    text = await _build_stats_text(user_id)
    keyboard = [
        [InlineKeyboardButton("📈 Band Score tarix", callback_data="band_history")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
    ]
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def _build_stats_text(user_id):
    session = get_session()
    try:
        results = session.query(UserResult).filter_by(user_id=user_id).all()
        if not results:
            return "📊 <b>Natijalarim</b>\n\nSiz hali test yechmadingiz. /bolimlar ni bosing!"

        total_tests = len(results)
        avg_pct = sum(r.percentage for r in results) / total_tests
        best = max(results, key=lambda r: r.percentage)
        mock_count = sum(1 for r in results if r.is_mock)

        # Band score
        band = _percentage_to_band(avg_pct)

        # Streak
        streak = session.query(DailyStreak).filter_by(user_id=user_id).first()
        streak_text = f"🔥 {streak.current_streak} kun" if streak else "0 kun"
        longest = f"⭐ {streak.longest_streak} kun" if streak else "0 kun"

        # Bo'limlarni bir marta yuklash (N+1 muammosini hal qilish)
        all_subjects = {s.id: s for s in session.query(Subject).all()}

        text = (
            f"📊 <b>Mening natijalarim</b>\n\n"
            f"🎯 O'rtacha: <b>{avg_pct:.1f}%</b> (Band {band})\n"
            f"📝 Jami testlar: <b>{total_tests}</b>\n"
            f"📋 Mock testlar: <b>{mock_count}</b>\n"
            f"🏆 Eng yaxshi: <b>{best.percentage:.0f}%</b>\n\n"
            f"🔥 Joriy streak: {streak_text}\n"
            f"⭐ Eng uzun: {longest}\n"
            f"\n{'─' * 25}\n"
            f"📚 <b>Bo'limlar bo'yicha:</b>\n\n"
        )

        # Bo'limlar bo'yicha tahlil
        subject_stats = {}
        for r in results:
            sid = r.subject_id
            if sid not in subject_stats:
                s = all_subjects.get(sid)
                subject_stats[sid] = {
                    "name": f"{s.emoji} {s.name}" if s else "?",
                    "tests": 0,
                    "total_pct": 0,
                    "best": 0,
                }
            subject_stats[sid]["tests"] += 1
            subject_stats[sid]["total_pct"] += r.percentage
            subject_stats[sid]["best"] = max(subject_stats[sid]["best"], r.percentage)

        for sid, info in sorted(subject_stats.items()):
            avg = info["total_pct"] / info["tests"]
            text += (
                f"  {info['name']}\n"
                f"    Tests: {info['tests']} | O'rtacha: {avg:.0f}% | Eng yaxshi: {info['best']:.0f}%\n\n"
            )

        return text
    finally:
        session.close()


async def band_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Band Score tarix — oxirgi 10 ta test"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    session = get_session()
    try:
        results = (
            session.query(UserResult)
            .filter_by(user_id=user_id)
            .order_by(desc(UserResult.completed_at))
            .limit(15)
            .all()
        )

        if not results:
            await query.edit_message_text("📈 Hali natijalar yo'q!")
            return

        text = "📈 <b>Band Score tarix</b>\n\n"

        for i, r in enumerate(results, 1):
            s = session.query(Subject).get(r.subject_id)
            s_name = f"{s.emoji}" if s else "?"
            band = _percentage_to_band(r.percentage)
            bar = _mini_bar(r.percentage)
            mock_tag = " 📋" if r.is_mock else ""
            diff_tag = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(r.difficulty_level, "")
            date_str = r.completed_at.strftime("%d.%m %H:%M") if r.completed_at else ""

            text += f"{i}. {s_name} {diff_tag} {bar} {r.percentage:.0f}% (Band {band}){mock_tag} — {date_str}\n"

        # Trend hisoblash
        if len(results) >= 2:
            recent_avg = sum(r.percentage for r in results[:5]) / min(5, len(results))
            older_idx = min(5, len(results))
            older = results[older_idx:]
            if older:
                older_avg = sum(r.percentage for r in older) / len(older)
                diff = recent_avg - older_avg
                if diff > 0:
                    text += f"\n📈 Trend: <b>+{diff:.1f}%</b> ↗️ Yaxshilanmoqda!"
                elif diff < -2:
                    text += f"\n📉 Trend: <b>{diff:.1f}%</b> ↘️ Ko'proq mashq qiling!"
                else:
                    text += f"\n➡️ Trend: Barqaror"

        keyboard = [
            [InlineKeyboardButton("📊 Umumiy natijalar", callback_data="my_stats")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
        ]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reyting buyrug'i"""
    text = _build_leaderboard()
    keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")]]
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reyting callback"""
    query = update.callback_query
    await query.answer()
    text = _build_leaderboard()
    keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")]]
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


def _build_leaderboard():
    session = get_session()
    try:
        leaderboard = (
            session.query(
                UserResult.user_id,
                func.max(UserResult.full_name).label("full_name"),
                func.avg(UserResult.percentage).label("avg_pct"),
                func.count(UserResult.id).label("test_count"),
            )
            .group_by(UserResult.user_id)
            .order_by(desc("avg_pct"))
            .limit(10)
            .all()
        )

        if not leaderboard:
            return "🏆 <b>Reyting</b>\n\nHali hech kim test yechmagan!"

        medals = ["🥇", "🥈", "🥉"]
        text = "🏆 <b>IELTS Reyting — Top 10</b>\n\n"

        for i, row in enumerate(leaderboard):
            medal = medals[i] if i < 3 else f"{i + 1}."
            band = _percentage_to_band(row.avg_pct)
            name = row.full_name or "Foydalanuvchi"
            text += f"{medal} <b>{name}</b> — {row.avg_pct:.0f}% (Band {band}) [{row.test_count} test]\n"

        return text
    finally:
        session.close()


def _percentage_to_band(pct):
    if pct >= 90:
        return "8.0-9.0"
    elif pct >= 75:
        return "6.5-7.5"
    elif pct >= 60:
        return "5.5-6.0"
    elif pct >= 40:
        return "4.5-5.0"
    else:
        return "3.0-4.0"


def _mini_bar(pct):
    filled = round(5 * pct / 100)
    return "▓" * filled + "░" * (5 - filled)
