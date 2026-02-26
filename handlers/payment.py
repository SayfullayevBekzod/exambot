"""Premium obuna — admin tasdiqlash orqali"""
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import ADMIN_IDS, PREMIUM_PLANS
from database import get_session, UserSettings, PremiumSubscription, check_premium, User


PREMIUM_FEATURES = (
    "🎧 Audio Listening — eshitib tushunish mashqlari\n"
    "📊 PDF Sertifikat — natijani yuklab olish\n"
    "🧠 Spaced Repetition — ilmiy takrorlash (SM-2)\n"
    "🗂️ Flashcards — so'z kartochkalari\n"
    "📅 Study Plan — shaxsiy o'qish rejasi\n"
    "🎮 Speed Round — tezlik raqobati\n"
    "🌐 Tarjima rejimi — savollarni o'zbekchada ko'rish"
)

PREMIUM_LOCKED_TEXT = (
    "🔒 <b>Premium funksiya!</b>\n\n"
    "Bu funksiya faqat Premium obunachilarga ochiq.\n\n"
    f"{PREMIUM_FEATURES}\n\n"
    "👑 Premium olish uchun: /premium"
)

# To'lov ma'lumotlari (admin .env ga o'zi yozadi)
from config import PAYMENT_CARD_NUMBER, PAYMENT_CARD_HOLDER

