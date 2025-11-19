from __future__ import annotations
from typing import List, Dict
import os
import json
import re

try:
    import google.generativeai as genai
    from dotenv import load_dotenv
    load_dotenv()
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        llm = genai.GenerativeModel("gemini-2.5-flash")
    else:
        llm = None
except Exception:
    llm = None


def tasks_from_image_bytes(file_bytes: bytes, mime_type: str = "image/jpeg") -> List[Dict]:
    """Parse schedule from image screenshot using Gemini vision. Optimized for tables with dates."""
    
    if not llm:
        raise RuntimeError("Gemini API not configured. Please set GOOGLE_API_KEY in .env")
    
    try:
        # Upload image to Gemini
        import google.generativeai as genai
        
        # Create a temporary file-like object
        image_part = {
            "mime_type": mime_type,
            "data": file_bytes
        }
        
        prompt = """
Analyze this schedule screenshot and extract all assignments, exams, projects, and deadlines.

This is likely a table/calendar with dates. Look for:
- Assignment names
- Due dates (any format: "Nov 25", "11/25/2025", "November 25", etc.)
- Task types (exam, assignment, project, quiz, etc.)
- Course codes or names

For each item found, extract:
- name: Assignment/exam/project name (be specific)
- due_date: Due date in YYYY-MM-DD format. If you see "Nov 25" or "11/25", assume 2025.
- priority: "High" for exams/final projects/major deadlines, "Medium" for regular assignments/quizzes, "Low" for readings/participation
- project: Course code or name (if visible)

Output ONLY a JSON array. No explanations, no markdown, just the JSON array.

Example:
[
  {"name": "Assignment 1", "due_date": "2025-11-25", "priority": "Medium", "project": "COMP 101"},
  {"name": "Midterm Exam", "due_date": "2025-12-05", "priority": "High", "project": "COMP 101"}
]

If you cannot read the image clearly or find any tasks, return: []
"""
        
        response = llm.generate_content([prompt, image_part])
        raw = response.text.strip()
        
        # Extract JSON array
        match = re.search(r'\[[\s\S]*\]', raw)
        if not match:
            return []
        
        tasks = json.loads(match.group(0))
        return tasks
        
    except Exception as e:
        raise RuntimeError(f"Failed to parse image: {e}")
