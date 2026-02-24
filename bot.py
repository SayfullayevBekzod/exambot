"""IELTS Preparation Bot — Asosiy fayl"""
import os
import json
import logging
import asyncio

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    PreCheckoutQueryHandler, filters, ContextTypes, PicklePersistence,
)

from config import BOT_TOKEN
from database import init_db, get_session, Subject

# === Handlers ===
from handlers.start import start_command, help_command, subjects_command, back_to_subjects_callback
from handlers.quiz import subject_selected_callback, answer_callback, difficulty_selected_callback, mock_test_callback
from handlers.stats import my_stats_command, my_stats_callback, leaderboard_command, leaderboard_callback, band_history_callback
from handlers.admin import import_command, admin_stats_command, handle_document, handle_text_import
from handlers.mistakes import mistakes_command, review_mistakes_callback, clear_mistakes_callback
from handlers.tips import tips_command, tips_callback, show_tips_menu_callback, writing_command, writing_callback, show_writing_menu_callback
from handlers.daily import daily_word_command, random_word_callback, reminder_command, reminder_toggle_callback, setup_daily_jobs
from handlers.achievements import achievements_command
from handlers.challenge import challenge_command
from handlers.audio import audio_test_command
from handlers.certificate import certificate_command
from handlers.spaced import spaced_command
from handlers.speaking import (
    speaking_command, speak_part1_callback, speak_p1_topic_callback,
    speak_part2_callback, speak_part3_callback, speak_random_callback,
    speak_back_callback, handle_speaking_voice, handle_speaking_text,
)
from handlers.flashcards import (
    flashcards_command, load_defaults_callback, study_flashcard_callback,
    reveal_flashcard_callback, flashcard_response_callback, flashcard_stats_callback,
)
from handlers.extras import (
    studyplan_command, plan_create_callback, plan_done_callback, plan_delete_callback,
    speed_command, speed_start_callback,
    translation_command, translation_toggle_callback,
    miniapp_command,
)
from handlers.payment import (
    premium_command, buy_premium_callback, go_premium_callback,
    handle_premium_receipt, admin_approve_callback, admin_reject_callback,
    admin_command, admin_give_premium_callback, admin_revoke_premium_callback,
    admin_set_premium_callback, admin_users_callback, admin_full_stats_callback,
    admin_back_callback,
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kutilmagan xatolarni boshqarish va adminga xabar berish"""
    from config import ADMIN_IDS
    import traceback
    
    logger.error("Xato yuz berdi:", exc_info=context.error)
    
    # Traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    
    # Adminga xabar
    message = (
        f"⚠️ <b>Kritik Xato!</b>\n\n"
        f"Update: <code>{update}</code>\n\n"
        f"Xato matni: <code>{str(context.error)}</code>\n\n"
        f"Tafsilotlar:\n<pre>{tb_string[:3000]}</pre>"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=message, parse_mode="HTML")
        except Exception:
            pass

    # Foydalanuvchiga xabar
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ <b>Xatolik yuz berdi!</b>\n\n"
                "Texnik nosozlik tufayli buyruqni bajarib bo'lmadi.\n"
                "Adminlar xabardor qilindi. Iltimos, bir ozdan keyin qayta urinib ko'ring.",
                parse_mode="HTML"
            )
        except Exception:
            pass


def load_initial_data():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    if not os.path.exists(data_dir):
        return

    session = get_session()
    try:
        existing = session.query(Subject).count()
        if existing > 0:
            logger.info(f"DB da {existing} ta bo'lim mavjud, import o'tkazilmaydi")
            return

        from utils.importer import import_from_json

        json_files = [f for f in os.listdir(data_dir) if f.endswith(".json") and not f.startswith(("daily_", "tips_"))]
        for filename in sorted(json_files):
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "subject" in data and "questions" in data:
                    added, name, err = import_from_json(data)
                    if added > 0:
                        logger.info(f"✅ {name}: {added} ta savol yuklandi")
                    if err:
                        logger.warning(f"⚠️ {filename}: {err}")
            except Exception as e:
                logger.error(f"❌ {filename} xato: {e}")
    finally:
        session.close()


async def main():
    # Render rolling update paytida 'Conflict' xatosini oldini olish uchun biroz kutamiz.
    # Bu vaqt ichida yangi web-server 'Healthy' bo'ladi va Render eski botni o'chiradi.
    if os.environ.get("RENDER"):
        print("⏳ Render muhiti aniqlandi. 20 soniya kutilyapti...")
        await asyncio.sleep(20)

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN topilmadi! .env faylga bot tokenini yozing.")
        return

    init_db()
    load_initial_data()

    # Persistence - sessiyalarni saqlash
    persistence = PicklePersistence(filepath="persistence.pickle")

    app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()

    # === Buyruqlar ===
    commands = [
        ("start", start_command), ("help", help_command), ("bolimlar", subjects_command),
        ("natijalarim", my_stats_command), ("reyting", leaderboard_command),
        ("xatolar", mistakes_command), ("yutuqlar", achievements_command),
        ("kunlik_soz", daily_word_command), ("tips", tips_command), ("writing", writing_command),
        ("challenge", challenge_command), ("eslatma", reminder_command),
        ("audio", audio_test_command), ("sertifikat", certificate_command),
        ("takrorlash", spaced_command), ("flashcards", flashcards_command),
        ("reja", studyplan_command), ("speed", speed_command),
        ("tarjima", translation_command), ("premium", premium_command),
        ("webapp", miniapp_command), ("speaking", speaking_command),
        ("admin", admin_command),
        ("import", import_command), ("admin_stats", admin_stats_command),
    ]
    for cmd, handler in commands:
        app.add_handler(CommandHandler(cmd, handler))

    # === To'lov handlerlari (Manual Receipt) ===
    app.add_handler(MessageHandler(filters.PHOTO, handle_premium_receipt))

    # === Callback querylar ===
    callbacks = [
        (r"^subject_\d+$", subject_selected_callback),
        (r"^diff_\d+_(easy|medium|hard|all)$", difficulty_selected_callback),
        (r"^mock_\d+$", mock_test_callback),
        (r"^answer_\d+_[abcd]$", answer_callback),
        (r"^back_subjects$", back_to_subjects_callback),
        (r"^my_stats$", my_stats_callback),
        (r"^band_history$", band_history_callback),
        (r"^leaderboard$", leaderboard_callback),
        (r"^review_mistakes$", review_mistakes_callback),
        (r"^clear_mistakes$", clear_mistakes_callback),
        (r"^tips_(Reading|Listening|Grammar|Vocabulary|Speaking)$", tips_callback),
        (r"^show_tips_menu$", show_tips_menu_callback),
        (r"^writing_(task1|task2|random)$", writing_callback),
        (r"^show_writing_menu$", show_writing_menu_callback),
        (r"^random_word$", random_word_callback),
        (r"^reminder_(on|off)$", reminder_toggle_callback),
        # Premium & Payment
        (r"^buy_premium_(1_month|3_months|6_months)$", buy_premium_callback),
        (r"^go_premium$", go_premium_callback),
        # Flashcards
        (r"^fc_study$", study_flashcard_callback),
        (r"^fc_load_defaults$", load_defaults_callback),
        (r"^fc_reveal_\d+$", reveal_flashcard_callback),
        (r"^fc_(knew|didnt)_\d+$", flashcard_response_callback),
        (r"^fc_stats$", flashcard_stats_callback),
        # Study Plan
        (r"^plan_create_(30|60|90)$", plan_create_callback),
        (r"^plan_done_today$", plan_done_callback),
        (r"^plan_delete$", plan_delete_callback),
        # Speed Round
        (r"^speed_start$", speed_start_callback),
        (r"^speed_restart$", speed_start_callback),
        # Translation
        (r"^translate_(on|off)$", translation_toggle_callback),
        # Speaking Practice
        (r"^speak_part1$", speak_part1_callback),
        (r"^speak_p1_\w+$", speak_p1_topic_callback),
        (r"^speak_part2$", speak_part2_callback),
        (r"^speak_part3$", speak_part3_callback),
        (r"^speak_random$", speak_random_callback),
        (r"^speak_back$", speak_back_callback),
        # Manual Payment Admin Approval
        (r"^adm_approve_", admin_approve_callback),
        (r"^adm_reject_", admin_reject_callback),
        (r"^adm_give_premium$", admin_give_premium_callback),
        (r"^adm_revoke_premium$", admin_revoke_premium_callback),
        (r"^adm_setprem_", admin_set_premium_callback),
        (r"^adm_users$", admin_users_callback),
        (r"^adm_full_stats$", admin_full_stats_callback),
        (r"^adm_back$", admin_back_callback),
    ]
    for pattern, handler in callbacks:
        app.add_handler(CallbackQueryHandler(handler, pattern=pattern))

    # === Reply keyboard tugmalari ===
    button_handlers = {
        "📚 Bo'limlar": subjects_command, "📝 Test boshlash": subjects_command,
        "📊 Natijalarim": my_stats_command, "🏆 Reyting": leaderboard_command,
        "❌ Xatolarim": mistakes_command, "🏅 Yutuqlar": achievements_command,
        "💡 Kunlik so'z": daily_word_command, "📖 Tips": tips_command,
        "✍️ Writing": writing_command, "🎧 Audio Test": audio_test_command,
        "🗂️ Flashcards": flashcards_command, "🧠 Takrorlash": spaced_command,
        "📅 Study Plan": studyplan_command, "🎮 Speed Round": speed_command,
        "📊 Sertifikat": certificate_command, "👑 Premium": premium_command,
        "🌐 Tarjima": translation_command, "🔔 Eslatma": reminder_command,
        "👥 Challenge": challenge_command, "ℹ️ Yordam": help_command,
        "🎤 Speaking": speaking_command, "⚙️ Admin": admin_command,
    }
    for text, handler in button_handlers.items():
        app.add_handler(MessageHandler(filters.Regex(f"^{text}$"), handler))

    # === Fayl, matn va voice (Group 1 - Pastroq ustuvorlik) ===
    # Bu guruhdagi handlerlar faqat Group 0 dagi tugmalarga mos kelmasa ishlaydi
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document), group=1)
    app.add_handler(MessageHandler(filters.VOICE, handle_speaking_voice), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_import), group=1)

    # === Error Handler ===
    app.add_error_handler(error_handler)

    # === Jobs ===
    setup_daily_jobs(app.job_queue)

    print("🤖 IELTS Preparation Bot ishga tushdi!")
    
    # PTB v21.10+ run_polling handles the loop internally if called correctly 
    # but we can initialize it to be safe
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        # Keep running
        while True:
            await asyncio.sleep(3600)


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