PAYMENT_INFO = (
    "💳 <b>To'lov usullari:</b>\n\n"
    f"🏦 Karta raqami: <code>{PAYMENT_CARD_NUMBER}</code>\n"
    f"👤 Egasi: <b>{PAYMENT_CARD_HOLDER}</b>\n\n"
    "📱 Yoki Click/Payme orqali yuqoridagi kartaga o'tkazing."
)


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/premium buyrug'i — obuna holati va sotib olish"""
    user_id = update.effective_user.id
    is_prem = check_premium(user_id)

    if is_prem:
        session = get_session()
        try:
            sub = session.query(PremiumSubscription).filter_by(
                user_id=user_id, is_active=True
            ).order_by(PremiumSubscription.end_date.desc()).first()

            if sub:
                days_left = (sub.end_date - datetime.utcnow()).days
                expire_text = (
                    f"\n📅 Amal qilish: <b>{sub.end_date.strftime('%d.%m.%Y')}</b>"
                    f"\n⏳ Qolgan: <b>{days_left} kun</b>"
                )
            else:
                expire_text = "\n🎁 Cheksiz obuna (admin)"

            text = (
                "👑 <b>Premium Obunachi!</b>\n\n"
                "Sizda barcha premium funksiyalar mavjud:\n\n"
                f"{PREMIUM_FEATURES}"
                f"\n{expire_text}\n\n"
                "🎉 Premium obunangiz faol!"
            )
            keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")]]
        finally:
            session.close()
    else:
        text = (
            "👑 <b>Premium Obuna</b>\n\n"
            "Premium obuna bilan quyidagilarni oling:\n\n"
            f"{PREMIUM_FEATURES}\n\n"
            "💰 <b>Narxlar:</b>\n"
        )
        keyboard = []
        for key, plan in PREMIUM_PLANS.items():
            price_formatted = f"{plan['price']:,}".replace(",", " ")
            text += f"{plan['emoji']} {plan['label']}: <b>{price_formatted} so'm</b>\n"
            keyboard.append([InlineKeyboardButton(
                f"{plan['emoji']} {plan['label']} — {price_formatted} so'm",
                callback_data=f"buy_premium_{key}"
            )])
        text += "\n📌 Rejani tanlang va to'lov chekini yuboring!"
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")])

    await update.message.reply_text(
        text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def buy_premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obuna rejasi tanlash — to'lov ma'lumotlarini ko'rsatish"""
    query = update.callback_query
    await query.answer()

    plan_key = query.data.replace("buy_premium_", "")
    plan = PREMIUM_PLANS.get(plan_key)
    if not plan:
        await query.edit_message_text("❌ Noto'g'ri reja!")
        return

    price_formatted = f"{plan['price']:,}".replace(",", " ")

    # Session'ga pending plan saqlash
    context.user_data["pending_premium_plan"] = plan_key

    text = (
        f"👑 <b>Premium {plan['label']}</b>\n\n"
        f"💰 Narx: <b>{price_formatted} so'm</b>\n"
        f"📅 Muddat: <b>{plan['duration']} kun</b>\n\n"
        f"{PAYMENT_INFO}\n\n"
        "📸 <b>To'lovni amalga oshiring va chek (screenshot) yuboring!</b>\n\n"
        "⚠️ <i>Chekni shu chatga rasm sifatida yuboring.\n"
        "Admin tekshirib, premium aktivlashtiradi.</i>"
    )

    await query.edit_message_text(text, parse_mode="HTML")


async def handle_premium_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi to'lov chekini (rasm) yubordi — adminlarga forward qilish"""
    pending_plan = context.user_data.get("pending_premium_plan")
    if not pending_plan:
        # Agar rasm yuborsa lekin plan tanlamagan bo'lsa
        await update.message.reply_text(
            "📷 <b>Rasm qabul qilindi!</b>\n\n"
            "Agar bu premium uchun to'lov cheki bo'lsa, "
            "iltimos avval 👑 <b>/premium</b> buyrug'i orqali "
            "reja tanlang, keyin chekni yuboring.",
            parse_mode="HTML"
        )
        return

    plan = PREMIUM_PLANS.get(pending_plan)
    if not plan:
        return False

    user = update.effective_user
    price_formatted = f"{plan['price']:,}".replace(",", " ")

    # Foydalanuvchiga tasdiqlash
    await update.message.reply_text(
        "✅ <b>Xabar qabul qilindi!</b>\n\n"
        "📋 Admin tekshirib, premium aktivlashtiriladi.\n"
        "⏳ Odatda 1-24 soat ichida tasdiqlanadi.\n\n"
        "Sabr qiling! 🙏",
        parse_mode="HTML"
    )

    # Har bir adminga xabar yuborish
    for admin_id in ADMIN_IDS:
        try:
            # Chek rasmini adminlarga forward
            await update.message.forward(chat_id=admin_id)

            # Tasdiqlash tugmalari bilan ma'lumot
            keyboard = [
                [
                    InlineKeyboardButton(
                        "✅ Tasdiqlash",
                        callback_data=f"adm_approve_{user.id}_{pending_plan}"
                    ),
                    InlineKeyboardButton(
                        "❌ Rad etish",
                        callback_data=f"adm_reject_{user.id}_{pending_plan}"
                    ),
                ],
            ]

            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    "💳 <b>Yangi to'lov cheki!</b>\n\n"
                    f"👤 Foydalanuvchi: <b>{user.full_name}</b>\n"
                    f"🆔 ID: <code>{user.id}</code>\n"
                    f"📱 Username: @{user.username or 'yo`q'}\n\n"
                    f"👑 Reja: <b>Premium {plan['label']}</b>\n"
                    f"💰 Narx: <b>{price_formatted} so'm</b>\n"
                    f"📅 Muddat: <b>{plan['duration']} kun</b>\n\n"
                    "Tasdiqlaysizmi?"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"Admin {admin_id} ga xabar yuborishda xato: {e}")

    # Pending plan tozalash
    context.user_data.pop("pending_premium_plan", None)
    return True


