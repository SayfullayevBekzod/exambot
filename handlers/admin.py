import json
import tempfile
import os

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import get_session, Subject, Question, UserResult
from utils.importer import import_from_json
from sqlalchemy import func


def is_admin(user_id):
    """Admin tekshirish"""
    return user_id in ADMIN_IDS


async def import_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/import buyrug'i — faqat admin uchun"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bu buyruq faqat adminlar uchun.")
        return

    await update.message.reply_text(
        "📥 <b>Savollar import qilish</b>\n\n"
        "JSON faylni yuboring yoki JSON matnni pastga yozing.\n\n"
        "📋 <b>Kutilayotgan format:</b>\n"
        '<pre>{\n'
        '  "subject": "Fan nomi",\n'
        '  "emoji": "📐",\n'
        '  "questions": [\n'
        '    {\n'
        '      "text": "Savol matni",\n'
        '      "options": {\n'
        '        "a": "Variant A",\n'
        '        "b": "Variant B",\n'
        '        "c": "Variant C",\n'
        '        "d": "Variant D"\n'
        '      },\n'
        '      "correct": "b",\n'
        '      "difficulty": 1\n'
        '    }\n'
        '  ]\n'
        '}</pre>',
        parse_mode="HTML",
    )
    context.user_data["awaiting_import"] = True


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """JSON fayl yuborilganda"""
    if not is_admin(update.effective_user.id):
        return

    if not context.user_data.get("awaiting_import"):
        return

    document = update.message.document
    if not document.file_name.endswith(".json"):
        await update.message.reply_text("⚠️ Faqat .json formatdagi fayllar qabul qilinadi.")
        return

    # Faylni yuklab olish
    file = await document.get_file()
    temp_path = os.path.join(tempfile.gettempdir(), document.file_name)
    await file.download_to_drive(temp_path)

    try:
        with open(temp_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        added, subject_name, error_msg = import_from_json(json_data)

        text = (
            f"📥 <b>Import natijasi</b>\n\n"
            f"📚 Fan: <b>{subject_name}</b>\n"
            f"✅ Qo'shilgan savollar: <b>{added}</b>"
        )
        if error_msg:
            text += f"\n{error_msg}"

        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        context.user_data.pop("awaiting_import", None)


async def handle_text_import(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """JSON matn sifatida yuborilganda"""
    if not is_admin(update.effective_user.id):
        return

    if not context.user_data.get("awaiting_import"):
        return

    text = update.message.text.strip()

    # JSON ekanligini tekshirish
    if not (text.startswith("{") or text.startswith("[")):
        return

    try:
        added, subject_name, error_msg = import_from_json(text)

        result_text = (
            f"📥 <b>Import natijasi</b>\n\n"
            f"📚 Fan: <b>{subject_name}</b>\n"
            f"✅ Qo'shilgan savollar: <b>{added}</b>"
        )
        if error_msg:
            result_text += f"\n{error_msg}"

        await update.message.reply_text(result_text, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")
    finally:
        context.user_data.pop("awaiting_import", None)


async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/admin_stats — umumiy statistika (faqat admin uchun)"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bu buyruq faqat adminlar uchun.")
        return

    session = get_session()
    try:
        total_subjects = session.query(func.count(Subject.id)).scalar()
        total_questions = session.query(func.count(Question.id)).scalar()
        total_results = session.query(func.count(UserResult.id)).scalar()
        unique_users = session.query(func.count(func.distinct(UserResult.user_id))).scalar()

        # Fan bo'yicha savollar soni
        subjects = session.query(Subject).all()
        subject_info = ""
        for s in subjects:
            q_count = session.query(func.count(Question.id)).filter_by(subject_id=s.id).scalar()
            r_count = session.query(func.count(UserResult.id)).filter_by(subject_id=s.id).scalar()
            subject_info += f"  {s.emoji} {s.name}: {q_count} savol, {r_count} test\n"

        text = (
            f"📊 <b>Admin Statistika</b>\n\n"
            f"📚 Fanlar soni: <b>{total_subjects}</b>\n"
            f"❓ Savollar soni: <b>{total_questions}</b>\n"
            f"📝 Yechilgan testlar: <b>{total_results}</b>\n"
            f"👥 Foydalanuvchilar: <b>{unique_users}</b>\n\n"
        )

        if subject_info:
            text += f"{'─' * 25}\n📚 <b>Fanlar tafsiloti:</b>\n\n{subject_info}"

        await update.message.reply_text(text, parse_mode="HTML")

    finally:
        session.close()
