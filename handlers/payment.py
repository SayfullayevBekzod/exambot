"""Click to'lov tizimi orqali Premium obuna — Telegram Payments API"""
from datetime import datetime, timedelta

from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import CLICK_PROVIDER_TOKEN, PREMIUM_PLANS
from database import get_session, UserSettings, PremiumSubscription, check_premium


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


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/premium buyrug'i — obuna holati va sotib olish"""
    user_id = update.effective_user.id
    is_prem = check_premium(user_id)

    if is_prem:
        # Obuna ma'lumotlari
        session = get_session()
        try:
            sub = session.query(PremiumSubscription).filter_by(
                user_id=user_id, is_active=True
            ).order_by(PremiumSubscription.end_date.desc()).first()

            if sub:
                days_left = (sub.end_date - datetime.utcnow()).days
                expire_text = f"\n📅 Amal qilish muddati: <b>{sub.end_date.strftime('%d.%m.%Y')}</b>\n⏳ Qolgan kunlar: <b>{days_left} kun</b>"
            else:
                expire_text = "\n🎁 Cheksiz obuna (admin)"

            text = (
                "👑 <b>Premium Obunachi!</b>\n\n"
                "Sizda barcha premium funksiyalar mavjud:\n\n"
                f"✅ {PREMIUM_FEATURES.replace('🎧', '✅ 🎧').replace('📊', '✅ 📊').replace('🧠', '✅ 🧠').replace('🗂️', '✅ 🗂️').replace('📅', '✅ 📅').replace('🎮', '✅ 🎮').replace('🌐', '✅ 🌐')}"
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
        text += "\n💳 To'lov: <b>Click</b>"
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")])

    await update.message.reply_text(
        text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def buy_premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obuna rejasini tanlash va invoice yuborish"""
    query = update.callback_query
    await query.answer()

    plan_key = query.data.replace("buy_premium_", "")
    plan = PREMIUM_PLANS.get(plan_key)
    if not plan:
        await query.edit_message_text("❌ Noto'g'ri reja!")
        return

    if not CLICK_PROVIDER_TOKEN:
        await query.edit_message_text(
            "⚠️ <b>To'lov tizimi sozlanmagan!</b>\n\n"
            "Admin CLICK_PROVIDER_TOKEN ni .env faylga qo'shishi kerak.\n\n"
            "BotFather → /mybots → Bot → Payments → Click",
            parse_mode="HTML"
        )
        return

    price_formatted = f"{plan['price']:,}".replace(",", " ")
    title = f"👑 IELTS Premium — {plan['label']}"
    description = (
        f"Premium obuna {plan['label']} ({plan['duration']} kun)\n"
        f"Barcha premium funksiyalar ochiladi!"
    )

    # Telegram Payments: narx tiyinda (so'm * 100)
    prices = [LabeledPrice(f"Premium {plan['label']}", plan['price'] * 100)]

    context.user_data["pending_plan"] = plan_key

    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title=title,
        description=description,
        payload=f"premium_{plan_key}_{query.from_user.id}",
        provider_token=CLICK_PROVIDER_TOKEN,
        currency="UZS",
        prices=prices,
        start_parameter=f"premium-{plan_key}",
        photo_url="https://i.imgur.com/8V7B5dN.png",
        photo_height=512,
        photo_width=512,
        need_name=False,
        need_phone_number=True,
        need_email=False,
    )


async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Click to'lov old-tekshiruvi"""
    query = update.pre_checkout_query

    if query.invoice_payload.startswith("premium_"):
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="❌ Noto'g'ri to'lov!")


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muvaffaqiyatli to'lov — premium aktivlashtirish"""
    payment = update.message.successful_payment
    user_id = update.effective_user.id

    # Payload dan plan topish
    payload = payment.invoice_payload  # premium_1_month_123456
    parts = payload.split("_")
    # plan_key = "1_month" yoki "3_months" yoki "6_months"
    if len(parts) >= 3:
        plan_key = f"{parts[1]}_{parts[2]}"
    else:
        plan_key = context.user_data.get("pending_plan", "1_month")

    plan = PREMIUM_PLANS.get(plan_key, PREMIUM_PLANS["1_month"])

    session = get_session()
    try:
        # Premium obunani saqlash
        now = datetime.utcnow()
        end_date = now + timedelta(days=plan["duration"])

        subscription = PremiumSubscription(
            user_id=user_id,
            plan_key=plan_key,
            amount=plan["price"],
            payment_id=payment.telegram_payment_charge_id or "",
            provider_payment_id=payment.provider_payment_charge_id or "",
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

        price_formatted = f"{plan['price']:,}".replace(",", " ")
        text = (
            "🎉 <b>To'lov muvaffaqiyatli!</b>\n\n"
            f"👑 <b>Premium {plan['label']}</b> aktivlashtirildi!\n\n"
            f"💰 To'langan: <b>{price_formatted} so'm</b>\n"
            f"📅 Boshlanish: <b>{now.strftime('%d.%m.%Y')}</b>\n"
            f"📅 Tugash: <b>{end_date.strftime('%d.%m.%Y')}</b>\n\n"
            "✅ Barcha premium funksiyalar sizga ochiq!\n\n"
            f"{PREMIUM_FEATURES}\n\n"
            "IELTS tayyorlanishda omad! 🚀"
        )
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        session.rollback()
        await update.message.reply_text(
            f"❌ Xato yuz berdi: {e}\n\nAdmin bilan bog'laning.",
            parse_mode="HTML"
        )
    finally:
        session.close()
        context.user_data.pop("pending_plan", None)


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
    text += "\n💳 To'lov: <b>Click</b>"
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