async def admin_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin premium ni tasdiqladi"""
    query = update.callback_query
    admin_id = query.from_user.id

    if admin_id not in ADMIN_IDS:
        await query.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    # callback_data: adm_approve_123456789_1_month
    parts = query.data.split("_")
    # adm_approve_USER_ID_PLAN_KEY
    user_id = int(parts[2])
    plan_key = "_".join(parts[3:])  # 1_month, 3_months, 6_months

    plan = PREMIUM_PLANS.get(plan_key)
    if not plan:
        await query.answer("❌ Reja topilmadi!", show_alert=True)
        return

    session = get_session()
    try:
        now = datetime.utcnow()
        end_date = now + timedelta(days=plan["duration"])

        # Premium obunani saqlash
        subscription = PremiumSubscription(
            user_id=user_id,
            plan_key=plan_key,
            amount=plan["price"],
            payment_id=f"admin_approved_{admin_id}",
            provider_payment_id=f"manual_{now.strftime('%Y%m%d%H%M%S')}",
            start_date=now,
            end_date=end_date,
            is_active=True,
        )
        session.add(subscription)

        # UserSettings yangilash
        settings = session.query(UserSettings).filter_by(user_id=user_id).first()
        if not settings:
            settings = UserSettings(user_id=user_id)
            session.add(settings)
        settings.is_premium = True
        session.commit()

        # Admin xabarini yangilash
        await query.edit_message_text(
            query.message.text + "\n\n✅ <b>TASDIQLANDI!</b>"
            f"\n👨‍💼 Admin: {query.from_user.full_name}"
            f"\n📅 Tugash: {end_date.strftime('%d.%m.%Y')}",
            parse_mode="HTML"
        )

        # Foydalanuvchiga xabar
        price_formatted = f"{plan['price']:,}".replace(",", " ")
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 <b>Premium aktivlashtirildi!</b>\n\n"
                    f"👑 <b>Premium {plan['label']}</b>\n"
                    f"💰 {price_formatted} so'm\n"
                    f"📅 Boshlanish: <b>{now.strftime('%d.%m.%Y')}</b>\n"
                    f"📅 Tugash: <b>{end_date.strftime('%d.%m.%Y')}</b>\n\n"
                    f"✅ Barcha premium funksiyalar sizga ochiq!\n\n"
                    f"{PREMIUM_FEATURES}\n\n"
                    "IELTS tayyorlanishda omad! 🚀"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass

        await query.answer("✅ Premium tasdiqlandi!", show_alert=True)

    except Exception as e:
        session.rollback()
        import traceback
        err_tb = traceback.format_exc()
        print(f"Approval error: {e}\n{err_tb}")
        await query.answer(f"❌ Xato: {str(e)[:100]}", show_alert=True)
    finally:
        session.close()


async def admin_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin premium ni rad etdi"""
    query = update.callback_query
    admin_id = query.from_user.id

    if admin_id not in ADMIN_IDS:
        await query.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    parts = query.data.split("_")
    user_id = int(parts[2])
    plan_key = "_".join(parts[3:])

    # Admin xabarini yangilash
    await query.edit_message_text(
        query.message.text + "\n\n❌ <b>RAD ETILDI!</b>"
        f"\n👨‍💼 Admin: {query.from_user.full_name}",
        parse_mode="HTML"
    )

    # Foydalanuvchiga xabar
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "❌ <b>To'lov rad etildi</b>\n\n"
                "Sizning to'lov chekingiz admin tomonidan rad etildi.\n\n"
                "📌 Mumkin sabablar:\n"
                "• Noto'g'ri summa\n"
                "• Chek aniq ko'rinmaydi\n"
                "• To'lov amalga oshmagan\n\n"
                "Qayta urinib ko'ring: /premium"
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await query.answer("❌ Rad etildi!", show_alert=True)


