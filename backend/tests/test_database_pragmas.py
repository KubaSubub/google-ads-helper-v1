"""Regression tests for SQLite PRAGMA settings in app.database.

Guards against silent removal of `busy_timeout`, whose absence causes
spurious HTTP 500s under concurrent writers (bulk sync across clients).
"""

import threading
import time

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.database import _set_sqlite_pragma


def _make_engine(db_path):
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    event.listen(engine, "connect", _set_sqlite_pragma)
    return engine


def test_busy_timeout_pragma_is_set(tmp_path):
    """Every new connection must report busy_timeout >= 30000 ms.
    Increased from 5000ms to reduce 'database is locked' 500s when
    recommendations persist concurrently with an active sync.
    """
    engine = _make_engine(tmp_path / "pragma.db")
    with engine.connect() as conn:
        value = conn.execute(text("PRAGMA busy_timeout")).scalar()
        assert value >= 30000, f"expected busy_timeout>=30000, got {value}"


def test_journal_mode_and_foreign_keys(tmp_path):
    """Sanity check the other two PRAGMAs still apply."""
    engine = _make_engine(tmp_path / "pragma.db")
    with engine.connect() as conn:
        journal = conn.execute(text("PRAGMA journal_mode")).scalar()
        fk = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert journal.lower() == "wal"
        assert fk == 1


def test_concurrent_writers_do_not_raise_database_locked(tmp_path):
    """Two threads writing to the same table must not raise 'database is locked'.

    Without busy_timeout, a simultaneous writer would fail immediately.
    With busy_timeout=5000, SQLite waits for the other transaction to
    commit (well under 5s for this tiny workload).
    """
    engine = _make_engine(tmp_path / "concurrent.db")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY, v INTEGER)"))

    Session = sessionmaker(bind=engine)
    errors = []
    barrier = threading.Barrier(2)

    def writer(thread_id: int):
        try:
            session = Session()
            barrier.wait()  # both threads start writing at the same time
            for i in range(50):
                session.execute(
                    text("INSERT INTO t (v) VALUES (:v)"),
                    {"v": thread_id * 1000 + i},
                )
                session.commit()
        except Exception as exc:  # pragma: no cover - should not happen
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=writer, args=(i,)) for i in (1, 2)]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)
    elapsed = time.time() - start

    assert not errors, f"concurrent writers raised: {errors}"
    assert elapsed < 10, f"writers took {elapsed:.1f}s (busy_timeout not effective?)"

    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM t")).scalar()
        assert total == 100
