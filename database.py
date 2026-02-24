from contextlib import contextmanager
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from config import DB_URL

# Engine sozlamalari (PostgreSQL uchun optimallash)
if "postgresql" in DB_URL:
    # Neon va boshqa cloud DBlar uchun SSL muhim
    connect_args = {"sslmode": "require"}
    engine = create_engine(
        DB_URL,
        echo=False,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10
    )
else:
    engine = create_engine(DB_URL, echo=False)

Session = sessionmaker(bind=engine)
Base = declarative_base()


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), default="")
    emoji = Column(String(10), default="📚")
    questions = relationship("Question", back_populates="subject", cascade="all, delete-orphan")
    results = relationship("UserResult", back_populates="subject")


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    text_uz = Column(Text, default="")  # O'zbek tarjimasi
    option_a = Column(String(500), nullable=False)
    option_b = Column(String(500), nullable=False)
    option_c = Column(String(500), nullable=False)
    option_d = Column(String(500), nullable=False)
    correct_answer = Column(String(1), nullable=False)
    difficulty = Column(Integer, default=1)
    subject = relationship("Subject", back_populates="questions")

    def get_options(self):
        return {"a": self.option_a, "b": self.option_b, "c": self.option_c, "d": self.option_d}


class UserResult(Base):
    __tablename__ = "user_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(100), default="")
    full_name = Column(String(200), default="")
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    score = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False, default=0)
    percentage = Column(Float, nullable=False, default=0.0)
    difficulty_level = Column(String(10), default="all")
    is_mock = Column(Boolean, default=False)
    completed_at = Column(DateTime, default=datetime.utcnow)
    subject = relationship("Subject", back_populates="results")


class WrongAnswer(Base):
    __tablename__ = "wrong_answers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    user_answer = Column(String(1), nullable=False)
    correct_answer = Column(String(1), nullable=False)
    answered_at = Column(DateTime, default=datetime.utcnow)
    reviewed = Column(Boolean, default=False)
    question = relationship("Question")


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    achievement_key = Column(String(50), nullable=False)
    achievement_name = Column(String(100), nullable=False)
    achievement_emoji = Column(String(10), default="🏅")
    earned_at = Column(DateTime, default=datetime.utcnow)


class UserSettings(Base):
    __tablename__ = "user_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)
    reminder_enabled = Column(Boolean, default=False)
    reminder_time = Column(String(5), default="09:00")
    daily_test_enabled = Column(Boolean, default=False)
    daily_word_enabled = Column(Boolean, default=False)
    translation_mode = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)


class DailyStreak(Base):
    __tablename__ = "daily_streaks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_active_date = Column(String(10), default="")
    total_tests = Column(Integer, default=0)


class SpacedRepetition(Base):
    __tablename__ = "spaced_repetition"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    easiness_factor = Column(Float, default=2.5)
    interval = Column(Integer, default=1)
    repetitions = Column(Integer, default=0)
    next_review = Column(String(10), default="")
    last_reviewed = Column(String(10), default="")
    question = relationship("Question")


class Flashcard(Base):
    __tablename__ = "flashcards"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    example = Column(Text, default="")
    category = Column(String(50), default="general")
    mastered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class StudyPlan(Base):
    __tablename__ = "study_plans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)
    plan_type = Column(String(10), default="30")
    target_band = Column(Float, default=6.5)
    start_date = Column(String(10), default="")
    current_day = Column(Integer, default=1)
    completed = Column(Boolean, default=False)


class PremiumSubscription(Base):
    __tablename__ = "premium_subscriptions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    plan_key = Column(String(20), nullable=False)
    amount = Column(Integer, nullable=False)
    payment_id = Column(String(100), default="")
    provider_payment_id = Column(String(100), default="")
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def check_premium(user_id):
    session = Session()
    try:
        settings = session.query(UserSettings).filter_by(user_id=user_id).first()
        if settings and settings.is_premium:
            sub = session.query(PremiumSubscription).filter_by(
                user_id=user_id, is_active=True
            ).order_by(PremiumSubscription.end_date.desc()).first()
            if sub and sub.end_date > datetime.utcnow():
                return True
            elif sub and sub.end_date <= datetime.utcnow():
                settings.is_premium = False
                sub.is_active = False
                session.commit()
                return False
            else:
                return True
        return False
    finally:
        session.close()


def fix_sequences():
    """PostgreSQL sequences sinxronizatsiya qilish"""
    if "postgresql" not in DB_URL:
        return

    tables = [
        "subjects", "questions", "user_results", "wrong_answers",
        "user_achievements", "user_settings", "daily_streaks",
        "spaced_repetition", "flashcards", "study_plans",
        "premium_subscriptions"
    ]

    with engine.connect() as conn:
        for table in tables:
            try:
                sql = text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), coalesce(max(id), 0) + 1, false) FROM {table};")
                conn.execute(sql)
            except Exception:
                pass
        conn.commit()


def init_db():
    Base.metadata.create_all(engine)
    fix_sequences()
    print("✅ Database tayyor (Sequences sinxronlandi)!")


def get_session():
    return Session()


@contextmanager
def session_scope():
    """Tranzaksiyalar uchun context manager"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

