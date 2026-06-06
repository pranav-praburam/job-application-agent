import sqlite3
import os
from contextlib import contextmanager

VALID_STATUSES = {"new", "applied", "interview", "offer", "rejected", "skipped"}


class Database:
    def __init__(self, path: str = "data/applications.db"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self._init_schema()
        self._migrate()

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    title       TEXT NOT NULL,
                    company     TEXT NOT NULL,
                    location    TEXT,
                    url         TEXT UNIQUE,
                    description TEXT,
                    source      TEXT,
                    match_score REAL,
                    status      TEXT NOT NULL DEFAULT 'new',
                    posted_at   TEXT,
                    found_at    TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS applications (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id          INTEGER NOT NULL REFERENCES jobs(id),
                    applied_at      TEXT,
                    resume_version  TEXT,
                    cover_letter    TEXT,
                    notes           TEXT,
                    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS events (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id      INTEGER NOT NULL REFERENCES jobs(id),
                    event_type  TEXT NOT NULL,
                    detail      TEXT,
                    occurred_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
            """)

    def _migrate(self):
        with self._conn() as conn:
            existing = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
            }
            for col, defn in [
                ("match_score", "REAL"),
                ("status", "TEXT NOT NULL DEFAULT 'new'"),
            ]:
                if col not in existing:
                    conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} {defn}")

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # --- jobs ---

    def upsert_job(self, title: str, company: str, url: str, **kwargs) -> int:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO jobs (title, company, url, location, description, source, match_score, posted_at)
                VALUES (:title, :company, :url, :location, :description, :source, :match_score, :posted_at)
                ON CONFLICT(url) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    match_score=excluded.match_score
                """,
                {
                    "title": title, "company": company, "url": url,
                    "location": kwargs.get("location"),
                    "description": kwargs.get("description"),
                    "source": kwargs.get("source"),
                    "match_score": kwargs.get("match_score"),
                    "posted_at": kwargs.get("posted_at"),
                },
            )
            row = conn.execute("SELECT id FROM jobs WHERE url=?", (url,)).fetchone()
            return row["id"]

    def update_job_status(self, job_id: int, status: str):
        if status not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        with self._conn() as conn:
            conn.execute(
                "UPDATE jobs SET status=? WHERE id=?",
                (status, job_id),
            )

    def get_jobs(self, limit: int = 100) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY match_score DESC NULLS LAST, found_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_job_status_counts(self) -> dict[str, int]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as n FROM jobs GROUP BY status"
            ).fetchall()
            return {r["status"]: r["n"] for r in rows}
