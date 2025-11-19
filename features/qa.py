"""
Q&A module for Kairos productivity chatbot.
Handles productivity-related questions using Gemini AI.
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

MODEL = "gemini-2.5-flash"
llm = genai.GenerativeModel(MODEL)


def get_qa_response(question: str, task_summary: str = None) -> str:
    """
    Get AI response to productivity questions.
    
    Args:
        question: User's question
        task_summary: Optional brief summary of current tasks (not full list)
    
    Returns:
        str: AI response
    """
    
    # Build context prompt
    context = ""
    if task_summary:
        context = f"\n\nUser's current workload summary:\n{task_summary}"
    
    prompt = f"""
You are Kairos — a productivity assistant for university students balancing courses, jobs, internships, and deadlines.

Format your response exactly like this:
1. One empathetic sentence acknowledging their situation
2. One practical tip (1-2 sentences, actionable and specific)

Tone: Supportive friend who gets it. No corporate jargon, no emojis, no asterisks or bold text.
Be realistic and direct. Never invent details they didn't mention. Try keeping your answers concise and casual, simple English. {context}

User question:
{question}
"""
    
    try:
        response = llm.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"I'm having trouble processing that question right now. Error: {str(e)}\n\nTry rephrasing your question or ask something else!"


def is_productivity_question(text: str) -> bool:
    """
    Check if text is likely a productivity-related question.
    
    Args:
        text: User's message
    
    Returns:
        bool: True if it appears to be a productivity question
    """
    # Question indicators
    question_words = ["how", "what", "why", "when", "where", "should", "can", "could", "would"]
    question_markers = ["?", "help", "advice", "tips", "suggest"]
    
    text_lower = text.lower()
    
    # Check for question words or markers
    has_question_indicator = (
        any(text_lower.startswith(word) for word in question_words) or
        any(marker in text_lower for marker in question_markers) or
        text.endswith("?")
    )
    
    # Productivity topics
    productivity_keywords = [
        "time", "manage", "organize", "productive", "focus", "study", "work",
        "balance", "priority", "deadline", "task", "schedule", "plan",
        "motivation", "burnout", "stress", "exam", "assignment", "job",
        "interview", "application", "course", "procrastinate"
    ]
    
    has_productivity_topic = any(keyword in text_lower for keyword in productivity_keywords)
    
    return has_question_indicator and has_productivity_topic and len(text.split()) >= 3


def get_brief_task_summary(tasks_list: list, max_tasks: int = 5) -> str:
    """
    Create a brief summary of tasks for context (not full formatted list).
    
    Args:
        tasks_list: List of task dictionaries
        max_tasks: Maximum number of tasks to include
    
    Returns:
        str: Brief summary
    """
    if not tasks_list:
        return "No current tasks"
    
    summary_lines = []
    for i, task in enumerate(tasks_list[:max_tasks]):
        try:
            props = task.get("properties", {})
            name = (
                props.get("Task", {}).get("title", [{}])[0].get("plain_text", "Untitled")
                if props.get("Task", {}).get("title")
                else "Untitled"
            )
            priority = props.get("Priority", {}).get("select", {}).get("name", "Medium")
            status = props.get("Status", {}).get("status", {}).get("name", "Not started")
            
            summary_lines.append(f"- {name} [{priority}] - {status}")
        except:
            continue
    
    if len(tasks_list) > max_tasks:
        summary_lines.append(f"...and {len(tasks_list) - max_tasks} more tasks")
    
    return "\n".join(summary_lines)
