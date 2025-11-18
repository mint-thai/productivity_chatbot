import os
import json
import re
from datetime import datetime, time as dt_time
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import google.generativeai as genai

from features.notion_utils import get_tasks_raw, set_task_status_by_name
from features.view import format_tasks_list
from features.add import add_task_from_text
from features.pomodoro import start_pomodoro, start_break, pomodoro_status, stop_pomodoro
from features.telegram_reminders import enable_daily_reminders, disable_daily_reminders, enable_daily_nudges, disable_daily_nudges
from features.habits import init_db as habits_init, add_habit, log_habit, list_habits, current_streak
from features.analytics import init_db as analytics_init, summary_last_7_days
from features.recommend import recommend, format_recommendations
from features.music import get_focus_link
from features.schedule_parser import parse_text_to_tasks, tasks_from_pdf_bytes
from app.config import validate_env

# --- Load environment variables ---
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Configure Gemini ---
genai.configure(api_key=GOOGLE_API_KEY)
MODEL = "gemini-2.5-flash"
llm = genai.GenerativeModel(MODEL)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi, I'm Kairos, a student-friendly productivity assistant.\n"
        "I help you manage tasks, focus with Pomodoro, track habits, and stay on top of deadlines.\n\n"
        "Task commands:\n"
        "- /tasks — View your Notion tasks\n"
        "- /add <task> — Add a new task to Notion\n"
        "- /done <task> — Mark a task completed\n"
    "- /status <task>, <Not started|In Progress|Completed> — Update status\n\n"
        "Pomodoro:\n"
        "- /pomodoro [task] — Start a 25-min focus session\n"
        "- /pomodoro_break — Start a 5-min break\n"
        "- /pomodoro_status — Check timer status\n"
        "- /pomodoro_stop — Stop current session\n\n"
        "Reminders (in-app):\n"
        "- /reminder_enable — Daily reminders at 8:00 AM\n"
        "- /reminder_disable — Turn off daily reminders\n\n"
    "Nudges:\n"
    "- /nudges_enable — Encouraging daily nudges at 6:00 PM\n"
    "- /nudges_disable — Turn off nudges\n\n"
        "Habits:\n"
        "- /habit_add <name>\n"
        "- /habit_log <name>\n"
    "- /habit_list\n"
    "- /habit_streak <name>\n\n"
        "Recommendations and analytics:\n"
        "- /recommend — Next best tasks\n"
        "- /analytics — Your weekly focus summary\n\n"
        "Focus mode:\n"
        "- /focus_on — Get a focus music link\n\n"
        "Import schedule:\n"
        "- /import_schedule <pasted text> or reply to a PDF with /import_schedule\n\n"
        "You can also ask questions about productivity. I'll keep it real and helpful.",
        parse_mode="Markdown"
    )


