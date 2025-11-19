import os, requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def get_tasks_raw(limit: int = 50):
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    body = {
        "page_size": limit,
        "sorts": [{"property": "Due date", "direction": "ascending"}],  # <-- exact property
    }
    r = requests.post(url, headers=HEADERS, json=body)
    if r.status_code != 200:
        print("❌ Notion API Error:", r.text)
        return []
    return r.json().get("results", [])

# if you use list_tasks() wrapper:
from features.view import format_tasks_list
def list_tasks():
    return format_tasks_list(get_tasks_raw()) or "📭 No tasks available."


# --- Helpers for updating tasks ---
def _get_page_id(task_row: dict) -> str | None:
    """Extract Notion page id from a task row."""
    return task_row.get("id")


def find_task_by_name(name: str, limit: int = 50) -> dict | None:
    """
    Find a task by its title (exact match, case-insensitive) in the Notion database.
    Returns the first match or None.
    """
    results = get_tasks_raw(limit=limit)
    target = name.strip().lower()
    for row in results:
        props = row.get("properties", {})
        title_arr = props.get("Task", {}).get("title") or []
        title = title_arr[0].get("plain_text") if title_arr else None
        if title and title.strip().lower() == target:
            return row
    return None


def update_task_status(page_id: str, status_name: str) -> dict:
    """
    Update the Status property of a Notion task page.
    status_name should match one of the database's status options (e.g.,
    "Not started", "In progress", "Completed").
    """
    if not page_id:
        return {"success": False, "message": "Missing page_id"}

    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "Status": {"status": {"name": status_name}}
        }
    }
    r = requests.patch(url, headers=HEADERS, json=payload)
    if r.status_code == 200:
        return {"success": True, "message": f"Status updated to '{status_name}'."}
    return {
        "success": False,
        "message": f"Failed to update status: {r.status_code} {r.text[:150]}"
    }


def set_task_status_by_name(task_name: str, status_name: str) -> dict:
    """Convenience helper to find a task by name and update its status."""
    row = find_task_by_name(task_name)
    if not row:
        return {"success": False, "message": f"Task not found: {task_name}"}
    page_id = _get_page_id(row)
    return update_task_status(page_id, status_name)


def archive_task(page_id: str) -> dict:
    """
    Archive (soft delete) a Notion task page by setting archived=true.
    """
    if not page_id:
        return {"success": False, "message": "Missing page_id"}

    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"archived": True}
    r = requests.patch(url, headers=HEADERS, json=payload)
    if r.status_code == 200:
        return {"success": True, "message": "Task archived successfully."}
    return {
        "success": False,
        "message": f"Failed to archive task: {r.status_code} {r.text[:150]}"
    }


def delete_task_by_name(task_name: str) -> dict:
    """Convenience helper to find a task by name and archive it."""
    row = find_task_by_name(task_name)
    if not row:
        return {"success": False, "message": f"Task not found: {task_name}"}
    page_id = _get_page_id(row)
    return archive_task(page_id)


def update_due_date(page_id: str, due_date: str) -> dict:
    """Update the Due date property of a Notion task page."""
    if not page_id:
        return {"success": False, "message": "Missing page_id"}
    
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "Due date": {"date": {"start": due_date}}
        }
    }
    r = requests.patch(url, headers=HEADERS, json=payload)
    if r.status_code == 200:
        return {"success": True, "message": f"Due date updated to {due_date}."}
    return {
        "success": False,
        "message": f"Failed to update due date: {r.status_code} {r.text[:150]}"
    }


def update_due_date_by_name(task_name: str, due_date: str) -> dict:
    """Convenience helper to find a task by name and update its due date."""
    row = find_task_by_name(task_name)
    if not row:
        return {"success": False, "message": f"Task not found: {task_name}"}
    page_id = _get_page_id(row)
    return update_due_date(page_id, due_date)


def update_due_date(page_id: str, due_date: str) -> dict:
    """Update the Due date property of a Notion task page."""
    if not page_id:
        return {"success": False, "message": "Missing page_id"}
    
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "Due date": {"date": {"start": due_date}}
        }
    }
    r = requests.patch(url, headers=HEADERS, json=payload)
    if r.status_code == 200:
        return {"success": True, "message": f"Due date updated to {due_date}."}
    return {
        "success": False,
        "message": f"Failed to update due date: {r.status_code} {r.text[:150]}"
    }


def update_due_date_by_name(task_name: str, due_date: str) -> dict:
    """Convenience helper to find a task by name and update its due date."""
    row = find_task_by_name(task_name)
    if not row:
        return {"success": False, "message": f"Task not found: {task_name}"}
    page_id = _get_page_id(row)
    return update_due_date(page_id, due_date)
