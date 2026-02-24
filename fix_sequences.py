import os
from sqlalchemy import create_engine, text
from config import DB_URL

def fix_sequences():
    if "postgresql" not in DB_URL:
        print("ℹ️ SQLite bazasida sequence muammosi bo'lmaydi.")
        return

    print(f"🔧 PostgreSQL sequences yangilanmoqda: {DB_URL.split('@')[-1]}") # URL ni qisman ko'rsatish
    
    engine = create_engine(DB_URL, connect_args={"sslmode": "require"})
    
    tables = [
        "subjects", "questions", "user_results", "wrong_answers", 
        "user_achievements", "user_settings", "daily_streaks", 
        "spaced_repetition", "flashcards", "study_plans", 
        "premium_subscriptions"
    ]

    with engine.connect() as conn:
        for table in tables:
            try:
                # Sequence nomini topish va yangilash
                sql = text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), coalesce(max(id), 0) + 1, false) FROM {table};")
                conn.execute(sql)
                print(f"✅ {table}: Sequence yangilandi.")
            except Exception as e:
                print(f"⚠️ {table}: Xato (balki jadval hali yo'qdir): {e}")
        
        conn.commit()
    print("\n🚀 Barcha sequences muvaffaqiyatli sinxronizatsiya qilindi!")

if __name__ == "__main__":
    fix_sequences()
