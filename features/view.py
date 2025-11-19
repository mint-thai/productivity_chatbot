from datetime import datetime, timedelta

def filter_tasks_by_date(results, date_filter=None):
    """
    Filter tasks by date range.
    date_filter can be: 'today', 'tomorrow', 'week', or None (no filter)
    """
    if not date_filter:
        return results
    
    today = datetime.now().date()
    
    if date_filter == 'today':
        target_date = today
        match_dates = [target_date]
    elif date_filter == 'tomorrow':
        target_date = today + timedelta(days=1)
        match_dates = [target_date]
    elif date_filter == 'week':
        # Next 7 days
        match_dates = [today + timedelta(days=i) for i in range(8)]
    else:
        return results
    
    filtered = []
    for row in results:
        try:
            props = row.get("properties", {})
            due_obj = props.get("Due date", {}).get("date")
            due_start = due_obj.get("start") if isinstance(due_obj, dict) else None
            
            if due_start:
                date_part = due_start[:10]
                task_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                if task_date in match_dates:
                    filtered.append(row)
        except Exception:
            continue
    
    return filtered


def format_tasks_list(results, date_filter=None, show_all=False):
    # Apply date filter if specified
    if date_filter:
        results = filter_tasks_by_date(results, date_filter)
    
    if not results:
        if date_filter:
            filter_names = {'today': 'today', 'tomorrow': 'tomorrow', 'week': 'this week'}
            return f"No tasks found for {filter_names.get(date_filter, 'the specified period')}."
        return "No tasks found."

    buckets = {"In progress": [], "Not started": [], "Completed": []}
    # Priority indicators: 🔴 High, 🟡 Medium, 🔵 Low
    priority_prefix = {"High": "🔴", "Medium": "🟡", "Low": "🔵"}

    for row in results:
        try:
            props = row.get("properties", {})

            name = (
                props.get("Task", {}).get("title", [{}])[0].get("plain_text", "Untitled")
                if props.get("Task", {}).get("title")
                else "Untitled"
            )
            status = props.get("Status", {}).get("status", {}).get("name", "Unknown")
            priority = props.get("Priority", {}).get("select", {}).get("name", "Low")
            prefix = priority_prefix.get(priority, "🔵")

            # ✅ exact key: "Due date" (case-sensitive)
            due_obj = props.get("Due date", {}).get("date")
            due_start = due_obj.get("start") if isinstance(due_obj, dict) else None

            if due_start:
                # handle date or datetime
                date_part = due_start[:10]
                try:
                    dt = datetime.strptime(date_part, "%Y-%m-%d")
                    date_str = f"Due: {dt.strftime('%b %d, %Y')}"
                except Exception:
                    date_str = f"Due: {due_start}"
            else:
                date_str = "No date"

            line = f"{prefix} {name} — {date_str}"
            (buckets[status] if status in buckets else buckets.setdefault("Other", [])).append(line)

        except Exception as e:
            print(f"⚠️ Skipped malformed task: {e}")
            continue

    # Build final output
    lines = []
    limit = None if show_all else 3

    if buckets["In progress"]:
        lines.append("*IN PROGRESS*")
        lines.extend(buckets["In progress"][:limit])

    if buckets["Not started"]:
        lines.append("\n*NOT STARTED*")
        lines.extend(buckets["Not started"][:limit])

    if buckets["Completed"]:
        lines.append("\n*COMPLETED*")
        lines.extend(buckets["Completed"][:limit])

    output = "\n".join(lines).strip()
    return output or "No tasks found."
