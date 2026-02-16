"""SQLAlchemy database engine and session factory for SQLite."""

from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


# Ensure the database directory exists (SQLite won't create parent dirs)
_db_path = settings.database_url.replace("sqlite:///", "")
Path(_db_path).parent.mkdir(parents=True, exist_ok=True)

# SQLite-specific: enable WAL mode and foreign keys for performance & integrity
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # Required for SQLite + FastAPI
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
    pass


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Call once at startup."""
    # Import all models so Base.metadata knows about them
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
