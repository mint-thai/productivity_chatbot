import os

REQUIRED_ENV = [
    "TELEGRAM_BOT_TOKEN",
    "NOTION_TOKEN",
    "NOTION_DATABASE_ID",
    "GOOGLE_API_KEY",
]


def validate_env() -> list[str]:
    missing = []
    for key in REQUIRED_ENV:
        if not os.getenv(key):
            missing.append(key)
    return missing
