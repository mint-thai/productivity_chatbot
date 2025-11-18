"""
Pomodoro Timer using Telegram Bot's Job Queue
Non-blocking implementation with status tracking
"""

from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

# Store active timers per user
active_timers = {}

WORK_MINUTES = 25
BREAK_MINUTES = 5


async def pomodoro_work_complete(context: ContextTypes.DEFAULT_TYPE):
    """Callback when work session completes"""
    job = context.job
    user_id = job.user_id
    chat_id = job.chat_id
    
    if user_id in active_timers:
        del active_timers[user_id]
    
    # Log end
    try:
        from features.analytics import log_session_end
        log_session_end(user_id, "work")
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=chat_id,
        text="Time's up. Take a 5-minute break. Use /pomodoro_break to start your break timer."
    )


async def pomodoro_break_complete(context: ContextTypes.DEFAULT_TYPE):
    """Callback when break session completes"""
    job = context.job
    user_id = job.user_id
    chat_id = job.chat_id
    
    if user_id in active_timers:
        del active_timers[user_id]
    
    # Log end
    try:
        from features.analytics import log_session_end
        log_session_end(user_id, "break")
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=chat_id,
        text="Break's over. Ready for another Pomodoro? Use /pomodoro to start a new focus session."
    )


async def start_pomodoro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a 25-minute work session"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if user_id in active_timers:
        remaining = active_timers[user_id]['end_time'] - datetime.now()
        minutes = int(remaining.total_seconds() // 60)
        seconds = int(remaining.total_seconds() % 60)
        timer_type = active_timers[user_id]['type']
        
        await update.message.reply_text(
            f"You already have an active {timer_type} timer.\n"
            f"Time remaining: {minutes:02d}:{seconds:02d}\n\n"
            f"Use /pomodoro_stop to cancel it."
        )
        return
    
    task = " ".join(context.args) if context.args else None
    
    end_time = datetime.now() + timedelta(minutes=WORK_MINUTES)
    active_timers[user_id] = {
        'end_time': end_time,
        'type': 'work',
        'task': task,
        'chat_id': chat_id
    }
    
    context.job_queue.run_once(
        pomodoro_work_complete,
        WORK_MINUTES * 60,
        chat_id=chat_id,
        user_id=user_id,
        name=f"pomodoro_work_{user_id}"
    )
    
    task_msg = f"\nTask: {task}" if task else ""
    # Log start
    try:
        from features.analytics import init_db, log_session_start
        init_db()
        log_session_start(user_id, "work", task)
    except Exception:
        pass

    await update.message.reply_text(
        f"Pomodoro started. {WORK_MINUTES} minutes of focused work{task_msg}.\n"
        f"Use /pomodoro_status to check remaining time.\n"
        f"Use /pomodoro_stop to cancel."
    )


async def start_break(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a 5-minute break"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if user_id in active_timers:
        remaining = active_timers[user_id]['end_time'] - datetime.now()
        minutes = int(remaining.total_seconds() // 60)
        seconds = int(remaining.total_seconds() % 60)
        
        await update.message.reply_text(
            f"You already have an active timer.\n"
            f"Time remaining: {minutes:02d}:{seconds:02d}"
        )
        return
    
    end_time = datetime.now() + timedelta(minutes=BREAK_MINUTES)
    active_timers[user_id] = {
        'end_time': end_time,
        'type': 'break',
        'task': None,
        'chat_id': chat_id
    }
    
    context.job_queue.run_once(
        pomodoro_break_complete,
        BREAK_MINUTES * 60,
        chat_id=chat_id,
        user_id=user_id,
        name=f"pomodoro_break_{user_id}"
    )
    
    # Log start
    try:
        from features.analytics import init_db, log_session_start
        init_db()
        log_session_start(user_id, "break", None)
    except Exception:
        pass

    await update.message.reply_text(
        f"Break started. {BREAK_MINUTES} minutes to recharge."
    )


async def pomodoro_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check current Pomodoro status"""
    user_id = update.effective_user.id
    
    if user_id not in active_timers:
        await update.message.reply_text(
            "No active Pomodoro session. Use /pomodoro to start a 25-minute focus session."
        )
        return
    
    timer = active_timers[user_id]
    remaining = timer['end_time'] - datetime.now()
    
    if remaining.total_seconds() <= 0:
        await update.message.reply_text("Time's up.")
        return
    
    minutes = int(remaining.total_seconds() // 60)
    seconds = int(remaining.total_seconds() % 60)
    
    if timer['type'] == 'work':
        task_msg = f"\nWorking on: {timer['task']}" if timer['task'] else ""
        icon = ""
        status = "Focus time"
    else:
        task_msg = ""
        icon = ""
        status = "Break time"
    
    await update.message.reply_text(
        f"{status}\n"
        f"Time remaining: {minutes:02d}:{seconds:02d}{task_msg}"
    )


async def stop_pomodoro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop/cancel current Pomodoro"""
    user_id = update.effective_user.id
    
    if user_id not in active_timers:
        await update.message.reply_text("No active Pomodoro session to stop.")
        return
    
    # Get all jobs for this user (both work and break)
    work_jobs = context.job_queue.get_jobs_by_name(f"pomodoro_work_{user_id}")
    break_jobs = context.job_queue.get_jobs_by_name(f"pomodoro_break_{user_id}")
    all_jobs = list(work_jobs) + list(break_jobs)
    
    for job in all_jobs:
        job.schedule_removal()
    
    del active_timers[user_id]
    
    # Log end of whichever was active
    try:
        from features.analytics import log_session_end
        kind = timer_type = 'work' if any(context.job_queue.get_jobs_by_name(f"pomodoro_work_{user_id}")) else 'break'
        log_session_end(user_id, kind)
    except Exception:
        pass

    await update.message.reply_text("Pomodoro stopped.")
