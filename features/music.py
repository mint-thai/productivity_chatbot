import random

FOCUS_SONGS = {
    "1": {
        "name": "🎵 Lo-fi Hip Hop Radio - Beats to Study/Relax",
        "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
        "duration": "Live stream"
    },
    "2": {
        "name": "🎹 Peaceful Piano - Calm & Relaxing",
        "url": "https://www.youtube.com/watch?v=5Q2Pc-e-8Qc",
        "duration": "3 hours"
    },
    "3": {
        "name": "🌧️ Rain Sounds + Jazz Music",
        "url": "https://www.youtube.com/watch?v=ATOPZqUfzUo",
        "duration": "10 hours"
    },
    "4": {
        "name": "🧘 Deep Focus - Ambient Sounds",
        "url": "https://www.youtube.com/watch?v=sUwD3GRPJos",
        "duration": "2 hours"
    },
    "5": {
        "name": "🎧 Synthwave - Cyberpunk Vibes",
        "url": "https://www.youtube.com/watch?v=4xDzrJKXOOY",
        "duration": "1 hour"
    }
}


def get_music_menu() -> str:
    """Returns formatted menu of focus music options"""
    menu = "🎵 **Focus Music** - Pick a vibe:\n\n"
    for key, song in FOCUS_SONGS.items():
        menu += f"{key}. {song['name']}\n   ⏱ {song['duration']}\n\n"
    menu += "Reply with a number (1-5) to play!"
    return menu


def get_song_by_choice(choice: str) -> dict | None:
    """Returns song dict for given choice, or None if invalid"""
    return FOCUS_SONGS.get(choice.strip())


def get_random_song() -> dict:
    """Returns a random song dict"""
    return random.choice(list(FOCUS_SONGS.values()))
