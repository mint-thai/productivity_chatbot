import os
import json
import re
from datetime import datetime, time as dt_time
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import google.generativeai as genai

from features.notion_utils import get_tasks_raw, set_task_status_by_name, delete_task_by_name, update_due_date_by_name
from features.view import format_tasks_list
from features.add import add_task_from_text
from features.pomodoro import start_pomodoro, start_break, pomodoro_status, stop_pomodoro
from features.habits import init_db as habits_init, add_habit, log_habit, list_habits, current_streak
from features.analytics import init_db as analytics_init, summary_last_7_days
from features.recommend import recommend, format_recommendations
from features.music import get_music_menu, get_song_by_choice, get_random_song
from features.schedule_parser import tasks_from_image_bytes
from features.translate import (set_language, get_language, translate_text, get_language_menu, 
                                 SUPPORTED_LANGUAGES, enable_tts, disable_tts, is_tts_enabled, text_to_speech)
from app.config import validate_env

# --- Load environment variables ---
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Configure Gemini ---
genai.configure(api_key=GOOGLE_API_KEY)
MODEL = "gemini-2.5-flash"
llm = genai.GenerativeModel(MODEL)

# --- TTS Helper Function ---
async def send_with_tts(update: Update, text: str, **kwargs):
    """Send message and optionally send TTS audio if enabled (translates to user's language)"""
    user_id = update.effective_user.id
    
    # Send text message
    msg = await update.message.reply_text(text, **kwargs)
    
    # If TTS enabled, send audio too
    if is_tts_enabled(user_id):
        try:
            lang = get_language(user_id)
            # Clean text for TTS (remove markdown, emojis, limit length)
            clean_text = text.replace("**", "").replace("*", "").replace("_", "").replace("`", "")
            clean_text = clean_text.replace("✨", "").strip()
            if len(clean_text) > 500:
                clean_text = clean_text[:500] + "..."
            
            # Translate if not English
            if lang != "en":
                from features.translate import translate_text
                clean_text = translate_text(clean_text, lang)
            
            audio_buffer = text_to_speech(clean_text, lang)
            await update.message.reply_voice(voice=audio_buffer)
            print(f"✓ TTS sent for user {user_id} in {lang}")
        except Exception as e:
            print(f"TTS error: {e}")
    
    return msg

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi, I'm Kairos, a student-friendly productivity assistant.\n"
        "I help you manage tasks, focus with Pomodoro, track habits, and stay on top of deadlines.\n\n"
        "Task Management:\n"
        "• /tasks — View your Notion tasks\n"
        "• /add — Add new task\n"
        "• /done <task> — Mark task completed\n"
        "• /delete <task> — Delete a task\n"
        "• /status <task>, <status> — Update status\n\n"
        "Reminder:\n"
        "• /reminder — Send email reminder now\n\n"
        "Recommendation:\n"
        "• /recommend — Get your next best task\n\n"
        "Pomodoro:\n"
        "• /pomodoro [task] — Start 25-min focus session\n"
        "• /pomodoro_break — Start 5-min break\n"
        "• /pomodoro_status — Check timer\n"
        "• /pomodoro_stop — Stop session\n\n"
        "Focus Music:\n"
        "• /music — Browse focus music\n\n"
        "Habit Tracker:\n"
        "• /habit_add <name>\n"
        "• /habit_log <name>\n"
        "• /habit_list\n"
        "• /habit_streak <name>\n\n"
        "Motivation:\n"
        "• /motivate — Get a motivational quote\n\n"
        "Q&A:\n"
        "• Ask productivity questions (e.g., \"I need tips on time management\")\n\n"
        "Language & Audio:\n"
        "• /language — View languages & audio settings\n"
        "• /tts_on — Enable audio 🔊\n"
        "• /tts_off — Disable audio 🔇\n\n"
        "Analytics:\n"
        "• /analytics — Weekly summary"
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
            "📝 To add a task, use this format:\n"
            "**/add TaskName [priority] due:DATE project:ProjectName**\n\n"
            "**Examples:**\n"
            "• /add Study for exam\n"
            "• /add Finish homework [high] due:tomorrow\n"
            "• /add Review notes [medium] due:2025-12-15 project:Math\n"
            "\n**Priority must be in brackets:** [high], [medium], or [low]\n"
            "• /add Write report [medium] due:2025-11-25 project:ADSC 3710\n\n"
            "**Options:**\n"
            "• Priority: [high], [medium], [low] (default: medium)\n"
            "• Due date: due:today, due:tomorrow, due:nextweek, or due:YYYY-MM-DD\n"
            "• Project: project:ProjectName\n\n"
            "You can also say: \"add Finish essay [high] due:tomorrow project:English\"",
            parse_mode="Markdown"
        )
        return
    
    await update.message.reply_text("Creating your task...")
    
    try:
        result = add_task_from_text(task_text)
        await update.message.reply_text(result["message"], parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error adding task: {e}")


async def send_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send email reminder immediately"""
    # Use SendGrid for email reminders
    from features.reminder import check_and_send_reminders, get_upcoming_tasks
    
    # Get tasks that will be included in email
    upcoming = get_upcoming_tasks(hours_ahead=24)
    
    if upcoming:
        # Show preview in chat
        preview = "📬 Email Preview:\n\n"
        priority_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🔵"}
        for task in upcoming[:5]:  # Show max 5
            emoji = priority_emoji.get(task['priority'], '🔵')
            due_str = task['due_date'].strftime('%b %d')
            preview += f"{emoji} {task['name']} (due {due_str})\n"
        if len(upcoming) > 5:
            preview += f"\n...and {len(upcoming)-5} more\n"
        preview += f"\n📧 Sending to email..."
        await update.message.reply_text(preview)
    else:
        await update.message.reply_text("📧 Sending email reminder...")
    
    try:

        result = check_and_send_reminders(hours_ahead=24)
        if result["success"]:
            await update.message.reply_text(
                f"✅ {result['message']}\n\n"
                f"Check your email inbox!"
            )
        else:
            error_msg = f"❌ {result['message']}\n\n"
            
            error_msg += (
                "Configure SendGrid in .env:\n"
                "- SENDGRID_API_KEY\n"
                "- SENDER_EMAIL (verified in SendGrid)\n"
                "- RECIPIENT_EMAIL"
            )
            
            await update.message.reply_text(error_msg)
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {e}\n\n"
            "If you see 'Operation timed out', your network blocks email.\n"
            "Run: pip install sendgrid and see EMAIL_TROUBLESHOOTING.md"
        )





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
      - send_reminder: {}
      - motivate: {}

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
Only choose an action if it is clearly requested AND has sufficient details to execute. If uncertain or missing key information, return intent: "none".
Output ONLY a minified JSON object with keys exactly as in the schema. Do not include any extra text.

Schema:
{{
  "intent": "update_status|mark_done|add_task|start_pomodoro|stop_pomodoro|habit_add|habit_log|habit_list|habit_streak|focus_music|delete_task|update_due_date|send_reminder|motivate|recommend|analytics|import_schedule|none",
  "task_name": "string|null",
  "status": "Not started|In progress|Completed|null",
  "habit_name": "string|null",
  "add_task_text": "string|null",
  "due_date": "string|null"
}}

Rules:
- status must be one of: Not started, In progress, Completed (normalize user's phrasing to these).
- task_name should be taken from the following current task titles when possible; use the exact title if you can match it.
- If you can't confidently identify a specific task, set task_name to null and use intent:"none".
- For add_task: ONLY set intent to "add_task" if the user provides SPECIFIC task details with at least a task name. The user must describe WHAT the task is. Vague requests like "add a task", "add a new task", "can you add a task for me", "create a task" WITHOUT any task description should return intent:"none". Examples:
  * "Create report for Math due Nov 20" → "report for Math due:2025-11-20" ✓
  * "Write essay [high] for English class due tomorrow" → "essay [high] due:tomorrow project:English" ✓
  * "Chatbot Report for ADSC 3710 project and due on November 21, 2025" → "Chatbot Report due:2025-11-21 project:ADSC 3710" ✓
  * "add a task" → intent:"none" ✗
  * "can you add a new task for me?" → intent:"none" ✗
  * "create a task" → intent:"none" ✗
- For delete_task: only set intent if a specific task is named. Vague requests like "delete a task" should return intent:"none".
- For start_pomodoro: Use when user wants to start a Pomodoro/focus session. Examples: "start pomodoro", "begin focus session", "start a pomodoro for Math homework", "pomodoro session for essay", "start 25 min timer". Extract task_name if mentioned.
- For stop_pomodoro: Use when user wants to stop/end the current Pomodoro session. Examples: "stop pomodoro", "end session", "cancel timer", "stop the focus session".
- For send_reminder: ONLY when user explicitly says "send me a reminder now" or "send reminder now" or very similar explicit phrasing. DO NOT trigger on general questions like "what's due" or "check my tasks".
- For motivate: Use when user asks for motivation, encouragement, inspiration, quotes, or boost. Examples: "motivate me", "I need inspiration", "give me a quote", "encourage me", "drop a micro motivation", "give me a wake-up punchline", "a little boost of the day", "quote of the day", "I'm feeling down".
- For recommend: Use when user asks what to work on next, what to prioritize, what's most important, or wants task recommendations. Examples: "what should I work on?", "what's my priority?", "what should I do next?", "recommend a task", "what's most urgent?", "help me prioritize".
- For habit_add: Use when user wants to create/add/start tracking a new habit. Examples: "add habit yoga", "start tracking calling family", "create habit sleep before 11pm", "track morning workout". Extract the habit name.
- For habit_log: Use when user says they completed/did a habit today. Examples: "I did yoga", "completed yoga", "log yoga", "mark yoga done", "I called family today", "finished morning workout". Extract the habit name.
- For habit_list: Use when user asks to see all habits, list habits, or show habits. Examples: "show me a list of habits", "what are my habits?", "list all habits", "show habits", "what habits am I tracking?".
- For habit_streak: Use when user asks about their streak for a specific habit. Examples: "what's my streak with yoga?", "how many days of yoga?", "yoga streak", "streak for calling family", "how long have I been doing yoga?". Extract the habit name.
- For analytics: Use when user asks about their productivity stats, focus sessions, weekly summary, or progress. Examples: "show me my analytics", "how productive was I this week?", "how many pomodoros did I do?", "show my stats", "weekly summary", "how focused was I?", "my productivity report".
- For import_schedule: Use when user wants to extract/parse/import/scan tasks from a schedule screenshot OR when they say "parse this" or "import this" with a photo. Examples: "import my schedule", "parse this schedule", "parse this", "extract tasks from this", "import tasks from screenshot", "scan my schedule", "parse this for me", "import this schedule". ALWAYS set intent to "import_schedule" if user mentions parsing/importing/extracting a schedule/calendar/screenshot.
- Vague requests without specifics should return intent:"none" so the conversational assistant can ask for details.

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
        print(f"DEBUG: Detected intent: {intent}")
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

        if intent == "delete_task":
            name = (data.get("task_name") or "").strip()
            if not name:
                return False
            res = delete_task_by_name(name)
            await update.message.reply_text(res.get("message", f"Deleted '{name}'."))
            return True
        
        if intent == "update_due_date":
            from features.add import parse_due_date
            name = (data.get("task_name") or "").strip()
            due_date_str = (data.get("due_date") or "").strip()
            if not name or not due_date_str:
                return False
            # Parse the due date using the same logic as /add
            due_date = parse_due_date(due_date_str)
            if not due_date:
                await update.message.reply_text(f"Invalid due date format: {due_date_str}")
                return True
            res = update_due_date_by_name(name, due_date)
            await update.message.reply_text(res.get("message", f"Due date updated for '{name}'."))
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

        if intent == "habit_list":
            await update.message.reply_text(list_habits())
            return True

        if intent == "habit_streak":
            habit_name = (data.get("habit_name") or "").strip()
            if not habit_name:
                return False
            msg = current_streak(habit_name)
            await update.message.reply_text(msg)
            return True

        if intent == "send_reminder":
            # Send reminder now
            await send_reminder(update, context)
            return True

        if intent == "motivate":
            # Send motivational quote with TTS
            from features.motivate import get_random_quote
            quote = get_random_quote()
            await send_with_tts(update, f"✨ {quote}")
            return True

        if intent == "recommend":
            # Show task recommendations
            rows = recommend(get_tasks_raw())
            await send_with_tts(update, format_recommendations(rows))
            return True

        if intent == "analytics":
            # Show productivity analytics
            await send_with_tts(update, summary_last_7_days())
            return True

        if intent == "focus_music":
            from features.music import get_music_menu
            await update.message.reply_text(get_music_menu(), parse_mode="Markdown")
            return True

        if intent == "import_schedule":
            # Check if message has a photo
            print(f"DEBUG: import_schedule intent detected. Has photo: {bool(update.message.photo)}")
            if not update.message.photo:
                await update.message.reply_text("📸 Please attach a screenshot of your schedule to import tasks.")
                return True
            
            from features.add import create_notion_task
            from features.schedule_parser import tasks_from_image_bytes
            
            await update.message.reply_text("🔍 Analyzing your schedule...")
            print(f"DEBUG: Processing photo, count: {len(update.message.photo)}")
            
            # Get highest resolution photo
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            data = await file.download_as_bytearray()
            
            try:
                tasks = tasks_from_image_bytes(bytes(data), "image/jpeg")
                if not tasks:
                    await update.message.reply_text("❌ No tasks found. Make sure dates are visible!")
                    return True
                
                created = 0
                for t in tasks:
                    res = create_notion_task(t["name"], t["priority"], t.get("due_date"), t.get("project", "")) 
                    if res.get("success"):
                        created += 1
                
                await update.message.reply_text(f"✅ Imported {created} tasks from your schedule!")
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {e}")
            return True

        return False

    except Exception:
        # On any error, silently fall back to normal flow
        return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles normal text messages and photo captions"""
    # Get text from either message text or photo caption
    text = (update.message.text or update.message.caption or "").strip()
    
    if not text:
        return  # No text to process

    # Check if user is replying with a music choice (1-5)
    if text in ["1", "2", "3", "4", "5"]:
        from features.music import get_song_by_choice
        song = get_song_by_choice(text)
        if song:
            await update.message.reply_text(
                f"🎵 Now playing: **{song['name']}**\n\n{song['url']}",
                parse_mode="Markdown"
            )
            return

    # Enhanced greeting detection - catch greetings early
    greetings = ["hi", "hello", "hey", "yo", "sup", "start", "hi!", "hello!", "hey!", "hi there", "hello there"]
    if text.lower() in greetings or text.lower().startswith(tuple(greetings)):
        await update.message.reply_text(
            "Hi, I'm Kairos — your productivity chatbot.\nHow can I help you today?"
        )
        return

    # Check if user is asking how to add a task (without task details)
    text_lower = text.lower()
    vague_add_phrases = ["add a new task", "add task", "create a task", "create task", "new task"]
    if any(phrase in text_lower for phrase in vague_add_phrases) and len(text_lower.split()) <= 8:
        await update.message.reply_text(
            "To add a task, use this format:\n\n"
            "/add TaskName [priority] due:DATE project:ProjectName\n\n"
            "Examples:\n"
            "• /add Study for exam [high] due:tomorrow\n"
            "• /add Essay [medium] project:English due:next week\n"
            "• /add Coffee Chat [low] due:11/21/2025 project:Career\n\n"
            "**Priority must be in brackets:** [high], [medium], or [low]\n\n"
            "Or tell me naturally:\n"
            "\"Add Math homework [high] due Nov 25\"",
            parse_mode="Markdown"
        )
        return

    # First, try to interpret and execute a natural-language intent
    did_act = await try_natural_action(update, context, text)
    if did_act:
        return

    # Check if user is asking for tasks/workload directly (not action requests)
    text_lower = text.lower()
    
    # Exclude action keywords that should be handled by natural language processing
    action_keywords = ["add", "create", "delete", "remove", "mark", "complete", "update", "change", "parse", "import", "extract", "scan"]
    is_action_request = any(action in text_lower for action in action_keywords)
    
    # Only show task list if it's a viewing request, not an action request
    view_keywords = ["show", "list", "view", "what do i have", "what's due", "whats due", "what is due", "my tasks", "upcoming"]
    is_view_request = any(keyword in text_lower for keyword in view_keywords)
    
    # Special handling: if just asking about "task", "workload", or "schedule" without action words
    passive_keywords = ["workload", "schedule"]
    is_passive_query = any(keyword in text_lower for keyword in passive_keywords) and not is_action_request
    
    if (is_view_request or is_passive_query) and not is_action_request:
        # If asking specifically about tasks, show the formatted list directly
        try:
            raw_tasks = get_tasks_raw()
            
            # Determine if user wants to see all tasks
            show_all = "all" in text_lower and ("task" in text_lower or "my" in text_lower)
            
            # Determine date filter
            date_filter = None
            intro = "Here are your current tasks:\n\n"
            
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
            
            formatted = format_tasks_list(raw_tasks, date_filter=date_filter, show_all=show_all)
            await update.message.reply_text(intro + formatted, parse_mode="Markdown")
            return
        except Exception as e:
            # If there's an error fetching tasks, fall through to Gemini
            pass

    # Only trigger Q&A if message is substantial (indicates a real question)
    # Skip very short messages or unclear inputs
    if len(text.split()) < 3:
        await update.message.reply_text(
            "I'm not sure what you mean. Try:\n"
            "• /tasks — See your tasks\n"
            "• /add [task] — Add a task\n"
            "• /motivate — Get motivation\n"
            "• Or ask me a productivity question!"
        )
        return
    
    # Trigger Q&A for substantial questions
    from features.qa import is_productivity_question, get_qa_response, get_brief_task_summary
    
    # Check if it's actually a productivity question
    if not is_productivity_question(text):
        await update.message.reply_text(
            "I'm not sure what you're asking. Try:\n"
            "• Ask a productivity question (e.g., 'How do I manage my time?')\n"
            "• /tasks — See your tasks\n"
            "• /motivate — Get motivation"
        )
        return
    
    # Get brief task summary (not full list to avoid token limit)
    try:
        raw_tasks = get_tasks_raw()
        task_summary = get_brief_task_summary(raw_tasks, max_tasks=5)
    except:
        task_summary = None
    
    # Get Q&A response
    response = get_qa_response(text, task_summary)
    await update.message.reply_text(response)


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
    
    # Email reminder command
    app.add_handler(CommandHandler("reminder", send_reminder))

    # Motivational command
    async def motivate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a motivational quote"""
        from features.motivate import get_random_quote
        quote = get_random_quote()
        await send_with_tts(update, f"✨ {quote}")
    
    app.add_handler(CommandHandler("motivate", motivate_cmd))

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

    async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete a task by name."""
        name = " ".join(context.args).strip()
        if not name:
            await update.message.reply_text("Usage: /delete <task name>")
            return
        res = delete_task_by_name(name)
        await update.message.reply_text(res.get("message", "Task deleted."))

    app.add_handler(CommandHandler("done", done_cmd))
    app.add_handler(CommandHandler("delete", delete_cmd))
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
    async def music_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from features.music import get_music_menu, get_song_by_choice, get_random_song
        
        # If user provided a choice (1-5), play that song
        if context.args:
            choice = context.args[0]
            song = get_song_by_choice(choice)
            if song:
                await update.message.reply_text(
                    f"🎵 Now playing: **{song['name']}**\n\n{song['url']}",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ Invalid choice. Pick 1-5!")
        else:
            # Show menu
            await update.message.reply_text(get_music_menu(), parse_mode="Markdown")
    
    # Support multiple aliases: /music, /tunes, /play
    app.add_handler(CommandHandler(["music", "tunes", "play"], music_cmd))

    # Language settings
    async def language_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # If no args, show menu
        if not context.args:
            await update.message.reply_text(get_language_menu(), parse_mode="Markdown")
            return
        
        # Set language
        lang_code = context.args[0].lower()
        result = set_language(user_id, lang_code)
        await update.message.reply_text(result["message"])
    
    app.add_handler(CommandHandler("language", language_cmd))

    # TTS commands
    async def tts_on_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        result = enable_tts(user_id)
        await update.message.reply_text(result["message"])
    
    async def tts_off_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        result = disable_tts(user_id)
        await update.message.reply_text(result["message"])
    
    app.add_handler(CommandHandler("tts_on", tts_on_cmd))
    app.add_handler(CommandHandler("tts_off", tts_off_cmd))

    # Import schedule
    async def import_schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from features.add import create_notion_task
        from features.schedule_parser import tasks_from_image_bytes
        
        # Must reply to a photo/screenshot
        if not update.message.reply_to_message or not update.message.reply_to_message.photo:
            await update.message.reply_text(
                "📸 Send a screenshot of your schedule, then reply with /import_schedule\n\n"
                "Works best with:\n"
                "• Tables with dates (Canvas, syllabi)\n"
                "• Calendar views (Google Calendar)\n"
                "• Course outline screenshots"
            )
            return
        
        await update.message.reply_text("🔍 Analyzing your schedule...")
        
        # Get highest resolution photo
        photo = update.message.reply_to_message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        data = await file.download_as_bytearray()
        
        try:
            tasks = tasks_from_image_bytes(bytes(data), "image/jpeg")
            if not tasks:
                await update.message.reply_text("❌ No tasks found. Make sure dates are visible!")
                return
            
            created = 0
            for t in tasks:
                res = create_notion_task(t["name"], t["priority"], t.get("due_date"), t.get("project", "")) 
                if res.get("success"):
                    created += 1
            
            await update.message.reply_text(f"✅ Imported {created} tasks from your schedule!")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    app.add_handler(CommandHandler("import_schedule", import_schedule_cmd))
    
    # Message handler (must be last) - handle both text messages and photo captions
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
    
    app.run_polling()