async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List tasks from Notion"""
    await update.message.reply_text("Fetching your tasks...")
    try:
        raw_tasks = get_tasks_raw()
        formatted = format_tasks_list(raw_tasks)
        await update.message.reply_text(formatted, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error retrieving tasks: {e}")


async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new task to Notion"""
    task_text = " ".join(context.args).strip()
    
    if not task_text:
        await update.message.reply_text(
            "To add a task, use:\n"
            "/add <task description>\n\n"
            "Examples:\n"
            "• /add Study for exam\n"
            "• /add Finish homework [high] due:tomorrow\n"
            "• /add Review notes due:2025-01-15 project:Math\n\n"
            "Options:\n"
            "• Priority: [high], [medium], [low]\n"
            "• Due date: due:today, due:tomorrow, due:nextweek, due:YYYY-MM-DD\n"
            "• Project: project:ProjectName"
        )
        return
    
    await update.message.reply_text("Creating your task...")
    
    try:
        result = add_task_from_text(task_text)
        await update.message.reply_text(result["message"], parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error adding task: {e}")


async def send_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deprecated: switch to in-app reminders."""
    await update.message.reply_text("Use /reminder_enable to receive in-app reminders each morning at 8 AM.")


async def enable_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable daily in-app reminders"""
    enable_daily_reminders(context, update.effective_user.id, update.effective_chat.id, hour=8, minute=0)
    await update.message.reply_text(
        "Daily reminders enabled. You'll get a message at 8:00 AM when you have tasks due soon."
    )


async def disable_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable in-app reminders"""
    removed = disable_daily_reminders(context, update.effective_user.id)
    if removed:
        await update.message.reply_text("Daily reminders disabled.")
    else:
        await update.message.reply_text("No active reminders to disable.")


async def scheduled_reminder_callback(context: ContextTypes.DEFAULT_TYPE):
    # kept for backward compatibility; handled in telegram_reminders module
    pass


# Pomodoro command handlers map directly to pomodoro.py functions
# These are just wrappers that pass the update and context to the actual implementations


# --- Natural language intent parsing and execution ---
async def try_natural_action(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Use Gemini to interpret the user's message and perform an action if confidently understood.

    Supported intents:
      - update_status: { task_name, status }
      - mark_done: { task_name }
      - add_task: { add_task_text }
      - start_pomodoro: { task_name? }
      - stop_pomodoro: {}
      - habit_add: { habit_name }
      - habit_log: { habit_name }
      - enable_reminders | disable_reminders | enable_nudges | disable_nudges

    Returns True if an action was executed, else False.
    """
    try:
        # Provide current task titles to help the model resolve names
        task_rows = get_tasks_raw()
        task_titles = []
        for row in task_rows:
            title_arr = (row.get("properties", {}).get("Task", {}).get("title") or [])
            if title_arr:
                task_titles.append(title_arr[0].get("plain_text", "").strip())

        task_titles_str = "\n".join(f"- {t}" for t in task_titles[:50])  # cap to 50 for brevity

        instruction = f"""
You are an assistant that converts a user's natural language request into a single structured action.
Only choose an action if it is clearly requested. If uncertain, return intent: "none".
Output ONLY a minified JSON object with keys exactly as in the schema. Do not include any extra text.

Schema:
{{
        "intent": "update_status|mark_done|add_task|start_pomodoro|stop_pomodoro|habit_add|habit_log|enable_reminders|disable_reminders|enable_nudges|disable_nudges|focus_music|none",
  "task_name": "string|null",
  "status": "Not started|In progress|Completed|null",
  "habit_name": "string|null",
  "add_task_text": "string|null"
}}

Rules:
- status must be one of: Not started, In progress, Completed (normalize user's phrasing to these).
- task_name should be taken from the following current task titles when possible; use the exact title if you can match it.
- If you can't confidently identify a specific task, set task_name to null and use intent:"none".

Current tasks (titles):
{task_titles_str}

User message:
{user_text}
"""

        resp = llm.generate_content(instruction)
        raw = resp.text.strip() if getattr(resp, "text", None) else ""

        # Extract JSON object from the response
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return False
        try:
            data = json.loads(m.group(0))
        except Exception:
            return False

        intent = (data.get("intent") or "none").lower()
        if intent == "none":
            return False

        def norm_status(s: str) -> str | None:
            if not s:
                return None
            key = s.strip().lower()
            map_ = {
                "not started": "Not started",
                "in progress": "In progress",
                "completed": "Completed",
            }
            return map_.get(key)

        # Execute actions
        if intent == "update_status":
            name = (data.get("task_name") or "").strip()
            status = norm_status(data.get("status"))
            if not name or not status:
                return False
            res = set_task_status_by_name(name, status)
            await update.message.reply_text(res.get("message", f"Updated '{name}' to {status}."))
            return True

        if intent == "mark_done":
            name = (data.get("task_name") or "").strip()
            if not name:
                return False
            res = set_task_status_by_name(name, "Completed")
            await update.message.reply_text(res.get("message", f"Marked '{name}' as Completed."))
            return True

        if intent == "add_task":
            add_text = (data.get("add_task_text") or "").strip()
            if not add_text:
                return False
            try:
                result = add_task_from_text(add_text)
                await update.message.reply_text(result.get("message", "Task added."), parse_mode="Markdown")
            except Exception as e:
                await update.message.reply_text(f"Error adding task: {e}")
            return True

        if intent == "start_pomodoro":
            # If a task name is included, pass it through context.args for the handler
            task_name = (data.get("task_name") or "").strip()
            context.args = [task_name] if task_name else []
            await start_pomodoro(update, context)
            return True

        if intent == "stop_pomodoro":
            await stop_pomodoro(update, context)
            return True

        if intent == "habit_add":
            habit_name = (data.get("habit_name") or "").strip()
            if not habit_name:
                return False
            msg = add_habit(habit_name)
            await update.message.reply_text(msg)
            return True

        if intent == "habit_log":
            habit_name = (data.get("habit_name") or "").strip()
            if not habit_name:
                return False
            msg = log_habit(habit_name)
            await update.message.reply_text(msg)
            return True

        if intent == "enable_reminders":
            enable_daily_reminders(context, update.effective_user.id, update.effective_chat.id, hour=8, minute=0)
            await update.message.reply_text("Daily reminders enabled. You'll get a message at 8:00 AM when you have tasks due soon.")
            return True

        if intent == "disable_reminders":
            removed = disable_daily_reminders(context, update.effective_user.id)
            await update.message.reply_text("Daily reminders disabled." if removed else "No active reminders to disable.")
            return True

        if intent == "enable_nudges":
            enable_daily_nudges(context, update.effective_user.id, update.effective_chat.id, hour=18, minute=0)
            await update.message.reply_text("Daily nudges enabled. You'll get a 6:00 PM check-in.")
            return True

        if intent == "disable_nudges":
            removed = disable_daily_nudges(context, update.effective_user.id)
            await update.message.reply_text("Daily nudges disabled." if removed else "No active nudges to disable.")
            return True

        if intent == "focus_music":
            await update.message.reply_text(f"Try this while you focus: {get_focus_link()}")
            return True

        return False

    except Exception:
        # On any error, silently fall back to normal flow
        return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles normal text messages"""
    text = update.message.text.strip()

    if text.lower() in ["hi", "hello", "hey", "yo", "sup", "start"]:
        await update.message.reply_text(
            "Hi, I'm Kairos — your productivity chatbot.\nHow can I help you today?"
        )
        return

    # First, try to interpret and execute a natural-language intent
    did_act = await try_natural_action(update, context, text)
    if did_act:
        return

    # Check if user is asking for tasks/workload directly
    task_keywords = ["task", "workload", "schedule", "what do i have", "what's due", "whats due", "what is due", "upcoming"]
    if any(keyword in text.lower() for keyword in task_keywords):
        # If asking specifically about tasks, show the formatted list directly
        try:
            raw_tasks = get_tasks_raw()
            
            # Determine date filter
            date_filter = None
            intro = "Here are your current tasks:\n\n"
            
            text_lower = text.lower()
            if "today" in text_lower or "due today" in text_lower:
                date_filter = "today"
                intro = "Here's what you have today:\n\n"
            elif "tomorrow" in text_lower or "due tomorrow" in text_lower:
                date_filter = "tomorrow"
                intro = "Here's what you have tomorrow:\n\n"
            elif "week" in text_lower or "next week" in text_lower or "this week" in text_lower:
                date_filter = "week"
                intro = "Here's your workload for the week:\n\n"
            elif "workload" in text_lower:
                date_filter = "week"
                intro = "Here's your workload:\n\n"
            elif "due" in text_lower or "upcoming" in text_lower:
                intro = "Here are your upcoming tasks:\n\n"
            
            formatted = format_tasks_list(raw_tasks, date_filter=date_filter)
            await update.message.reply_text(intro + formatted, parse_mode="Markdown")
            return
        except Exception as e:
            # If there's an error fetching tasks, fall through to Gemini
            pass

    await respond_with_gemini(update, text)


async def respond_with_gemini(update: Update, text: str):
    """Send message + Notion context to Gemini"""
    try:
        notion_context = format_tasks_list(get_tasks_raw())

        prompt = f"""
You are Kairos — a student-friendly productivity assistant helping university students manage workload, tasks, and priorities.
Respond factually, concisely, and in a friendly, encouraging tone. Strictly no emojis.
Never invent meetings, classes, or deadlines. If information is missing, say that it's not available.
Provide clear, practical suggestions. Be ready to answer short Q&A or FAQs about productivity when asked.

Task data context (copy structure without emojis if you need to quote):
{notion_context}

User message:
{text}
"""
        response = llm.generate_content(prompt)
        await update.message.reply_text(response.text.strip())

    except Exception as e:
        await update.message.reply_text(f"Gemini API error: {e}")


# --- Runner ---
if __name__ == "__main__":
    print("🤖 Kairos is running...")

    missing_env = validate_env()
    if missing_env:
        print("Warning: Missing environment variables:", ", ".join(missing_env))

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Basic commands
    app.add_handler(CommandHandler("start", start))
    
    # Task commands
    app.add_handler(CommandHandler("tasks", tasks))
    app.add_handler(CommandHandler("add", add_task))
    
    # Pomodoro commands
    app.add_handler(CommandHandler("pomodoro", start_pomodoro))
    app.add_handler(CommandHandler("pomodoro_start", start_pomodoro))
    app.add_handler(CommandHandler("pomodoro_stop", stop_pomodoro))
    app.add_handler(CommandHandler("pomodoro_status", pomodoro_status))
    app.add_handler(CommandHandler("pomodoro_break", start_break))
    
    # Email reminder commands
    app.add_handler(CommandHandler("reminder", send_reminder))
    app.add_handler(CommandHandler("reminder_enable", enable_reminders))
    app.add_handler(CommandHandler("reminder_disable", disable_reminders))

    # Nudges commands
    async def nudges_enable_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        enable_daily_nudges(context, update.effective_user.id, update.effective_chat.id, hour=18, minute=0)
        await update.message.reply_text("Daily nudges enabled. You'll get a 6:00 PM check-in.")

    async def nudges_disable_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        removed = disable_daily_nudges(context, update.effective_user.id)
        if removed:
            await update.message.reply_text("Daily nudges disabled.")
        else:
            await update.message.reply_text("No active nudges to disable.")

    app.add_handler(CommandHandler("nudges_enable", nudges_enable_cmd))
    app.add_handler(CommandHandler("nudges_disable", nudges_disable_cmd))

    # Task status update commands
    async def done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        name = " ".join(context.args).strip()
        if not name:
            # Offer a helpful example from current tasks
            try:
                tasks = get_tasks_raw()
                example = None
                for row in tasks:
                    props = row.get("properties", {})
                    status = props.get("Status", {}).get("status", {}).get("name", "Unknown")
                    if status != "Completed":
                        title_arr = props.get("Task", {}).get("title") or []
                        example = title_arr[0].get("plain_text") if title_arr else None
                        if example:
                            break
                if example:
                    await update.message.reply_text(
                        f"Usage: /done <task name>\nExample: /done {example}"
                    )
                else:
                    await update.message.reply_text("Usage: /done <task name>")
            except Exception:
                await update.message.reply_text("Usage: /done <task name>")
            return
        res = set_task_status_by_name(name, "Completed")
        await update.message.reply_text(res.get("message", "Done."))

    async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Update a task's status.
        Expected format: /status <task name>, <Not started|In Progress|Completed>
        Also supports legacy format without comma: /status <task name> <Not started|In progress|Completed>
        """
        text_after_command = update.message.text.partition(" ")[2].strip()
        if not text_after_command:
            await update.message.reply_text(
                "Usage: /status <task name>, <Not started|In Progress|Completed>"
            )
            return

        name = None
        status_raw = None

        # Preferred: comma-separated format
        if "," in text_after_command:
            parts = [p.strip() for p in text_after_command.split(",", 1)]
            if len(parts) == 2:
                name, status_raw = parts[0], parts[1]

        # Fallback: legacy format (status as the trailing phrase)
        if not name or not status_raw:
            full = " ".join(context.args).strip()
            for opt in ["Not started", "In progress", "In Progress", "Completed"]:
                if full.lower().endswith(opt.lower()):
                    status_raw = opt
                    name = full[: -len(opt)].strip()
                    break

        if not name or not status_raw:
            await update.message.reply_text(
                "Usage: /status <task name>, <Not started|In Progress|Completed>"
            )
            return

        # Normalize status to Notion's expected casing
        normalized = status_raw.strip().strip("<>")
        status_map = {
            "not started": "Not started",
            "in progress": "In progress",
            "completed": "Completed",
        }
        status_key = normalized.lower()
        if status_key not in status_map:
            await update.message.reply_text(
                "Status must be one of: Not started, In Progress, Completed"
            )
            return

        notion_status = status_map[status_key]
        res = set_task_status_by_name(name, notion_status)
        await update.message.reply_text(res.get("message", "Updated."))

    app.add_handler(CommandHandler("done", done_cmd))
    app.add_handler(CommandHandler("status", status_cmd))

    # Habits
    habits_init(); analytics_init()

    async def habit_add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        name = " ".join(context.args).strip()
        msg = add_habit(name)
        await update.message.reply_text(msg)

    async def habit_log_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        name = " ".join(context.args).strip()
        msg = log_habit(name)
        await update.message.reply_text(msg)

    async def habit_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(list_habits())

    async def habit_streak_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        name = " ".join(context.args).strip()
        if not name:
            await update.message.reply_text("Usage: /habit_streak <name>")
            return
        await update.message.reply_text(current_streak(name))

    app.add_handler(CommandHandler("habit_add", habit_add_cmd))
    app.add_handler(CommandHandler("habit_log", habit_log_cmd))
    app.add_handler(CommandHandler("habit_list", habit_list_cmd))
    app.add_handler(CommandHandler("habit_streak", habit_streak_cmd))

    # Recommendations and analytics
    async def recommend_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        rows = recommend(get_tasks_raw())
        await update.message.reply_text(format_recommendations(rows))

    async def analytics_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(summary_last_7_days())

    app.add_handler(CommandHandler("recommend", recommend_cmd))
    app.add_handler(CommandHandler("analytics", analytics_cmd))

    # Focus music
    async def focus_on_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(f"Try this while you focus: {get_focus_link()}")
    # Support multiple aliases: /focus_on, /focuson, /focus
    app.add_handler(CommandHandler(["focus_on", "focuson", "focus"], focus_on_cmd))

    # Import schedule
    async def import_schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Case 1: Pasted text after command
        text = " ".join(context.args).strip()
        created = 0
        if text:
            from features.add import create_notion_task
            tasks = parse_text_to_tasks(text)
            for t in tasks:
                res = create_notion_task(t["name"], t["priority"], t["due_date"], t["project"]) 
                if res.get("success"):
                    created += 1
            await update.message.reply_text(f"Imported {created} task(s) from text.")
            return
        # Case 2: Replying to a PDF
        if update.message.reply_to_message and update.message.reply_to_message.document:
            doc = update.message.reply_to_message.document
            if doc.file_name and doc.file_name.lower().endswith(".pdf"):
                file = await context.bot.get_file(doc.file_id)
                data = await file.download_as_bytearray()
                try:
                    tasks = tasks_from_pdf_bytes(bytes(data))
                except Exception as e:
                    await update.message.reply_text(f"Could not parse PDF: {e}")
                    return
                from features.add import create_notion_task
                for t in tasks:
                    res = create_notion_task(t["name"], t["priority"], t["due_date"], t["project"]) 
                    if res.get("success"):
                        created += 1
                await update.message.reply_text(f"Imported {created} task(s) from PDF.")
                return
        await update.message.reply_text("Usage: /import_schedule <pasted text> or reply to a PDF with /import_schedule")

    app.add_handler(CommandHandler("import_schedule", import_schedule_cmd))
    
    # Message handler (must be last)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()
