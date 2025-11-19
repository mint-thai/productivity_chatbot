"""
SendGrid email reminder system (alternative to Gmail SMTP).
Works even when SMTP ports are blocked by firewalls.
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from features.notion_utils import get_tasks_raw

load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")  # Must be verified in SendGrid
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")


def send_email_sendgrid(subject: str, body: str, recipient: str = None):
    """
    Send email using SendGrid API (no SMTP ports needed).
    
    Setup:
    1. Sign up at https://sendgrid.com (free tier: 100 emails/day)
    2. Create API key at https://app.sendgrid.com/settings/api_keys
    3. Verify sender email at https://app.sendgrid.com/settings/sender_auth
    4. Add to .env:
       SENDGRID_API_KEY=your_key_here
       SENDER_EMAIL=verified@email.com
       RECIPIENT_EMAIL=where_to_send@email.com
    
    Install: pip install sendgrid
    """
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content
    except ImportError:
        return {
            "success": False,
            "message": "SendGrid not installed. Run: pip install sendgrid"
        }
    
    if not SENDGRID_API_KEY:
        return {
            "success": False,
            "message": "SENDGRID_API_KEY not configured in .env"
        }
    
    if not SENDER_EMAIL:
        return {
            "success": False,
            "message": "SENDER_EMAIL not configured in .env (must be verified in SendGrid)"
        }
    
    recipient = recipient or RECIPIENT_EMAIL
    if not recipient:
        return {
            "success": False,
            "message": "RECIPIENT_EMAIL not configured in .env"
        }
    
    try:
        message = Mail(
            from_email=SENDER_EMAIL,
            to_emails=recipient,
            subject=subject,
            html_content=body
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        return {
            "success": True,
            "message": f"Email sent successfully to {recipient} via SendGrid"
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"SendGrid error: {str(e)}"
        }


def get_upcoming_tasks(hours_ahead: int = 24):
    """Get tasks due today or tomorrow (within next 24 hours)."""
    all_tasks = get_tasks_raw()
    upcoming = []
    
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    
    for task in all_tasks:
        try:
            props = task.get("properties", {})
            
            name = (
                props.get("Task", {}).get("title", [{}])[0].get("plain_text", "Untitled")
                if props.get("Task", {}).get("title")
                else "Untitled"
            )
            
            status = props.get("Status", {}).get("status", {}).get("name", "Unknown")
            if status == "Completed":
                continue
            
            priority = props.get("Priority", {}).get("select", {}).get("name", "Low")
            
            due_obj = props.get("Due date", {}).get("date")
            due_start = due_obj.get("start") if isinstance(due_obj, dict) else None
            
            if due_start:
                date_part = due_start[:10]
                due_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                
                # Include tasks due today or tomorrow
                if due_date == today or due_date == tomorrow:
                    upcoming.append({
                        "name": name,
                        "due_date": datetime.combine(due_date, datetime.min.time()),
                        "priority": priority,
                        "status": status
                    })
        
        except Exception as e:
            print(f"⚠️ Error processing task: {e}")
            continue
    
    upcoming.sort(key=lambda x: x["due_date"])
    return upcoming


def format_reminder_email(tasks: list):
    """Format tasks into HTML email with motivational quote."""
    if not tasks:
        return None, None
    
    # Import motivate for motivational quotes
    try:
        from features.motivate import get_random_quote
        motivational_quote = get_random_quote()
    except:
        motivational_quote = "Stay focused! 💪"
    
    priority_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🔵"}
    
    if len(tasks) == 1:
        subject = f"⏰ Reminder: {tasks[0]['name']} is due soon"
    else:
        subject = f"⏰ Reminder: {len(tasks)} tasks due soon"
    
    html_body = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #4A90E2; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .task {{ 
                    background-color: #f9f9f9; 
                    border-left: 4px solid #4A90E2; 
                    padding: 15px; 
                    margin: 10px 0; 
                    border-radius: 4px;
                }}
                .task-name {{ font-weight: bold; font-size: 16px; }}
                .task-details {{ color: #666; margin-top: 5px; }}
                .high-priority {{ border-left-color: #E74C3C; }}
                .medium-priority {{ border-left-color: #F39C12; }}
                .low-priority {{ border-left-color: #3498DB; }}
                .motivation {{ 
                    margin-top: 30px; 
                    padding: 20px; 
                    background-color: #f0f7ff; 
                    border-left: 4px solid #4A90E2; 
                    border-radius: 4px;
                }}
                .quote {{ 
                    font-style: italic; 
                    color: #555; 
                    margin: 0;
                    font-size: 15px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>⏰ Kairos Task Reminder</h1>
            </div>
            <div class="content">
                <p>You have <strong>{len(tasks)}</strong> task{"s" if len(tasks) > 1 else ""} due in the next 24 hours:</p>
    """
    
    for task in tasks:
        priority_class = f"{task['priority'].lower()}-priority"
        emoji = priority_emoji.get(task['priority'], '🔵')
        due_str = task['due_date'].strftime('%b %d, %Y')
        
        html_body += f"""
                <div class="task {priority_class}">
                    <div class="task-name">{emoji} {task['name']}</div>
                    <div class="task-details">
                        📅 Due: {due_str}<br>
                        📊 Status: {task['status']}<br>
                        ⚡ Priority: {task['priority']}
                    </div>
                </div>
        """
    
    html_body += f"""
                <div class="motivation">
                    <p class="quote">✨ {motivational_quote}</p>
                </div>
                <p style="margin-top: 20px;">Stay focused! 💪</p>
            </div>
        </body>
    </html>
    """
    
    return subject, html_body


def check_and_send_reminders(hours_ahead: int = 24):
    """Check for upcoming tasks and send email via SendGrid."""
    try:
        upcoming_tasks = get_upcoming_tasks(hours_ahead)
        
        if not upcoming_tasks:
            return {
                "success": True,
                "message": "No upcoming tasks. No reminder sent.",
                "tasks_count": 0
            }
        
        subject, body = format_reminder_email(upcoming_tasks)
        result = send_email_sendgrid(subject, body)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Reminder sent for {len(upcoming_tasks)} task(s)",
                "tasks_count": len(upcoming_tasks)
            }
        else:
            return {
                "success": False,
                "message": result["message"],
                "tasks_count": len(upcoming_tasks)
            }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "tasks_count": 0
        }
