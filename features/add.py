"""
Module for adding new tasks to the Notion database via the Telegram bot.
Supports natural language parsing and structured task creation.
"""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# --- Environment setup ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# --- Parser: interpret freeform text ---
def parse_task_input(text: str) -> dict:
    """
    Parse user input to extract task details.

    Supported examples:
        "Finish homework"
        "Finish homework [high]"
        "Finish homework due:tomorrow"
        "Finish homework [high] due:2025-11-12 project:Math"

    Returns dict with: name, priority, due_date, project
    """
    task_data = {
        "name": "",
        "priority": "Medium",  # Default
        "due_date": None,
        "project": ""
    }

    original = text.strip()

    # --- Extract priority ---
    priority_map = {"[high]": "High", "[medium]": "Medium", "[low]": "Low"}
    for key, val in priority_map.items():
        if key in original.lower():
            task_data["priority"] = val
            # Remove priority using case-insensitive replacement
            import re
            original = re.sub(re.escape(key), "", original, flags=re.IGNORECASE).strip()
            break

    # --- Extract project FIRST (to avoid conflict with due date) ---
    if "project:" in original.lower():
        parts = original.lower().split("project:")
        before = parts[0]
        after = original[len(before) + 8:]  # +8 for "project:"
        original = before.strip()
        task_data["project"] = after.strip()

    # --- Extract due date ---
    if "due:" in original.lower():
        parts = original.lower().split("due:")
        before = parts[0]
        after = original[len(before) + 4:]  # +4 for "due:"
        original = before.strip()
        due_str = after.strip().split()[0]

        due_str = due_str.lower()
        today = datetime.now()

        if due_str == "today":
            task_data["due_date"] = today.strftime("%Y-%m-%d")
        elif due_str == "tomorrow":
            task_data["due_date"] = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        elif due_str in ["nextweek", "next-week"]:
            task_data["due_date"] = (today + timedelta(weeks=1)).strftime("%Y-%m-%d")
        else:
            # Try standard format first
            try:
                parsed = datetime.strptime(due_str, "%Y-%m-%d")
                task_data["due_date"] = parsed.strftime("%Y-%m-%d")
            except ValueError:
                # Try alternative formats
                for fmt in ["%m-%d-%Y", "%m/%d/%Y", "%Y/%m/%d"]:
                    try:
                        parsed = datetime.strptime(due_str, fmt)
                        task_data["due_date"] = parsed.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue

    # Remaining text = task name
    task_data["name"] = original.strip()

    return task_data


# --- Formatter for preview ---
def format_task_summary(data: dict) -> str:
    """Readable summary before adding a task."""
    parts = [f"New task: *{data['name']}*"]
    if data.get("due_date"):
        parts.append(f"Due: {data['due_date']}")
    if data.get("priority"):
        parts.append(f"Priority: {data['priority']}")
    if data.get("project"):
        parts.append(f"Project: {data['project']}")
    return "\n".join(parts)


# --- Create task in Notion ---
def create_notion_task(task_name: str, priority: str = "Medium", due_date: str = None, project: str = "") -> dict:
    """
    Create a new page (task) in the Notion database.
    """
    if not task_name:
        return {"success": False, "message": "Task name cannot be empty."}

    props = {
        "Task": {"title": [{"text": {"content": task_name}}]},
        "Status": {"status": {"name": "Not started"}},
        "Priority": {"select": {"name": priority}},
    }

    if due_date:
        props["Due date"] = {"date": {"start": due_date}}

    if project:
        props["Project"] = {"rich_text": [{"text": {"content": project}}]}

    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": props,
    }

    try:
        res = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload)
        if res.status_code == 200:
            msg = f"Task created: *{task_name}*\nPriority: {priority}\nStatus: Not started"
            if due_date:
                msg += f"\nDue: {due_date}"
            if project:
                msg += f"\nProject: {project}"
            return {"success": True, "message": msg}
        else:
            return {
                "success": False,
                "message": f"Failed to create task: {res.status_code}\n{res.text[:150]}"
            }

    except Exception as e:
        return {"success": False, "message": f"Error creating task: {e}"}


# --- Main callable from bot.py ---
def add_task_from_text(text: str) -> dict:
    """
    Parse the task text and create it in Notion.
    """
    task_data = parse_task_input(text)

    if not task_data["name"]:
        return {
            "success": False,
            "message": (
                "Please provide a task name.\n\n"
                "Examples:\n"
                "• /add Study for exam\n"
                "• /add Finish homework [high] due:tomorrow\n"
                "• /add Review notes due:2025-01-15 project:Math"
            ),
        }

    return create_notion_task(
        task_name=task_data["name"],
        priority=task_data["priority"],
        due_date=task_data["due_date"],
        project=task_data["project"],
    )


# --- Testing (run standalone) ---
if __name__ == "__main__":
    examples = [
        "Finish assignment",
        "Study for exam [high] due:tomorrow",
        "Review notes due:2025-11-15 project:Math",
        "Complete project [low] due:nextweek project:CS",
    ]
    for example in examples:
        print(f"\nExample: {example}")
        print(parse_task_input(example))
