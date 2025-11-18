# Kairos — Telegram-Based Productivity Assistant

**Author:** Mint Thai

**Role:** Data Science Student / Product Builder 

**Last Updated:** November 2025

## Project Overview

**Kairos** is a Telegram-based productivity bot that helps university students manage their workload, track deadlines, and prioritize effectively, so they can study more efficiently and stay on top of their goals. The bot integrates Notion for task management and Google's Gemini 2.5 Flash for conversational AI assistance. 

## Product Architecture

Kairos is built around modular, asynchronous components:

| Component | Description |
|------------|--------------|
| **Telegram Bot Interface** | Handles user commands and text messages via the Telegram API using `python-telegram-bot`. Manages commands like `/add`, `/tasks`, and `/pomodoro`. |
| **Task Management (Notion Integration)** | Connects to the Notion API to create, retrieve, and format tasks stored in a Notion database. Handles parsing, prioritization, due dates, and project tagging. |
| **Pomodoro Timer System** | Implements non-blocking Pomodoro sessions using Telegram’s `JobQueue`, allowing work/break timers, progress tracking, and session management per user. |
| **Conversational AI Layer (Gemini 2.5 Flash)** | Uses Google’s Gemini API to provide intelligent, context-aware replies, leveraging Notion task data to ensure factual, relevant responses. |
| **Task Formatter & Filter** | Structures Notion data into readable Telegram messages, grouping tasks by status and filtering by date (today, tomorrow, this week). |

The bot runs continuously via polling and uses `.env` configuration for tokens (Telegram, Notion, and Google APIs).

<div style="page-break-after: always;"></div>

## Functional Feature List

| **Feature** | **Description** |
|--------------|----------------|
| **1. Task Search / Retrieval** | View and filter Notion tasks by status or date (e.g., *today*, *tomorrow*, *this week*) using `/tasks` or natural queries like “What’s due today?”. |
| **2. Task Parsing and Creation** | Add tasks in natural language (e.g., “Finish homework [high] due:tomorrow project:Math”). Automatically extracts priority, due date, and project. |
| **3. Pomodoro Scheduling** | Manage focus sessions with the Pomodoro technique, including start, check, .s, or stop timers directly in Telegram. |
| **4. FAQ / Q&A** | Provides concise, AI-powered responses to productivity-related questions via Google’s Gemini 2.5 Flash. |
| **5. Error Handling** | Gives clear feedback and examples for invalid commands or incomplete inputs. |
| **6. Context Awareness (Limited)** | Uses Notion data context in Gemini responses for accurate, task-based answers. |
| **7. Integration Ecosystem** | Connects Telegram (UI), Notion (task storage), and Gemini (AI engine) through secure APIs. |
| **8. Task Status Updates** | Users can mark tasks as complete or change their status, automatically syncing updates to Notion. |
| **9. Email Reminders** | Sends automated reminders for upcoming tasks or deadlines via email. |
| **10. Habit Tracking** | Logs recurring habits (e.g., study sessions) and tracks consistency over time. |rec
| **11. Motivational Nudges** | Sends short encouragements or productivity tips based on user activity. |
| **12. Task Recommendations** | Suggests next best tasks based on priority, due dates, or recent activity. |
| **13. Productivity Analytics** | Tracks and visualizes metrics such as completed tasks, focus sessions, and progress trends. |
| **14. Focus Mode / Relaxing Music** | Plays ambient or focus music during Pomodoro sessions to enhance concentration. |
| **15. Class Schedule Parsing** | Parses uploaded class schedules to auto-create tasks or deadlines in Notion. |
