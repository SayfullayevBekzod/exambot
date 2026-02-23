"""Tips & Tricks + Writing bo'limi"""
import json
import os
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


def _load_data():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tips_and_writing.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def tips_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tips buyrug'i"""
    keyboard = [
        [InlineKeyboardButton("📖 Reading Tips", callback_data="tips_Reading")],
        [InlineKeyboardButton("🎧 Listening Tips", callback_data="tips_Listening")],
        [InlineKeyboardButton("✏️ Grammar Tips", callback_data="tips_Grammar")],
        [InlineKeyboardButton("📝 Vocabulary Tips", callback_data="tips_Vocabulary")],
        [InlineKeyboardButton("🗣️ Speaking Tips", callback_data="tips_Speaking")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
    ]
    await update.message.reply_text(
        "📖 <b>IELTS Tips & Tricks</b>\n\nQaysi bo'lim uchun maslahat olmoqchisiz?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def tips_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bo'lim tanlanganda tipslarni ko'rsatish"""
    query = update.callback_query
    await query.answer()

    section = query.data.replace("tips_", "")
    data = _load_data()
    tips_data = data.get("tips", {}).get(section, {})

    if not tips_data:
        await query.edit_message_text("❌ Tips topilmadi!")
        return

    emoji = tips_data.get("emoji", "📚")
    tips_list = tips_data.get("tips", [])

    text = f"{emoji} <b>{section} — Tips & Tricks</b>\n\n"
    for i, tip in enumerate(tips_list, 1):
        text += f"{i}. {tip}\n\n"

    keyboard = [
        [InlineKeyboardButton("🔙 Boshqa bo'limlar", callback_data="show_tips_menu")],
        [InlineKeyboardButton("🏠 Bosh sahifa", callback_data="back_subjects")],
    ]
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_tips_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tips menyu qaytish"""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📖 Reading Tips", callback_data="tips_Reading")],
        [InlineKeyboardButton("🎧 Listening Tips", callback_data="tips_Listening")],
        [InlineKeyboardButton("✏️ Grammar Tips", callback_data="tips_Grammar")],
        [InlineKeyboardButton("📝 Vocabulary Tips", callback_data="tips_Vocabulary")],
        [InlineKeyboardButton("🗣️ Speaking Tips", callback_data="tips_Speaking")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
    ]
    await query.edit_message_text(
        "📖 <b>IELTS Tips & Tricks</b>\n\nQaysi bo'lim uchun maslahat olmoqchisiz?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# === Writing bo'limi ===

async def writing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/writing buyrug'i"""
    keyboard = [
        [InlineKeyboardButton("📊 Task 1 — Graph/Chart", callback_data="writing_task1")],
        [InlineKeyboardButton("✍️ Task 2 — Essay", callback_data="writing_task2")],
        [InlineKeyboardButton("🎲 Tasodifiy mavzu", callback_data="writing_random")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
    ]
    await update.message.reply_text(
        "📚 <b>IELTS Writing</b>\n\n"
        "Writing bo'limida 2 ta task mavjud:\n\n"
        "📊 <b>Task 1</b> — Graph, chart yoki diagramma tavsifi (150+ so'z)\n"
        "✍️ <b>Task 2</b> — Essay yozish (250+ so'z)\n\n"
        "Qaysi task uchun mavzu va maslahat olmoqchisiz?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def writing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Writing task tanlash"""
    query = update.callback_query
    await query.answer()

    data = _load_data()
    topics = data.get("writing_topics", [])
    action = query.data.replace("writing_", "")

    if action == "task1":
        filtered = [t for t in topics if t["task"] == 1]
    elif action == "task2":
        filtered = [t for t in topics if t["task"] == 2]
    else:
        filtered = topics

    if not filtered:
        await query.edit_message_text("❌ Mavzular topilmadi!")
        return

    topic = random.choice(filtered)
    phrases = topic.get("key_phrases", [])

    text = (
        f"✍️ <b>IELTS Writing Task {topic['task']}</b>\n"
        f"Turi: <b>{topic['type']}</b>\n\n"
        f"📋 <b>Mavzu:</b>\n<i>{topic['topic']}</i>\n\n"
        f"💡 <b>Foydali iboralar:</b>\n"
    )
    for p in phrases:
        text += f"  • <code>{p}</code>\n"

    if topic["task"] == 1:
        text += (
            f"\n📐 <b>Tuzilma:</b>\n"
            f"1️⃣ Introduction (1-2 gap — paraphrase)\n"
            f"2️⃣ Overview (asosiy tendentsiya)\n"
            f"3️⃣ Body 1 (birinchi guruh ma'lumotlar)\n"
            f"4️⃣ Body 2 (ikkinchi guruh)\n"
            f"⚠️ Minimum 150 so'z!"
        )
    else:
        text += (
            f"\n📐 <b>Tuzilma:</b>\n"
            f"1️⃣ Introduction (mavzuni paraphrase + fikringiz)\n"
            f"2️⃣ Body 1 (1-dalil + misol)\n"
            f"3️⃣ Body 2 (2-dalil + misol)\n"
            f"4️⃣ Conclusion (xulosa)\n"
            f"⚠️ Minimum 250 so'z!"
        )

    keyboard = [
        [InlineKeyboardButton("🎲 Boshqa mavzu", callback_data=f"writing_{action}")],
        [InlineKeyboardButton("🔙 Writing menyu", callback_data="show_writing_menu")],
    ]
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_writing_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📊 Task 1 — Graph/Chart", callback_data="writing_task1")],
        [InlineKeyboardButton("✍️ Task 2 — Essay", callback_data="writing_task2")],
        [InlineKeyboardButton("🎲 Tasodifiy mavzu", callback_data="writing_random")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_subjects")],
    ]
    await query.edit_message_text(
        "📚 <b>IELTS Writing</b>\n\nQaysi task uchun mavzu olmoqchisiz?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
