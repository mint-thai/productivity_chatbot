"""
Email reminder system for Kairos productivity chatbot.
Sends automated reminders for upcoming tasks or deadlines via email.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv

from features.notion_utils import get_tasks_raw

load_dotenv()

# Email configuration from environment
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")


def send_email(subject: str, body: str, recipient: str = None):
    """
    Send an email using SMTP.
    
    Args:
        subject: Email subject line
        body: Email body content (can be HTML)
        recipient: Recipient email address (defaults to RECIPIENT_EMAIL from .env)
    
    Returns:
        dict: Result with 'success' boolean and 'message' string
    """
    if not all([EMAIL_ADDRESS, EMAIL_PASSWORD]):
        return {
            "success": False,
            "message": "Email credentials not configured. Please set EMAIL_ADDRESS and EMAIL_PASSWORD in .env"
        }
    
    recipient = recipient or RECIPIENT_EMAIL
    if not recipient:
        return {
            "success": False,
            "message": "No recipient email configured. Please set RECIPIENT_EMAIL in .env"
        }
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient
        msg['Subject'] = subject
        
        # Attach HTML body
        html_part = MIMEText(body, 'html')
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        
        return {
            "success": True,
            "message": f"Email sent successfully to {recipient}"
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to send email: {str(e)}"
        }


def get_upcoming_tasks(hours_ahead: int = 24):
    """
    Get tasks due within the specified number of hours.
    
    Args:
        hours_ahead: Number of hours to look ahead (default: 24)
    
    Returns:
        list: Tasks due within the specified timeframe
    """
    all_tasks = get_tasks_raw()
    upcoming = []
    
    now = datetime.now()
    cutoff_time = now + timedelta(hours=hours_ahead)
    
    for task in all_tasks:
        try:
            props = task.get("properties", {})
            
            # Get task details
            name = (
                props.get("Task", {}).get("title", [{}])[0].get("plain_text", "Untitled")
                if props.get("Task", {}).get("title")
                else "Untitled"
            )
            
            status = props.get("Status", {}).get("status", {}).get("name", "Unknown")
            
            # Skip completed tasks
            if status == "Completed":
                continue
            
            priority = props.get("Priority", {}).get("select", {}).get("name", "Low")
            
            # Get due date
            due_obj = props.get("Due date", {}).get("date")
            due_start = due_obj.get("start") if isinstance(due_obj, dict) else None
            
            if due_start:
                # Parse due date
                date_part = due_start[:10]
                due_date = datetime.strptime(date_part, "%Y-%m-%d")
                
                # Check if task is due within the timeframe
                if now <= due_date <= cutoff_time:
                    upcoming.append({
                        "name": name,
                        "due_date": due_date,
                        "priority": priority,
                        "status": status
                    })
        
        except Exception as e:
            print(f"⚠️ Error processing task for reminder: {e}")
            continue
    
    # Sort by due date
    upcoming.sort(key=lambda x: x["due_date"])
    return upcoming


def format_reminder_email(tasks: list):
    """
    Format tasks into an HTML email body.
    
    Args:
        tasks: List of task dictionaries
    
    Returns:
        tuple: (subject, html_body)
    """
    if not tasks:
        return None, None
    
    priority_emoji = {"High": "🔴", "Medium": "🟠", "Low": "🟣"}
    
    # Email subject
    if len(tasks) == 1:
        subject = f"⏰ Reminder: {tasks[0]['name']} is due soon"
    else:
        subject = f"⏰ Reminder: {len(tasks)} tasks due soon"
    
    # Email body (HTML)
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
                .low-priority {{ border-left-color: #9B59B6; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>⏰ Kairos Task Reminder</h1>
            </div>
            <div class="content">
                <p>Hi there,</p>
                <p>You have <strong>{len(tasks)}</strong> task{"s" if len(tasks) > 1 else ""} due in the next 24 hours:</p>
    """
    
    for task in tasks:
        priority_class = f"{task['priority'].lower()}-priority"
        emoji = priority_emoji.get(task['priority'], '🟣')
        due_str = task['due_date'].strftime('%b %d, %Y at %I:%M %p')
        
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
    
    html_body += """
                <p>Stay focused and keep up the great work! 💪</p>
            </div>
            <div class="footer">
                <p>This is an automated reminder from Kairos — Your Productivity Assistant</p>
            </div>
        </body>
    </html>
    """
    
    return subject, html_body


def check_and_send_reminders(hours_ahead: int = 24):
    """
    Check for upcoming tasks and send email reminders.
    
    Args:
        hours_ahead: Number of hours to look ahead (default: 24)
    
    Returns:
        dict: Result with 'success' boolean, 'message' string, and 'tasks_count' int
    """
    try:
        # Get upcoming tasks
        upcoming_tasks = get_upcoming_tasks(hours_ahead)
        
        if not upcoming_tasks:
            return {
                "success": True,
                "message": "No upcoming tasks found. No reminder sent.",
                "tasks_count": 0
            }
        
        # Format email
        subject, body = format_reminder_email(upcoming_tasks)
        
        # Send email
        result = send_email(subject, body)
        
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
            "message": f"Error checking reminders: {str(e)}",
            "tasks_count": 0
        }


# For testing
if __name__ == "__main__":
    print("🔔 Testing email reminder system...")
    result = check_and_send_reminders()
    print(f"Result: {result}")
