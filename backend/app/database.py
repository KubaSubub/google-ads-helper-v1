"""SQLAlchemy database engine and session factory for SQLite."""

from pathlib import Path
import shutil

from loguru import logger
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _sqlite_path_from_url(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None

    path_part = database_url.removeprefix("sqlite:///")
    if path_part in {"", ":memory:"}:
        return None

    return Path(path_part)


def _migrate_legacy_sqlite_path() -> Path | None:
    db_path = _sqlite_path_from_url(settings.database_url)
    if db_path is None:
        return None

    legacy_path = settings.backend_dir / "data" / db_path.name
    if legacy_path.resolve() == db_path.resolve():
        return db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        if legacy_path.exists():
            logger.warning(
                "Runtime SQLite database is {}. Legacy copy remains at {} and will be ignored.",
                db_path,
                legacy_path,
            )
        return db_path

    if not legacy_path.exists():
        return db_path

    for suffix in ("", "-wal", "-shm"):
        legacy_variant = Path(f"{legacy_path}{suffix}")
        if not legacy_variant.exists():
            continue

        target_variant = Path(f"{db_path}{suffix}")
        target_variant.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(legacy_variant), str(target_variant))

    logger.warning(
        "Migrated SQLite runtime data from legacy path {} to canonical path {}.",
        legacy_path,
        db_path,
    )
    return db_path


_db_path = _migrate_legacy_sqlite_path() or _sqlite_path_from_url(settings.database_url)
if _db_path is not None:
    _db_path.parent.mkdir(parents=True, exist_ok=True)

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
    # Wait up to 30s for a lock instead of failing immediately with
    # "database is locked". Prevents spurious 500s when multiple writers
    # contend (e.g. recommendations persist during sync across several clients).
    cursor.execute("PRAGMA busy_timeout=30000")
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
            "campaign_subtype": "TEXT",
            "campaign_role_auto": "TEXT",
            "campaign_role_final": "TEXT",
            "role_confidence": "FLOAT",
            "protection_level": "TEXT",
            "role_source": "TEXT DEFAULT 'AUTO'",
            "labels": "TEXT",
            "target_cpa_micros": "INTEGER",
            "target_roas": "FLOAT",
            "primary_status": "TEXT",
            "primary_status_reasons": "TEXT",
            "bidding_strategy_resource_name": "TEXT",
            "portfolio_bid_strategy_id": "TEXT",
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
        "keywords": {
            "criterion_kind": "TEXT DEFAULT 'POSITIVE'",
        },
        "metrics_segmented": {
            "ad_network_type": "TEXT",
            "age_range": "TEXT",
            "gender": "TEXT",
        },
        "negative_keywords": {
            "ad_group_id": "INTEGER",
            "google_criterion_id": "TEXT",
            "google_resource_name": "TEXT",
            "criterion_kind": "TEXT DEFAULT 'NEGATIVE'",
            "negative_scope": "TEXT DEFAULT 'CAMPAIGN'",
            "source": "TEXT DEFAULT 'LOCAL_ACTION'",
            "updated_at": "DATETIME",
        },
        "clients": {
            "currency": "TEXT DEFAULT 'PLN'",
            "strategy_context": "TEXT",
            "script_configs": "TEXT",
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
        # Composite index for time-range queries on /dashboard-kpis, /trends, /correlation, /wow-comparison.
        # The uq_metric_daily UNIQUE constraint gives SQLite an autoindex on the same columns,
        # but a named index makes ANALYZE results stable and the planner choice explicit.
        if inspector.has_table("metrics_daily"):
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_metrics_daily_campaign_date ON metrics_daily (campaign_id, date)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_keywords_criterion_kind ON keywords (criterion_kind)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_negative_keywords_google_criterion_id ON negative_keywords (google_criterion_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_negative_keywords_negative_scope ON negative_keywords (negative_scope)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_negative_keywords_source ON negative_keywords (source)"))

        if inspector.has_table("keywords"):
            conn.execute(text("UPDATE keywords SET criterion_kind = 'POSITIVE' WHERE criterion_kind IS NULL OR criterion_kind = ''"))

        if inspector.has_table("negative_keywords"):
            negative_existing = {col["name"] for col in inspector.get_columns("negative_keywords")}
            conn.execute(text("UPDATE negative_keywords SET criterion_kind = 'NEGATIVE' WHERE criterion_kind IS NULL OR criterion_kind = ''"))
            conn.execute(text("UPDATE negative_keywords SET status = 'ENABLED' WHERE status = 'ACTIVE' OR status IS NULL OR status = ''"))
            if "level" in negative_existing:
                conn.execute(text("UPDATE negative_keywords SET negative_scope = COALESCE(NULLIF(negative_scope, ''), NULLIF(level, ''), 'CAMPAIGN')"))
            else:
                conn.execute(text("UPDATE negative_keywords SET negative_scope = COALESCE(NULLIF(negative_scope, ''), 'CAMPAIGN')"))
            conn.execute(text("UPDATE negative_keywords SET source = 'LOCAL_ACTION' WHERE source IS NULL OR source = ''"))
            conn.execute(text("UPDATE negative_keywords SET updated_at = created_at WHERE updated_at IS NULL"))

        # BUG-H1 fix: SQLite NULL != NULL in UNIQUE constraints allows duplicate rows.
        # Add a functional unique index using COALESCE to treat NULLs as sentinel values.
        # The index MUST include every dimension column that sync_*_metrics sets —
        # otherwise rows from different segmentation types (parental/income) collide
        # with each other on the (campaign, date, null_*) slot and fail on commit.
        # Refresh planner statistics after any schema/index changes above.
        conn.execute(text("ANALYZE"))

        if inspector.has_table("metrics_segmented"):
            # Drop old index that didn't include parental_status / income_range
            conn.execute(text("DROP INDEX IF EXISTS uq_metric_segmented_coalesced"))
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_metric_segmented_coalesced "
                "ON metrics_segmented("
                "campaign_id, date, "
                "COALESCE(device, '__NONE__'), "
                "COALESCE(geo_city, '__NONE__'), "
                "COALESCE(hour_of_day, -1), "
                "COALESCE(age_range, '__NONE__'), "
                "COALESCE(gender, '__NONE__'), "
                "COALESCE(parental_status, '__NONE__'), "
                "COALESCE(income_range, '__NONE__'), "
                "COALESCE(ad_network_type, '__NONE__'))"
            ))


def init_db():
    """Create all tables. Call once at startup."""
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()
