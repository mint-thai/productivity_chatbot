import os
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "kairos.db")
DB_PATH = os.path.abspath(DB_PATH)


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS habit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                logged_at TEXT NOT NULL,
                FOREIGN KEY(habit_id) REFERENCES habits(id)
            )
        """)
        conn.commit()


def add_habit(name: str) -> str:
    name = name.strip()
    if not name:
        return "Please provide a habit name."
    try:
        with _conn() as conn:
            conn.execute("INSERT OR IGNORE INTO habits(name) VALUES (?)", (name,))
            conn.commit()
        return f"Habit added: {name}"
    except Exception as e:
        return f"Failed to add habit: {e}"


def log_habit(name: str) -> str:
    name = name.strip()
    if not name:
        return "Please provide a habit name."
    try:
        with _conn() as conn:
            cur = conn.execute("SELECT id FROM habits WHERE name = ?", (name,))
            row = cur.fetchone()
            if not row:
                return "Habit not found. Use /habit_add <name> first."
            habit_id = row[0]
            now = datetime.utcnow().isoformat()
            conn.execute("INSERT INTO habit_logs(habit_id, logged_at) VALUES (?, ?)", (habit_id, now))
            conn.commit()
        return f"Logged habit: {name}"
    except Exception as e:
        return f"Failed to log habit: {e}"


def list_habits() -> str:
    try:
        with _conn() as conn:
            cur = conn.execute("SELECT h.name, COUNT(l.id) FROM habits h LEFT JOIN habit_logs l ON l.habit_id = h.id GROUP BY h.id ORDER BY h.name")
            rows = cur.fetchall()
        if not rows:
            return "No habits yet. Add one with /habit_add <name>."
        lines = ["Your habits:"]
        for name, count in rows:
            lines.append(f"- {name} (logged {count} times)")
        return "\n".join(lines)
    except Exception as e:
        return f"Failed to list habits: {e}"


def current_streak(name: str) -> str:
    try:
        with _conn() as conn:
            cur = conn.execute("SELECT id FROM habits WHERE name = ?", (name,))
            row = cur.fetchone()
            if not row:
                return "Habit not found."
            habit_id = row[0]
            cur = conn.execute("SELECT date(logged_at) FROM habit_logs WHERE habit_id = ? ORDER BY logged_at DESC", (habit_id,))
            dates = [datetime.fromisoformat(d + "T00:00:00").date() for (d,) in cur.fetchall()]
        if not dates:
            return "No logs yet."
        streak = 0
        today = datetime.utcnow().date()
        day = today
        while day in dates:
            streak += 1
            day = day - timedelta(days=1)
        return f"Current streak for {name}: {streak} day(s)."
    except Exception as e:
        return f"Failed to compute streak: {e}"


def logs_today() -> int:
    """Count total habit logs made today (UTC)."""
    try:
        with _conn() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM habit_logs WHERE date(logged_at) = date('now')")
            return int(cur.fetchone()[0] or 0)
    except Exception:
        return 0
