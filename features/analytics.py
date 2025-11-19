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
    from datetime import timedelta
    from features.notion_utils import get_tasks_raw
    
    with _conn() as conn:
        # Pomodoro sessions
        cur = conn.execute("SELECT COUNT(*) FROM pomodoro_sessions WHERE kind='work' AND started_at >= datetime('now', '-7 days')")
        work_count = cur.fetchone()[0]
        
        # Habit logs
        cur = conn.execute("SELECT COUNT(*) FROM habit_logs WHERE logged_at >= datetime('now', '-7 days')")
        habit_count = cur.fetchone()[0]
        
        # Daily breakdown for pomodoros
        cur = conn.execute("""
            SELECT date(started_at) as day, COUNT(*) as count 
            FROM pomodoro_sessions 
            WHERE kind='work' AND started_at >= datetime('now', '-7 days')
            GROUP BY date(started_at)
            ORDER BY day DESC
        """)
        daily_pomodoro = cur.fetchall()
        
        # Daily breakdown for habits
        cur = conn.execute("""
            SELECT date(logged_at) as day, COUNT(*) as count 
            FROM habit_logs 
            WHERE logged_at >= datetime('now', '-7 days')
            GROUP BY date(logged_at)
            ORDER BY day DESC
        """)
        daily_habits = cur.fetchall()
    
    # Get completed tasks from Notion
    try:
        tasks = get_tasks_raw()
        completed_count = sum(1 for task in tasks 
                             if task.get("properties", {}).get("Status", {}).get("status", {}).get("name") == "Completed")
        in_progress_count = sum(1 for task in tasks 
                               if task.get("properties", {}).get("Status", {}).get("status", {}).get("name") == "In progress")
        not_started_count = sum(1 for task in tasks 
                               if task.get("properties", {}).get("Status", {}).get("status", {}).get("name") == "Not started")
    except:
        completed_count = 0
        in_progress_count = 0
        not_started_count = 0
    
    # Calculate metrics
    total_minutes = work_count * 25
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    # Calculate productivity score
    activity_score = (work_count * 2) + (habit_count * 1) + (completed_count * 3)
    if activity_score >= 50:
        trend = "On fire"
    elif activity_score >= 30:
        trend = "Strong momentum"
    elif activity_score >= 15:
        trend = "Steady progress"
    else:
        trend = "Building habits"
    
    # Build report
    lines = ["📊 Productivity Analytics (Last 7 Days)\n"]
    
    # Overview
    lines.append("📈 OVERVIEW:")
    lines.append(f"  Focus sessions: {work_count} ({hours}h {minutes}m)")
    lines.append(f"  Habits logged: {habit_count}")
    lines.append(f"  Tasks completed: {completed_count}")
    lines.append(f"  Trend: {trend}\n")
    
    # Task breakdown
    total_tasks = completed_count + in_progress_count + not_started_count
    if total_tasks > 0:
        completion_rate = (completed_count / total_tasks) * 100
        lines.append("✅ TASK PROGRESS:")
        lines.append(f"  Completed: {completed_count}/{total_tasks} ({completion_rate:.0f}%)")
        lines.append(f"  In progress: {in_progress_count}")
        lines.append(f"  Not started: {not_started_count}\n")
    
    # Daily activity visualization - start from Monday
    pomodoro_dict = {day: count for day, count in daily_pomodoro}
    habit_dict = {day: count for day, count in daily_habits}
    today = datetime.utcnow().date()
    
    # Find the most recent Monday
    days_since_monday = today.weekday()  # 0 = Monday, 6 = Sunday
    monday = today - timedelta(days=days_since_monday)
    
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    lines.append("📅 DAILY ACTIVITY:")
    for i in range(7):  # Monday to Sunday
        day_date = monday + timedelta(days=i)
        day_str = day_date.strftime("%Y-%m-%d")
        pom_count = pomodoro_dict.get(day_str, 0)
        hab_count = habit_dict.get(day_str, 0)
        day_name = days[i]
        
        if day_date == today:
            day_label = f"{day_name} (today)"
        else:
            day_label = day_name
        
        lines.append(f"  {day_label:13} {pom_count} sessions, {hab_count} habits")
    
    return "\n".join(lines)


def work_sessions_today(user_id: int) -> int:
    """Count work sessions started today (UTC)."""
    with _conn() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM pomodoro_sessions WHERE user_id = ? AND kind='work' AND date(started_at) = date('now')",
            (user_id,)
        )
        return int(cur.fetchone()[0] or 0)
