import random

FOCUS_LINKS = [
    "https://www.youtube.com/watch?v=sUwD3GRPJos&t=4241s",
    "https://www.youtube.com/watch?v=5Q2Pc-e-8Qc",
    "https://www.youtube.com/watch?v=ATOPZqUfzUo",
]


def get_focus_link() -> str:
    return random.choice(FOCUS_LINKS)
