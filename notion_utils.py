import streamlit as st
import requests

NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
NOTION_DATABASE_ID = st.secrets["NOTION_DATABASE_ID"]

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def add_task(task_name, due_date, priority="Medium"):
    url = "https://api.notion.com/v1/pages"
    body = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Task Name": {"title": [{"text": {"content": task_name}}]},
            "Due Date": {"date": {"start": due_date}},
            "Priority": {"select": {"name": priority}},
            "Status": {"select": {"name": "To Do"}},
        },
    }
    r = requests.post(url, headers=HEADERS, json=body)
    r.raise_for_status()
    return r.json()

def list_tasks(limit=20):
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    r = requests.post(url, headers=HEADERS, json={"page_size": limit})
    r.raise_for_status()
    results = []
    for row in r.json().get("results", []):
        p = row["properties"]
        name = p["Task Name"]["title"][0]["plain_text"] if p["Task Name"]["title"] else "Untitled"
        due = p["Due Date"]["date"]["start"] if p["Due Date"]["date"] else None
        pr  = p["Priority"]["select"]["name"] if p["Priority"]["select"] else None
        stt = p["Status"]["select"]["name"] if p["Status"]["select"] else None
        results.append({"name": name, "due": due, "priority": pr, "status": stt})
    return results
