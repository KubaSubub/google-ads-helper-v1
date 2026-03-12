"""SQLAlchemy database engine and session factory for SQLite."""

from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


_db_path = settings.database_url.replace("sqlite:///", "")
Path(_db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=settings.is_development,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL mode and foreign keys on every new SQLite connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""



def get_db():
    """FastAPI dependency - yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_sqlite_columns():
    if engine.dialect.name != "sqlite":
        return

    schema_updates = {
        "campaigns": {
            "campaign_role_auto": "TEXT",
            "campaign_role_final": "TEXT",
            "role_confidence": "FLOAT",
            "protection_level": "TEXT",
            "role_source": "TEXT DEFAULT 'AUTO'",
        },
        "recommendations": {
            "source": "TEXT DEFAULT 'PLAYBOOK_RULES'",
            "stable_key": "TEXT",
            "campaign_id": "INTEGER",
            "ad_group_id": "INTEGER",
            "action_payload": "JSON",
            "evidence_json": "JSON",
            "impact_micros": "INTEGER",
            "impact_score": "FLOAT",
            "confidence_score": "FLOAT",
            "risk_score": "FLOAT",
            "score": "FLOAT",
            "executable": "INTEGER DEFAULT 0",
            "expires_at": "DATETIME",
            "google_resource_name": "TEXT",
            "context_outcome": "TEXT",
            "blocked_reasons": "JSON",
            "downgrade_reasons": "JSON",
        },
        "action_log": {
            "execution_mode": "TEXT DEFAULT 'LIVE'",
            "precondition_status": "TEXT",
            "context_json": "JSON",
            "action_payload": "JSON",
        },
    }

    with engine.begin() as conn:
        inspector = inspect(conn)
        for table_name, columns in schema_updates.items():
            if not inspector.has_table(table_name):
                continue
            existing = {col["name"] for col in inspector.get_columns(table_name)}
            for column_name, column_type in columns.items():
                if column_name in existing:
                    continue
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))

        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_recommendations_stable_key ON recommendations (stable_key)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_recommendations_campaign_id ON recommendations (campaign_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_recommendations_ad_group_id ON recommendations (ad_group_id)"))


def init_db():
    """Create all tables. Call once at startup."""
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()
