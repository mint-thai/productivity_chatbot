"""
In-app reminder system using Telegram messages (no email).
Schedules daily checks for upcoming tasks and sends summaries in chat.
"""

from datetime import datetime, timedelta, time as dt_time
from typing import Tuple
from telegram.ext import ContextTypes

from features.notion_utils import get_tasks_raw
from features.view import format_tasks_list
from features.analytics import work_sessions_today
from features.habits import logs_today


def _upcoming_tasks_within_hours(hours: int = 24):
	now = datetime.now()
	cutoff = now + timedelta(hours=hours)
	tasks = []
	for row in get_tasks_raw():
		try:
			props = row.get("properties", {})
			status = props.get("Status", {}).get("status", {}).get("name", "Unknown")
			if status == "Completed":
				continue
			due_obj = props.get("Due date", {}).get("date")
			due_start = due_obj.get("start") if isinstance(due_obj, dict) else None
			if not due_start:
				continue
			date_part = due_start[:10]
			due_dt = datetime.strptime(date_part, "%Y-%m-%d")
			if now <= due_dt <= cutoff:
				tasks.append(row)
		except Exception:
			continue
	return tasks


def build_reminder_message(hours: int = 24) -> Tuple[str, int]:
	rows = _upcoming_tasks_within_hours(hours)
	count = len(rows)
	if count == 0:
		return ("No tasks due soon.", 0)
	formatted = format_tasks_list(rows)
	header = f"You have {count} task(s) due in the next {hours} hours.\n\n"
	return (header + formatted, count)


async def scheduled_reminder_callback(context: ContextTypes.DEFAULT_TYPE):
	message, count = build_reminder_message(hours=24)
	if count > 0:
		await context.bot.send_message(chat_id=context.job.chat_id, text=message, parse_mode="Markdown")


# --- Motivational nudges ---
def build_nudge_message(user_id: int) -> str | None:
	sessions = work_sessions_today(user_id)
	habit_logs = logs_today()
	if sessions == 0 and habit_logs == 0:
		return (
			"You haven't logged any focus sessions or habits today. "
			"Pick one small task and start a 25-minute Pomodoro. You've got this."
		)
	if sessions < 2:
		return (
			"Nice start today. If you can, aim for one more Pomodoro to keep momentum."
		)
	return None


async def scheduled_nudge_callback(context: ContextTypes.DEFAULT_TYPE):
	user_id = context.job.user_id
	msg = build_nudge_message(user_id)
	if msg:
		await context.bot.send_message(chat_id=context.job.chat_id, text=msg)


def enable_daily_reminders(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, hour: int = 8, minute: int = 0):
	# Remove existing
	name = f"daily_reminder_{user_id}"
	for job in context.job_queue.get_jobs_by_name(name):
		job.schedule_removal()

	context.job_queue.run_daily(
		callback=scheduled_reminder_callback,
		time=dt_time(hour=hour, minute=minute),
		name=name,
		chat_id=chat_id,
		user_id=user_id,
	)


def disable_daily_reminders(context: ContextTypes.DEFAULT_TYPE, user_id: int):
	name = f"daily_reminder_{user_id}"
	jobs = context.job_queue.get_jobs_by_name(name)
	for job in jobs:
		job.schedule_removal()
	return len(jobs)


def enable_daily_nudges(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, hour: int = 18, minute: int = 0):
	name = f"daily_nudge_{user_id}"
	for job in context.job_queue.get_jobs_by_name(name):
		job.schedule_removal()
	context.job_queue.run_daily(
		callback=scheduled_nudge_callback,
		time=dt_time(hour=hour, minute=minute),
		name=name,
		chat_id=chat_id,
		user_id=user_id,
	)


def disable_daily_nudges(context: ContextTypes.DEFAULT_TYPE, user_id: int):
	name = f"daily_nudge_{user_id}"
	jobs = context.job_queue.get_jobs_by_name(name)
	for job in jobs:
		job.schedule_removal()
	return len(jobs)
