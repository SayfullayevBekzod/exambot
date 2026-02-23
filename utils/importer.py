import json
from database import get_session, Subject, Question


def import_from_json(json_data):
    """
    JSON ma'lumotlardan savollarni DB ga import qiladi.
    
    Kutilayotgan format:
    {
        "subject": "Matematika",
        "emoji": "📐",
        "description": "Matematika fani bo'yicha savollar",
        "questions": [
            {
                "text": "2 + 2 = ?",
                "options": {"a": "3", "b": "4", "c": "5", "d": "6"},
                "correct": "b",
                "difficulty": 1
            }
        ]
    }
    
    Returns:
        tuple: (qo'shilgan_savollar_soni, fan_nomi, xato_xabar)
    """
    session = get_session()
    try:
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data

        subject_raw = data.get("subject", "")
        if isinstance(subject_raw, dict):
            subject_name = subject_raw.get("name", "").strip()
            emoji = subject_raw.get("emoji", data.get("emoji", "📚"))
            description = subject_raw.get("description", data.get("description", ""))
        else:
            subject_name = str(subject_raw).strip()
            emoji = data.get("emoji", "📚")
            description = data.get("description", "")

        if not subject_name:
            return 0, "", "❌ Fan nomi ko'rsatilmagan!"
        questions_data = data.get("questions", [])

        if not questions_data:
            return 0, subject_name, "❌ Savollar topilmadi!"

        # Fan mavjud bo'lsa topish, bo'lmasa yaratish
        subject = session.query(Subject).filter_by(name=subject_name).first()
        if not subject:
            subject = Subject(name=subject_name, emoji=emoji, description=description)
            session.add(subject)
            session.flush()
        else:
            # Mavjud fanning emoji va description ni yangilash
            if emoji:
                subject.emoji = emoji
            if description:
                subject.description = description

        added = 0
        errors = []
        for i, q in enumerate(questions_data, 1):
            try:
                text = q.get("text", "").strip()
                options = q.get("options", {})
                correct = q.get("correct", "").strip().lower()
                difficulty = q.get("difficulty", 1)

                if not text:
                    errors.append(f"Savol #{i}: matn bo'sh")
                    continue
                if correct not in ("a", "b", "c", "d"):
                    errors.append(f"Savol #{i}: noto'g'ri javob kaliti '{correct}'")
                    continue
                if not all(k in options for k in ("a", "b", "c", "d")):
                    errors.append(f"Savol #{i}: a/b/c/d variantlar to'liq emas")
                    continue

                question = Question(
                    subject_id=subject.id,
                    text=text,
                    option_a=str(options["a"]),
                    option_b=str(options["b"]),
                    option_c=str(options["c"]),
                    option_d=str(options["d"]),
                    correct_answer=correct,
                    difficulty=difficulty,
                )
                session.add(question)
                added += 1
            except Exception as e:
                errors.append(f"Savol #{i}: {str(e)}")

        session.commit()

        error_msg = ""
        if errors:
            error_msg = "\n⚠️ Xatolar:\n" + "\n".join(f"  • {e}" for e in errors[:10])
            if len(errors) > 10:
                error_msg += f"\n  ... va yana {len(errors) - 10} ta xato"

        return added, subject_name, error_msg

    except json.JSONDecodeError as e:
        return 0, "", f"❌ JSON formati noto'g'ri: {e}"
    except Exception as e:
        session.rollback()
        return 0, "", f"❌ Xatolik: {e}"
    finally:
        session.close()


def import_from_file(file_path):
    """JSON fayldan import qilish"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return import_from_json(data)
