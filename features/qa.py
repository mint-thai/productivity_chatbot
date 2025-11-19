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
    Check if text is EXPLICITLY asking for productivity help/tips/advice.
    Very strict - only triggers on clear help requests, not commands or statements.
    
    Args:
        text: User's message
    
    Returns:
        bool: True if it's clearly asking for productivity advice
    """
    text_lower = text.lower()
    
    # EXPLICIT help request phrases - user must clearly ask for help/tips/advice
    explicit_help_phrases = [
        "i need help",
        "i need tips",
        "i need advice",
        "give me tips",
        "give me advice",
        "help me",
        "any tips",
        "any advice",
        "can you help",
        "how do i",
        "how can i",
        "how should i",
        "what should i do",
        "tips for",
        "advice on",
        "advice for"
    ]
    
    # Must contain one of these explicit phrases
    is_explicit_help = any(phrase in text_lower for phrase in explicit_help_phrases)
    
    # Must also be a question (ends with ?) OR contains help/tips/advice
    is_question_format = text.endswith("?") or any(word in text_lower for word in ["help", "tips", "advice"])
    
    # Must be substantial (at least 4 words)
    is_substantial = len(text.split()) >= 4
    
    return is_explicit_help and is_question_format and is_substantial


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
