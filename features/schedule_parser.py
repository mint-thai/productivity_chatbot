from __future__ import annotations
from typing import List, Dict
from datetime import datetime
import io

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None


EXAMPLE_TEXT = """
Course: MATH 101
Task: Homework 3 due:2025-11-20 [high]
Task: Midterm due:2025-11-25 [high]
Task: Review notes due:2025-11-18 [medium]
"""


def parse_text_to_tasks(text: str) -> List[Dict]:
    tasks = []
    for line in text.splitlines():
        line = line.strip()
        if not line or not ("due:" in line or "due:" in line.lower()):
            continue
        name = line
        priority = "Medium"
        if "[high]" in line.lower():
            priority = "High"
            name = name.replace("[high]", "").strip()
        elif "[low]" in line.lower():
            priority = "Low"
            name = name.replace("[low]", "").strip()
        elif "[medium]" in line.lower():
            priority = "Medium"
            name = name.replace("[medium]", "").strip()
        due_date = None
        if "due:" in line.lower():
            parts = line.lower().split("due:")
            before = parts[0]
            after = line[len(before) + 4:]
            token = after.strip().split()[0]
            try:
                _ = datetime.strptime(token, "%Y-%m-%d")
                due_date = token
                name = before.strip()
            except Exception:
                pass
        if name:
            tasks.append({"name": name.strip(), "priority": priority, "due_date": due_date, "project": ""})
    return tasks


def parse_pdf_bytes(file_bytes: bytes) -> str:
    if not PdfReader:
        raise RuntimeError("PyPDF2 not installed. Please add PyPDF2 to requirements.txt")
    reader = PdfReader(io.BytesIO(file_bytes))
    text = []
    for page in reader.pages:
        text.append(page.extract_text() or "")
    return "\n".join(text)


def tasks_from_pdf_bytes(file_bytes: bytes) -> List[Dict]:
    text = parse_pdf_bytes(file_bytes)
    return parse_text_to_tasks(text)
