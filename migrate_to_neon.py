import os
import sqlite3
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from database import Base, Subject, Question, UserResult, WrongAnswer, UserAchievement, UserSettings, DailyStreak, SpacedRepetition, Flashcard, StudyPlan, PremiumSubscription
from config import DB_URL

# SQLite ulanishi (asl nusxa)
sqlite_path = os.path.join(os.path.dirname(__file__), "exam_bot.db")
sqlite_url = f"sqlite:///{sqlite_path}"
sqlite_engine = create_engine(sqlite_url)
SQLiteSession = sessionmaker(bind=sqlite_engine)

# PostgreSQL ulanishi (Neon)
pg_engine = create_engine(DB_URL)
PGSession = sessionmaker(bind=pg_engine)

def migrate_data():
    print(f"🔄 Migratsiya boshlandi: {sqlite_url} -> {DB_URL}")
    
    # Neon bazasida jadvallarni yaratish
    Base.metadata.create_all(pg_engine)
    print("✅ Neon bazasida jadvallar yaratildi.")

    sqlite_session = SQLiteSession()
    pg_session = PGSession()

    tables = [
        Subject, Question, UserResult, WrongAnswer, UserAchievement, 
        UserSettings, DailyStreak, SpacedRepetition, Flashcard, 
        StudyPlan, PremiumSubscription
    ]

    try:
        for model in tables:
            table_name = model.__tablename__
            print(f"📦 {table_name} ko'chirilmoqda...")
            
            # SQLite dan ma'lumotlarni o'qish
            data = sqlite_session.query(model).all()
            if not data:
                print(f"ℹ️ {table_name} bo'sh.")
                continue

            # Neon bazasini tozalash (agar ma'lumot bo'lsa)
            pg_session.query(model).delete()
            
            # Neon bazasiga yozish
            for item in data:
                # Obyektni SQLite sessiyasidan ajratish (expunge) va yangi sessiyaga qo'shish
                # Lekin osonroq yo'li - yangi obyekt yaratish
                attrs = {c.key: getattr(item, c.key) for c in inspect(item).mapper.column_attrs}
                new_item = model(**attrs)
                pg_session.add(new_item)
            
            pg_session.commit()
            print(f"✅ {table_name}: {len(data)} ta qator ko'chirildi.")

        print("\n🚀 Barcha ma'lumotlar muvaffaqiyatli Neon bazasiga ko'chirildi!")
    
    except Exception as e:
        pg_session.rollback()
        print(f"❌ Migratsiyada xato: {e}")
    finally:
        sqlite_session.close()
        pg_session.close()

if __name__ == "__main__":
    migrate_data()
