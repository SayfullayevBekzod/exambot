"""Achievement badges tizimi"""
from datetime import datetime, date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_session, UserAchievement, UserResult, DailyStreak, WrongAnswer
from sqlalchemy import func


# Barcha achievementlar
ACHIEVEMENTS = {
    "first_test": {"name": "Birinchi qadam", "emoji": "🎯", "desc": "Birinchi testni yechish"},
    "ten_tests": {"name": "Faol o'quvchi", "emoji": "📚", "desc": "10 ta test yechish"},
    "fifty_tests": {"name": "IELTS Warrior", "emoji": "⚔️", "desc": "50 ta test yechish"},
    "hundred_tests": {"name": "IELTS Master", "emoji": "👑", "desc": "100 ta test yechish"},
    "perfect_score": {"name": "Mukammal!", "emoji": "💯", "desc": "100% natija olish"},
    "band_7": {"name": "Band 7+", "emoji": "🥇", "desc": "75%+ natija olish"},
    "streak_3": {"name": "3 kun ketma-ket", "emoji": "🔥", "desc": "3 kun ketma-ket test yechish"},
    "streak_7": {"name": "Haftalik streak", "emoji": "🌟", "desc": "7 kun ketma-ket test yechish"},
    "streak_30": {"name": "Oylik streak", "emoji": "💎", "desc": "30 kun ketma-ket test yechish"},
    "all_sections": {"name": "Universal", "emoji": "🌍", "desc": "Barcha bo'limlardan test yechish"},
    "mistake_fixer": {"name": "Xatolardan o'rganuvchi", "emoji": "🔧", "desc": "10 ta xatoni tuzatish"},
    "mock_master": {"name": "Mock Test Master", "emoji": "🏆", "desc": "Mock testni 70%+ yechish"},
}


async def achievements_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/yutuqlar buyrug'i"""
    user_id = update.effective_user.id
    session = get_session()
    try:
        earned = session.query(UserAchievement).filter_by(user_id=user_id).all()
        earned_keys = {a.achievement_key for a in earned}

        text = "🏅 <b>Yutuqlar (Achievements)</b>\n\n"

        if earned:
            text += f"✅ Qo'lga kiritilgan: <b>{len(earned)}/{len(ACHIEVEMENTS)}</b>\n\n"
            for a in earned:
                date_str = a.earned_at.strftime("%d.%m.%Y") if a.earned_at else ""
                text += f"  {a.achievement_emoji} <b>{a.achievement_name}</b> — {date_str}\n"
        else:
            text += "Hali yutuqlar yo'q. Test yechishni boshlang! 💪\n"

        # Qolgan achievementlar
        remaining = [v for k, v in ACHIEVEMENTS.items() if k not in earned_keys]
        if remaining:
            text += f"\n{'─' * 25}\n🔒 <b>Qolganlar ({len(remaining)}):</b>\n\n"
            for r in remaining[:6]:
                text += f"  🔒 {r['emoji']} {r['name']} — <i>{r['desc']}</i>\n"
            if len(remaining) > 6:
                text += f"  ... va yana {len(remaining) - 6} ta\n"

        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")]]
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        session.close()


async def check_and_award_achievements(user_id, context):
    """Yangi achievement tekshirish va berish"""
    session = get_session()
    new_achievements = []
    try:
        earned_keys = {
            a.achievement_key
            for a in session.query(UserAchievement).filter_by(user_id=user_id).all()
        }

        total_tests = session.query(func.count(UserResult.id)).filter_by(user_id=user_id).scalar() or 0

        # Test count achievements
        for key, count in [("first_test", 1), ("ten_tests", 10), ("fifty_tests", 50), ("hundred_tests", 100)]:
            if key not in earned_keys and total_tests >= count:
                new_achievements.append(key)

        # Perfect score
        if "perfect_score" not in earned_keys:
            perfect = session.query(UserResult).filter_by(user_id=user_id).filter(UserResult.percentage >= 100).first()
            if perfect:
                new_achievements.append("perfect_score")

        # Band 7+
        if "band_7" not in earned_keys:
            band7 = session.query(UserResult).filter_by(user_id=user_id).filter(UserResult.percentage >= 75).first()
            if band7:
                new_achievements.append("band_7")

        # All sections
        if "all_sections" not in earned_keys:
            unique_subjects = session.query(func.count(func.distinct(UserResult.subject_id))).filter_by(user_id=user_id).scalar() or 0
            from database import Subject
            total_subjects = session.query(func.count(Subject.id)).scalar() or 0
            if total_subjects > 0 and unique_subjects >= total_subjects:
                new_achievements.append("all_sections")

        # Streaks
        streak = session.query(DailyStreak).filter_by(user_id=user_id).first()
        if streak:
            for key, days in [("streak_3", 3), ("streak_7", 7), ("streak_30", 30)]:
                if key not in earned_keys and streak.current_streak >= days:
                    new_achievements.append(key)

        # Mistake fixer
        if "mistake_fixer" not in earned_keys:
            fixed = session.query(func.count(WrongAnswer.id)).filter_by(user_id=user_id, reviewed=True).scalar() or 0
            if fixed >= 10:
                new_achievements.append("mistake_fixer")

        # Mock master
        if "mock_master" not in earned_keys:
            mock_pass = session.query(UserResult).filter_by(user_id=user_id, is_mock=True).filter(UserResult.percentage >= 70).first()
            if mock_pass:
                new_achievements.append("mock_master")

        # Award new achievements
        for key in new_achievements:
            info = ACHIEVEMENTS[key]
            ua = UserAchievement(
                user_id=user_id,
                achievement_key=key,
                achievement_name=info["name"],
                achievement_emoji=info["emoji"],
            )
            session.add(ua)

        session.commit()

        # Notify user
        for key in new_achievements:
            info = ACHIEVEMENTS[key]
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 <b>Yangi yutuq!</b>\n\n{info['emoji']} <b>{info['name']}</b>\n{info['desc']}",
                    parse_mode="HTML",
                )
            except Exception:
                pass

        return new_achievements
    finally:
        session.close()


def update_streak(user_id):
    """Kundalik streak yangilash"""
    session = get_session()
    try:
        streak = session.query(DailyStreak).filter_by(user_id=user_id).first()
        today = date.today().isoformat()

        if not streak:
            streak = DailyStreak(user_id=user_id, current_streak=1, longest_streak=1, last_active_date=today, total_tests=1)
            session.add(streak)
        else:
            streak.total_tests += 1
            if streak.last_active_date == today:
                pass  # Bugun allaqachon test yechgan
            elif streak.last_active_date == date.today().replace(day=date.today().day - 1).isoformat() if date.today().day > 1 else "":
                streak.current_streak += 1
            else:
                from datetime import timedelta
                yesterday = (date.today() - timedelta(days=1)).isoformat()
                if streak.last_active_date == yesterday:
                    streak.current_streak += 1
                else:
                    streak.current_streak = 1

            streak.longest_streak = max(streak.longest_streak, streak.current_streak)
            streak.last_active_date = today

        session.commit()
    finally:
        session.close()
