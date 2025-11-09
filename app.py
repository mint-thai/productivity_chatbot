import streamlit as st
import requests
from notion_utils import add_task, list_tasks
from google import genai

# Load secrets
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

client = genai.Client(api_key=GOOGLE_API_KEY)

st.set_page_config(page_title="Student Productivity Chatbot", page_icon="🎓")
st.title("🎓 Student Productivity Assistant")

st.caption("Try: `add task finish essay due 2025-11-12 high`, `show tasks`, or `weekly summary`")

if "chat" not in st.session_state:
    st.session_state.chat = []

def gemini_reply(messages):
    model = "gemini-1.5-flash"
    resp = client.models.generate_content(model=model, contents=messages)
    return resp.text

def parse_add(text):
    # expected: "add task <title> due <YYYY-MM-DD> [priority]"
    try:
        body = text[len("add task"):].strip()
        title, rest = body.split("due", 1)
        title = title.strip()
        parts = rest.strip().split()
        date = parts[0]
        priority = (parts[1] if len(parts) > 1 else "Medium").capitalize()
        if priority not in ["High", "Medium", "Low"]:
            priority = "Medium"
        return title, date, priority
    except Exception:
        return None, None, None

for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user = st.chat_input("Type here...")
if user:
    st.session_state.chat.append({"role": "user", "content": user})
    lower = user.lower()

    if lower.startswith("add task"):
        title, date, pr = parse_add(user)
        if not title or not date:
            reply = "Format: `add task <title> due <YYYY-MM-DD> [high|medium|low]`"
        else:
            try:
                add_task(title, date, pr)
                reply = f"✅ Added **{title}** (due {date}, priority {pr}) to Notion."
            except Exception as e:
                reply = f"❌ Error adding task: {e}"

    elif "show" in lower and "task" in lower:
        items = list_tasks()
        if not items:
            reply = "🎉 No tasks found."
        else:
            lines = [f"- **{t['name']}** · Due: {t['due'] or '—'} · Priority: {t['priority'] or '—'}"
                     for t in items]
            reply = "🗓️ Your tasks:\n" + "\n".join(lines)

    elif "summary" in lower or "week" in lower:
        tasks = list_tasks()
        if not tasks:
            reply = "🎉 No tasks to summarize!"
        else:
            bullet = "\n".join([f"{t['name']} (due {t['due']}, priority {t['priority']})" for t in tasks])
            prompt = f"You are a friendly student productivity coach. Summarize and prioritize:\n{bullet}"
            reply = gemini_reply(prompt)

    else:
        reply = ("Try one of these:\n"
                 "- `add task write essay due 2025-11-15 high`\n"
                 "- `show tasks`\n"
                 "- `weekly summary`")

    st.session_state.chat.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)
