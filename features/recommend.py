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
    """Score tasks by priority and due date urgency."""
    scored = []
    now = datetime.now()
    
    for row in results:
        name, status, priority, due_date = _extract_task_fields(row)
        if status == "Completed":
            continue
        
        # Priority scoring: High=50, Medium=30, Low=10
        priority_score = PRIORITY_WEIGHT.get(priority, 1) * 15
        
        # Urgency scoring based on due date
        urgency_score = 0
        if due_date:
            delta_days = (due_date - now).days
            
            if delta_days < 0:
                # Overdue: boost based on priority
                days_overdue = abs(delta_days)
                if priority == "High":
                    urgency_score = 50 + min(days_overdue * 2, 20)  # Max 70
                elif priority == "Medium":
                    urgency_score = 40 + min(days_overdue, 10)  # Max 50
                else:  # Low
                    urgency_score = 30 + min(days_overdue, 5)  # Max 35
            elif delta_days == 0:
                # Due today: very urgent
                urgency_score = 45
            elif delta_days == 1:
                # Due tomorrow: urgent
                urgency_score = 40
            elif delta_days <= 3:
                # Due within 3 days: important
                urgency_score = 30
            elif delta_days <= 7:
                # Due this week: moderate
                urgency_score = 20
            else:
                # Due later: low urgency (but still factor it in)
                urgency_score = max(0, 15 - (delta_days - 7) // 7)
        else:
            # No due date: lowest urgency
            urgency_score = 5
        
        # Final score: priority + urgency
        score = priority_score + urgency_score
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