# ==========================================
#  ADMIN PANEL
# ==========================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/admin buyrug'i — admin panel"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Siz admin emassiz!")
        return

    session = get_session()
    try:
        total_users = session.query(User).count()
        premium_users = session.query(UserSettings).filter_by(is_premium=True).count()
        active_subs = session.query(PremiumSubscription).filter_by(is_active=True).count()
    finally:
        session.close()

    keyboard = [
        [InlineKeyboardButton("👥 Foydalanuvchilar (Barcha)", callback_data="adm_users")],
        [InlineKeyboardButton("📝 Imtihon topshirganlar", callback_data="adm_quiz_users")],
        [InlineKeyboardButton("📊 To'liq statistika", callback_data="adm_full_stats")],
        [InlineKeyboardButton("👑 Premium berish", callback_data="adm_give_premium")],
        [InlineKeyboardButton("🚫 Premium olish", callback_data="adm_revoke_premium")],
    ]

    text = (
        "⚙️ <b>Admin Panel</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n"
        f"👑 Premium obunchilar: <b>{premium_users}</b>\n"
        f"📋 Faol obunalar: <b>{active_subs}</b>\n\n"
        "Boshqarish uchun tugmani tanlang:"
    )

    await update.message.reply_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchilar ro'yxatini ko'rsatish"""
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Admin emas!", show_alert=True)
        return
    await query.answer()

    session = get_session()
    try:
        # Oxirgi 50 ta foydalanuvchi
        users = session.query(User).order_by(User.id.desc()).limit(50).all()
        
        text = "👥 <b>Foydalanuvchilar (Oxirgi 50 ta):</b>\n\n"
        for u in users:
            # Premium holatini UserSettings dan olish kerak
            from database import UserSettings
            settings = session.query(UserSettings).filter_by(user_id=u.user_id).first()
            status = "👑" if settings and settings.is_premium else "👤"
            username = f" (@{u.username})" if u.username else ""
            text += f"{status} <code>{u.user_id}</code> - {u.full_name}{username}\n"
        
        if not users:
            text += "Foydalanuvchilar topilmadi."
            
    finally:
        session.close()

    keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="adm_back")]]
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_quiz_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Imtihon topshirgan foydalanuvchilar ro'yxati"""
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Admin emas!", show_alert=True)
        return
    await query.answer()

    from database import UserResult, User
    from sqlalchemy import func

    session = get_session()
    try:
        # UserResult bor userlarni yig'ish (user_id bo'yicha guruhlab)
        # Oxirgi 50 ta faol user (oxirgi marta test yechganiga ko'ra)
        quiz_users = session.query(
            User.user_id, User.full_name, User.username, func.count(UserResult.id).label('test_count')
        ).join(UserResult, User.user_id == UserResult.user_id)\
         .group_by(User.user_id, User.full_name, User.username)\
         .order_by(func.max(UserResult.completed_at).desc())\
         .limit(50).all()

        text = "📝 <b>Imtihon topshirganlar (Oxirgi 50 ta):</b>\n\n"
        for u_id, name, username, count in quiz_users:
            uname = f" (@{username})" if username else ""
            text += f"👤 <code>{u_id}</code> - {name}{uname} (<b>{count}</b> ta test)\n"

        if not quiz_users:
            text += "Hozircha hech kim imtihon topshirmadi."

    finally:
        session.close()

    keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="adm_back")]]
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_full_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Batafsil statistika"""
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Admin emas!", show_alert=True)
        return
    await query.answer()

    from database import Subject, Question, UserResult
    from sqlalchemy import func

    session = get_session()
    try:
        total_q = session.query(func.count(Question.id)).scalar()
        total_r = session.query(func.count(UserResult.id)).scalar()
        
        subjects = session.query(Subject).all()
        sub_text = ""
        for s in subjects:
            q_count = session.query(func.count(Question.id)).filter_by(subject_id=s.id).scalar()
            r_count = session.query(func.count(UserResult.id)).filter_by(subject_id=s.id).scalar()
            sub_text += f"{s.emoji} {s.name}: <b>{q_count} savol</b> ({r_count} marta yechilgan)\n"

        text = (
            "📊 <b>Batafsil Statistika</b>\n\n"
            f"❓ Jami savollar: <b>{total_q}</b>\n"
            f"📝 Jami yechilgan testlar: <b>{total_r}</b>\n\n"
            f"📚 <b>Bo'limlar bo'yicha:</b>\n{sub_text}"
        )
    finally:
        session.close()

    keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="adm_back")]]
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panelga qaytish"""
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Admin emas!", show_alert=True)
        return
    await query.answer()

    session = get_session()
    try:
        total_users = session.query(User).count()
        premium_users = session.query(UserSettings).filter_by(is_premium=True).count()
        active_subs = session.query(PremiumSubscription).filter_by(is_active=True).count()
    finally:
        session.close()

    keyboard = [
        [InlineKeyboardButton("👥 Foydalanuvchilar (Barcha)", callback_data="adm_users")],
        [InlineKeyboardButton("📝 Imtihon topshirganlar", callback_data="adm_quiz_users")],
        [InlineKeyboardButton("📊 To'liq statistika", callback_data="adm_full_stats")],
        [InlineKeyboardButton("👑 Premium berish", callback_data="adm_give_premium")],
        [InlineKeyboardButton("🚫 Premium olish", callback_data="adm_revoke_premium")],
    ]

    text = (
        "⚙️ <b>Admin Panel</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n"
        f"👑 Premium obunchilar: <b>{premium_users}</b>\n"
        f"📋 Faol obunalar: <b>{active_subs}</b>\n\n"
        "Tanlang:"
    )

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_give_premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin to'g'ridan-to'g'ri premium berish"""
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Admin emas!", show_alert=True)
        return
    await query.answer()

    context.user_data["admin_action"] = "give_premium"

    await query.edit_message_text(
        "👑 <b>Premium berish</b>\n\n"
        "Foydalanuvchi ID sini yuboring:\n\n"
        "<i>Masalan: 1258119183</i>",
        parse_mode="HTML"
    )


async def admin_revoke_premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin premium olib tashlash"""
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Admin emas!", show_alert=True)
        return
    await query.answer()

    context.user_data["admin_action"] = "revoke_premium"

    await query.edit_message_text(
        "🚫 <b>Premium olib tashlash</b>\n\n"
        "Foydalanuvchi ID sini yuboring:\n\n"
        "<i>Masalan: 1258119183</i>",
        parse_mode="HTML"
    )


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Admin text input handler — give/revoke premium"""
    admin_action = context.user_data.get("admin_action")
    if not admin_action:
        return False

    if update.effective_user.id not in ADMIN_IDS:
        return False

    text = update.message.text.strip()

    # give_premium: ID yuborildi
    if admin_action == "give_premium":
        try:
            target_id = int(text)
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri ID! Raqam yuboring.")
            return True

        # Premium rejani tanlash
        context.user_data["admin_target_id"] = target_id
        context.user_data.pop("admin_action", None)

        keyboard = []
        for key, plan in PREMIUM_PLANS.items():
            keyboard.append([InlineKeyboardButton(
                f"{plan['emoji']} {plan['label']} ({plan['duration']} kun)",
                callback_data=f"adm_setprem_{target_id}_{key}"
            )])

        await update.message.reply_text(
            f"👑 <b>Premium berish</b>\n\n"
            f"🆔 ID: <code>{target_id}</code>\n\n"
            "Rejani tanlang:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return True

    # revoke_premium: ID yuborildi
    elif admin_action == "revoke_premium":
        try:
            target_id = int(text)
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri ID! Raqam yuboring.")
            return True

        context.user_data.pop("admin_action", None)

        session = get_session()
        try:
            settings = session.query(UserSettings).filter_by(user_id=target_id).first()
            if settings:
                settings.is_premium = False
            # Faol obunalarni bekor qilish
            subs = session.query(PremiumSubscription).filter_by(
                user_id=target_id, is_active=True
            ).all()
            for sub in subs:
                sub.is_active = False
            session.commit()

            await update.message.reply_text(
                f"🚫 <b>Premium olib tashlandi!</b>\n\n"
                f"🆔 ID: <code>{target_id}</code>",
                parse_mode="HTML"
            )
        except Exception as e:
            session.rollback()
            await update.message.reply_text(f"❌ Xato: {e}")
        finally:
            session.close()
        return True

    return False


async def admin_set_premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin premium reja tanladi — aktivlashtirish"""
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Admin emas!", show_alert=True)
        return

    # adm_setprem_USER_ID_PLAN_KEY
    parts = query.data.split("_")
    target_id = int(parts[2])
    plan_key = "_".join(parts[3:])

    plan = PREMIUM_PLANS.get(plan_key)
    if not plan:
        await query.answer("❌ Reja topilmadi!", show_alert=True)
        return

    session = get_session()
    try:
        now = datetime.utcnow()
        end_date = now + timedelta(days=plan["duration"])

        subscription = PremiumSubscription(
            user_id=target_id,
            plan_key=plan_key,
            amount=0,
            payment_id=f"admin_granted_{query.from_user.id}",
            provider_payment_id=f"manual_{now.strftime('%Y%m%d%H%M%S')}",
            start_date=now,
            end_date=end_date,
            is_active=True,
        )
        session.add(subscription)

        settings = session.query(UserSettings).filter_by(user_id=target_id).first()
        if not settings:
            settings = UserSettings(user_id=target_id)
            session.add(settings)
        settings.is_premium = True
        session.commit()

        await query.edit_message_text(
            f"✅ <b>Premium berildi!</b>\n\n"
            f"🆔 ID: <code>{target_id}</code>\n"
            f"👑 Reja: <b>{plan['label']}</b>\n"
            f"📅 Tugash: <b>{end_date.strftime('%d.%m.%Y')}</b>",
            parse_mode="HTML"
        )

        # Foydalanuvchiga xabar
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    "🎉 <b>Premium aktivlashtirildi!</b>\n\n"
                    f"👑 <b>Premium {plan['label']}</b> admin tomonidan berildi.\n\n"
                    f"📅 Tugash: <b>{end_date.strftime('%d.%m.%Y')}</b>\n\n"
                    f"{PREMIUM_FEATURES}\n\n"
                    "IELTS tayyorlanishda omad! 🚀"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass

        await query.answer("✅ Premium berildi!", show_alert=True)
    except Exception as e:
        session.rollback()
        await query.answer(f"❌ Xato: {e}", show_alert=True)
    finally:
        session.close()


