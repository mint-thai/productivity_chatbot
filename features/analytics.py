import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "kairos.db")
DB_PATH = os.path.abspath(DB_PATH)


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS pomodoro_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                kind TEXT NOT NULL, -- 'work' or 'break'
                task TEXT
            )
        """)
        conn.commit()


def log_session_start(user_id: int, kind: str, task: str | None):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO pomodoro_sessions(user_id, started_at, kind, task) VALUES (?, ?, ?, ?)",
            (user_id, datetime.utcnow().isoformat(), kind, task)
        )
        conn.commit()


def log_session_end(user_id: int, kind: str):
    with _conn() as conn:
        # update the latest open session of this kind for user
        cur = conn.execute(
            "SELECT id FROM pomodoro_sessions WHERE user_id = ? AND kind = ? AND ended_at IS NULL ORDER BY id DESC LIMIT 1",
            (user_id, kind)
        )
        row = cur.fetchone()
        if row:
            conn.execute(
                "UPDATE pomodoro_sessions SET ended_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), row[0])
            )
            conn.commit()


def summary_last_7_days() -> str:
    with _conn() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM pomodoro_sessions WHERE kind='work' AND started_at >= datetime('now', '-7 days')")
        work_count = cur.fetchone()[0]
        cur = conn.execute("SELECT COUNT(*) FROM pomodoro_sessions WHERE kind='break' AND started_at >= datetime('now', '-7 days')")
        break_count = cur.fetchone()[0]
    lines = ["Your last 7 days:"]
    lines.append(f"- Pomodoro work sessions: {work_count}")
    lines.append(f"- Break sessions: {break_count}")
    return "\n".join(lines)


def work_sessions_today(user_id: int) -> int:
    """Count work sessions started today (UTC)."""
    with _conn() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM pomodoro_sessions WHERE user_id = ? AND kind='work' AND date(started_at) = date('now')",
            (user_id,)
        )
        return int(cur.fetchone()[0] or 0)
