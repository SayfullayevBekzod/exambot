"""
dtm_1000_seed.json faylini DB ga import qilish skripti.
Bu fayl boshqacha formatda — uni standart formatga convert qilib yuklaydi.
"""
import json
import os
import sys

# Loyihaning root papkasini topish
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import func
from database import init_db, get_session, Subject, Question

SUBJECT_EMOJIS = {
    "Adabiyot": "📖",
    "Ona tili": "✏️",
}


def import_dtm(filepath):
    """DTM JSON faylini import qilish"""
    init_db()

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    meta = data.get("meta", {})
    print(f"📋 {meta.get('name', 'DTM')}")
    print(f"📊 Jami savollar: {len(questions)}")

    session = get_session()
    try:
        added = 0
        skipped = 0
        subject_counts = {}

        for q in questions:
            subject_name = q.get("subject", "").strip()
            if not subject_name:
                skipped += 1
                continue

            # Fan yaratish yoki topish
            subject = session.query(Subject).filter(func.lower(Subject.name) == func.lower(subject_name)).first()
            if not subject:
                emoji = SUBJECT_EMOJIS.get(subject_name, "📚")
                subject = Subject(name=subject_name, emoji=emoji, description=f"{subject_name} fani")
                session.add(subject)
                session.flush()

            # Variantlarni olish
            options = q.get("options", [])
            if len(options) != 4:
                skipped += 1
                continue

            # Variantlar va to'g'ri javobni aniqlash
            option_map = {}
            correct_key = None
            for opt in options:
                key = opt["key"].lower()  # A -> a, B -> b, ...
                option_map[key] = opt["text"]
                if opt.get("is_correct"):
                    correct_key = key

            if not correct_key or not all(k in option_map for k in ("a", "b", "c", "d")):
                skipped += 1
                continue

            # Savol yaratish
            question = Question(
                subject_id=subject.id,
                text=q.get("question_text", ""),
                option_a=option_map["a"],
                option_b=option_map["b"],
                option_c=option_map["c"],
                option_d=option_map["d"],
                correct_answer=correct_key,
                difficulty=min(q.get("difficulty", 1), 3),  # max 3 ga chegaralash
            )
            session.add(question)
            added += 1

            # Fan bo'yicha hisob
            subject_counts[subject_name] = subject_counts.get(subject_name, 0) + 1

        session.commit()

        print(f"\n✅ Jami qo'shildi: {added} ta savol")
        if skipped:
            print(f"⚠️ O'tkazib yuborildi: {skipped}")
        print(f"\n📚 Fanlar bo'yicha:")
        for name, count in sorted(subject_counts.items()):
            emoji = SUBJECT_EMOJIS.get(name, "📚")
            print(f"   {emoji} {name}: {count} ta savol")

    except Exception as e:
        session.rollback()
        print(f"❌ Xatolik: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    filepath = os.path.join(os.path.dirname(__file__), "dtm_1000_seed.json")
    if not os.path.exists(filepath):
        print(f"❌ Fayl topilmadi: {filepath}")
        sys.exit(1)
    import_dtm(filepath)
