"""IELTS Preparation Bot — Asosiy fayl"""
import os
import json
import logging

from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    PreCheckoutQueryHandler, filters,
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
    premium_command, buy_premium_callback, precheckout_handler,
    successful_payment_handler, go_premium_callback,
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


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


def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN topilmadi! .env faylga bot tokenini yozing.")
        return

    init_db()
    load_initial_data()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

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
        ("webapp", miniapp_command),
        ("import", import_command), ("admin_stats", admin_stats_command),
    ]
    for cmd, handler in commands:
        app.add_handler(CommandHandler(cmd, handler))

    # === To'lov handlerlari (Click) ===
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

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
    }
    for text, handler in button_handlers.items():
        app.add_handler(MessageHandler(filters.Regex(f"^{text}$"), handler))

    # === Fayl va matn (admin) ===
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_import))

    # === Jobs ===
    setup_daily_jobs(app.job_queue)

    print("🤖 IELTS Preparation Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
