import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "acadbridge.db"


def _database_url() -> str:
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    # Vercel Functions can write only to /tmp; this file is not durable across instances.
    if os.getenv("VERCEL"):
        return "sqlite:////tmp/kokoro.db"
    return f"sqlite:///{_DEFAULT_DB}"


DATABASE_URL = _database_url()

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_column(conn, table: str, column: str, spec: str):
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    names = {row[1] for row in rows}
    if names and column not in names:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {spec}"))


def migrate_schema():
    if not DATABASE_URL.startswith("sqlite"):
        return
    with engine.begin() as conn:
        tables = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
        if "learners" in tables:
            _add_column(conn, "learners", "hours_per_day", "INTEGER DEFAULT 2")
            _add_column(conn, "learners", "budget", "VARCHAR DEFAULT 'free'")
            _add_column(conn, "learners", "last_active_date", "VARCHAR DEFAULT ''")
            _add_column(conn, "learners", "streak_days", "INTEGER DEFAULT 0")
            _add_column(conn, "learners", "duration_months", "INTEGER DEFAULT 0")
            _add_column(conn, "learners", "goal_meta", "TEXT")
            _add_column(conn, "learners", "goal_subskills", "TEXT")
            _add_column(conn, "learners", "active_skill_id", "VARCHAR DEFAULT ''")
        if "chat_messages" in tables:
            _add_column(conn, "chat_messages", "skill_id", "VARCHAR DEFAULT ''")
            _add_column(conn, "chat_messages", "session_id", "VARCHAR DEFAULT ''")
        if "chat_sessions" in tables:
            _add_column(conn, "chat_sessions", "skill_id", "VARCHAR DEFAULT ''")
            _add_column(conn, "chat_sessions", "title", "VARCHAR DEFAULT 'New chat'")
        if "learning_paths" in tables:
            _add_column(conn, "learning_paths", "skill_id", "VARCHAR DEFAULT ''")
        if "assessments" in tables:
            _add_column(conn, "assessments", "skill_id", "VARCHAR DEFAULT ''")
        if "path_items" in tables:
            _add_column(conn, "path_items", "skill_id", "VARCHAR DEFAULT ''")
            _add_column(conn, "path_items", "phase", "VARCHAR DEFAULT ''")
            _add_column(conn, "path_items", "week", "INTEGER DEFAULT 1")
            _add_column(conn, "path_items", "title", "VARCHAR DEFAULT ''")
            _add_column(conn, "path_items", "url", "VARCHAR DEFAULT ''")
            _add_column(conn, "path_items", "skill_name", "VARCHAR DEFAULT ''")
            _add_column(conn, "path_items", "topic_id", "VARCHAR DEFAULT ''")
            _add_column(conn, "path_items", "resources", "TEXT")
        if "assessment_items" in tables:
            _add_column(conn, "assessment_items", "skill_name", "VARCHAR DEFAULT ''")
            _add_column(conn, "assessment_items", "topic_id", "VARCHAR DEFAULT ''")
            _add_column(conn, "assessment_items", "explanation", "TEXT DEFAULT ''")
        if "skill_topics" in tables:
            _add_column(conn, "skill_topics", "slug", "VARCHAR DEFAULT ''")
            _add_column(conn, "skill_topics", "sort_order", "INTEGER DEFAULT 0")
            _add_column(conn, "skill_topics", "parent_id", "VARCHAR DEFAULT ''")
            _add_column(conn, "skill_topics", "prerequisites", "TEXT")
            _add_column(conn, "skill_topics", "required", "INTEGER DEFAULT 70")
        if "skills" in tables:
            _add_column(conn, "skills", "description", "TEXT DEFAULT ''")
            _add_column(conn, "skills", "domain", "VARCHAR DEFAULT 'general'")
            _add_column(conn, "skills", "taxonomy_version", "INTEGER DEFAULT 1")
            _add_column(conn, "skills", "source", "VARCHAR DEFAULT 'catalog'")
        if "learner_skills" in tables:
            _add_column(conn, "learner_skills", "overall_proficiency", "INTEGER DEFAULT 0")
            _add_column(conn, "learner_skills", "confidence", "INTEGER DEFAULT 0")
            _add_column(conn, "learner_skills", "status", "VARCHAR DEFAULT 'not_assessed'")
        if "learner_topic_mastery" in tables:
            _add_column(conn, "learner_topic_mastery", "proficiency", "INTEGER DEFAULT 0")
            _add_column(conn, "learner_topic_mastery", "confidence", "INTEGER DEFAULT 0")
            _add_column(conn, "learner_topic_mastery", "status", "VARCHAR DEFAULT 'not_assessed'")
            _add_column(conn, "learner_topic_mastery", "evidence_count", "INTEGER DEFAULT 0")
        if "academic_subjects" in tables:
            _add_column(conn, "academic_subjects", "resources", "TEXT")


def init_db():
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_schema()
    from app.services.skill_registry import seed_catalog_skills

    db = SessionLocal()
    try:
        seed_catalog_skills(db)
    except Exception:
        db.rollback()
    finally:
        db.close()
