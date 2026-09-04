"""Database engine and session management.

Uses the configured `DATABASE_URL` (Supabase PostgreSQL when available).
Falls back to a local SQLite file so the demo runs out of the box.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# Respect an explicit env override even if .env is not loaded.
database_url = os.getenv("DATABASE_URL", settings.database_url)

engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency yielding a database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Columns added to existing tables after the first deploy. `create_all` does
# not alter existing tables, so they are back-filled here (SQLite + Postgres).
# JSON columns use the dialect's native type where available.
_is_postgres = database_url.startswith("postgresql")
_JSON_TYPE = "JSON" if _is_postgres else "TEXT"

_ADDITIVE_COLUMNS: dict[str, dict[str, str]] = {
    "reports": {
        "source": "VARCHAR(64)",
        "processing_status": "VARCHAR(16) DEFAULT 'analyzed'",
        "source_id": "VARCHAR(64)",
    },
    "analyses": {
        "summary": "TEXT",
        "suggested_actions": _JSON_TYPE,
        "languages": _JSON_TYPE,
        "uncertainty_note": "TEXT",
        "location": "VARCHAR(128)",
        "equipment": _JSON_TYPE,
        "unsafe_type": "VARCHAR(32)",
        "rule_conditions": _JSON_TYPE,
        "modified_fields": _JSON_TYPE,
    },
    "ingest_jobs": {
        "duplicates": _JSON_TYPE,
    },
}


def _additive_migrations() -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    for table, columns in _ADDITIVE_COLUMNS.items():
        if table not in inspector.get_table_names():
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        for name, ddl in columns.items():
            if name not in existing:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def init_db() -> None:
    """Create all tables and apply additive migrations."""
    from app.models import entities  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)
    _additive_migrations()