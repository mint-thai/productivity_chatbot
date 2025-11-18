from datetime import datetime

# Simple priority weights
PRIORITY_WEIGHT = {"High": 3, "Medium": 2, "Low": 1}


def _extract_task_fields(row: dict):
    props = row.get("properties", {})
    title_arr = props.get("Task", {}).get("title") or []
    name = title_arr[0].get("plain_text") if title_arr else "Untitled"
    status = props.get("Status", {}).get("status", {}).get("name", "Unknown")
    priority = props.get("Priority", {}).get("select", {}).get("name", "Low")
    due_obj = props.get("Due date", {}).get("date")
    due_start = due_obj.get("start") if isinstance(due_obj, dict) else None
    due_date = None
    if due_start:
        try:
            due_date = datetime.strptime(due_start[:10], "%Y-%m-%d")
        except Exception:
            due_date = None
    return name, status, priority, due_date


def recommend(results: list, limit: int = 3) -> list:
    """Score tasks by priority and due date proximity."""
    scored = []
    now = datetime.now()
    for row in results:
        name, status, priority, due_date = _extract_task_fields(row)
        if status == "Completed":
            continue
        base = PRIORITY_WEIGHT.get(priority, 1)
        date_score = 0
        if due_date:
            delta_days = (due_date - now).days
            # Sooner due increases score; overdue get a small boost
            date_score = max(0, 10 - max(delta_days, 0)) + (5 if delta_days < 0 else 0)
        score = base * 10 + date_score
        scored.append((score, name, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, __, row in scored[:limit]]


def format_recommendations(rows: list) -> str:
    if not rows:
        return "No recommendations right now."
    lines = ["Try these next:"]
    for i, row in enumerate(rows, 1):
        name, status, priority, due_date = _extract_task_fields(row)
        due_str = due_date.strftime('%b %d, %Y') if due_date else 'No date'
        lines.append(f"{i}. {name} — {priority} priority — Due: {due_str}")
    return "\n".join(lines)
