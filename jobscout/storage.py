from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from jobscout.config import DB_FILE
from jobscout.schemas import JobPosting


def make_job_id(company: str, job: JobPosting) -> str:
    raw = f"{company}:{job.url or job.title}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def init_db() -> None:
    with closing(sqlite3.connect(DB_FILE)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                location TEXT,
                department TEXT,
                posted_date TEXT,
                description TEXT,
                summary_json TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
            """
        )
        conn.commit()


def is_known(company: str, job: JobPosting) -> bool:
    """Whether this job already has a stored row - used to skip re-summarizing
    jobs the LLM has already distilled, since the summary rarely needs refreshing."""
    init_db()
    job_id = make_job_id(company, job)
    with closing(sqlite3.connect(DB_FILE)) as conn:
        return conn.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone() is not None


def upsert_jobs(company: str, jobs: list[JobPosting]) -> list[JobPosting]:
    """Insert new jobs, refresh last_seen/description on known ones. Returns the newly-seen jobs.

    summary_json is only written on first insert - it's deliberately left untouched on
    updates so a rescan doesn't silently discard an already-computed summary.
    """
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    new_jobs: list[JobPosting] = []
    with closing(sqlite3.connect(DB_FILE)) as conn:
        for job in jobs:
            job_id = make_job_id(company, job)
            existing = conn.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if existing is None:
                summary_json = job.summary.model_dump_json() if job.summary else ""
                conn.execute(
                    """
                    INSERT INTO jobs
                        (id, company, title, url, location, department, posted_date,
                         description, summary_json, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        company,
                        job.title,
                        job.url,
                        job.location,
                        job.department,
                        job.posted_date,
                        job.description,
                        summary_json,
                        now,
                        now,
                    ),
                )
                new_jobs.append(job)
            else:
                conn.execute(
                    "UPDATE jobs SET last_seen = ?, description = ? WHERE id = ?",
                    (now, job.description, job_id),
                )
        conn.commit()
    return new_jobs


def get_all_jobs(company: str | None = None) -> list[dict]:
    init_db()
    with closing(sqlite3.connect(DB_FILE)) as conn:
        conn.row_factory = sqlite3.Row
        if company:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE company = ? ORDER BY first_seen DESC", (company,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM jobs ORDER BY first_seen DESC").fetchall()
        return [dict(row) for row in rows]


def delete_jobs(company: str | None = None) -> int:
    """Delete stored jobs so the next scan treats them as new again. Returns count deleted."""
    init_db()
    with closing(sqlite3.connect(DB_FILE)) as conn:
        if company:
            cursor = conn.execute("DELETE FROM jobs WHERE company = ?", (company,))
        else:
            cursor = conn.execute("DELETE FROM jobs")
        conn.commit()
        return cursor.rowcount


def get_companies_in_db() -> list[str]:
    init_db()
    with closing(sqlite3.connect(DB_FILE)) as conn:
        rows = conn.execute("SELECT DISTINCT company FROM jobs ORDER BY company").fetchall()
        return [row[0] for row in rows]
