# 📚 Exam Bot

Telegram orqali turli fanlar bo'yicha test yechish boti.

## 🚀 O'rnatish

```bash
# Virtual environment yaratish
python -m venv env
env\Scripts\activate  # Windows

# Kutubxonalarni o'rnatish
pip install -r requirements.txt
```

## ⚙️ Sozlash

`.env` faylga bot tokenini yozing:

```
BOT_TOKEN=sizning_bot_tokeningiz
ADMIN_IDS=123456789,987654321
```

## ▶️ Ishga tushirish

```bash
python bot.py
```

Bot birinchi marta ishga tushganda `data/` papkasidagi barcha JSON fayllarni avtomatik yuklaydi.

## 📥 Savollar qo'shish

### JSON format:

```json
{
  "subject": "Fan nomi",
  "emoji": "📐",
  "questions": [
    {
      "text": "Savol matni",
      "options": {"a": "A variant", "b": "B variant", "c": "C variant", "d": "D variant"},
      "correct": "b",
      "difficulty": 1
    }
  ]
}
```

### Usullar:
1. **Fayl orqali**: JSON faylni `data/` papkasiga qo'shing (birinchi yuklashda)
2. **Bot orqali**: `/import` buyrug'ini yuboring va JSON faylni yoki matnni yuboring (faqat admin)

## 📋 Buyruqlar

| Buyruq | Tavsif |
|--------|--------|
| `/start` | Botni boshlash |
| `/fanlar` | Fanlar ro'yxati |
| `/natijalarim` | Shaxsiy natijalar |
| `/reyting` | Top 10 reyting |
| `/help` | Yordam |
| `/import` | Savollar import (admin) |
| `/admin_stats` | Statistika (admin) |