async def require_premium(update: Update, feature_name: str = "") -> bool:
    """Premium tekshirish — False qaytarsa, handler to'xtashi kerak"""
    user_id = update.effective_user.id
    if check_premium(user_id):
        return True

    keyboard = [[InlineKeyboardButton("👑 Premium olish", callback_data="go_premium")]]
    text = PREMIUM_LOCKED_TEXT
    if feature_name:
        text = f"🔒 <b>{feature_name}</b> — Premium funksiya!\n\n" + text.split("\n\n", 1)[1]

    if update.callback_query:
        await update.callback_query.answer("🔒 Premium kerak!", show_alert=True)
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.message:
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    return False


async def go_premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔒 dan /premium ga o'tish"""
    query = update.callback_query
    await query.answer()

    text = (
        "👑 <b>Premium Obuna</b>\n\n"
        "Premium obuna bilan quyidagilarni oling:\n\n"
        f"{PREMIUM_FEATURES}\n\n"
        "💰 <b>Narxlar:</b>\n"
    )
    keyboard = []
    for key, plan in PREMIUM_PLANS.items():
        price_formatted = f"{plan['price']:,}".replace(",", " ")
        text += f"{plan['emoji']} {plan['label']}: <b>{price_formatted} so'm</b>\n"
        keyboard.append([InlineKeyboardButton(
            f"{plan['emoji']} {plan['label']} — {price_formatted} so'm",
            callback_data=f"buy_premium_{key}"
        )])
    text += "\n📌 Rejani tanlang va to'lov chekini yuboring!"
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
