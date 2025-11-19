import os
import json
from typing import Optional
from io import BytesIO

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

try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False


# Store user language preferences (user_id -> language_code)
user_languages = {}

# Store user TTS preferences (user_id -> bool)
user_tts_enabled = {}

SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "ko": "Korean",
    "pt": "Portuguese",
    "it": "Italian",
    "ru": "Russian",
    "ar": "Arabic",
    "hi": "Hindi"
}

# Map language codes to TTS language codes
TTS_LANGUAGE_MAP = {
    "en": "en",
    "es": "es",
    "fr": "fr",
    "de": "de",
    "zh": "zh-CN",
    "ja": "ja",
    "ko": "ko",
    "pt": "pt",
    "it": "it",
    "ru": "ru",
    "ar": "ar",
    "hi": "hi"
}


def set_language(user_id: int, language_code: str) -> dict:
    """Set user's preferred language"""
    # Strip angle brackets and whitespace
    language_code = language_code.strip("<>").strip().lower()
    
    if language_code not in SUPPORTED_LANGUAGES:
        return {
            "success": False,
            "message": f"❌ Language '{language_code}' not supported. Available: {', '.join(SUPPORTED_LANGUAGES.keys())}"
        }
    
    user_languages[user_id] = language_code
    lang_name = SUPPORTED_LANGUAGES[language_code]
    return {
        "success": True,
        "message": f"✅ Language set to {lang_name} ({language_code})"
    }


def get_language(user_id: int) -> str:
    """Get user's preferred language (default: English)"""
    return user_languages.get(user_id, "en")


def translate_text(text: str, target_language: str) -> str:
    """Translate text to target language using Gemini AI"""
    
    # Skip translation for English
    if target_language == "en":
        return text
    
    if not llm:
        return text  # Return original if translation unavailable
    
    lang_name = SUPPORTED_LANGUAGES.get(target_language, target_language)
    
    try:
        prompt = f"""
Translate the following text to {lang_name} ({target_language}).

IMPORTANT RULES:
- Preserve ALL emojis, symbols, and special characters exactly as they are
- Preserve ALL URLs, links, and dates
- Preserve formatting (bullets, newlines, etc.)
- Keep technical terms like "Pomodoro", "Notion", proper names
- Keep command names like /tasks, /add, /pomodoro unchanged
- Translate only the natural language parts

Text to translate:
{text}

Output ONLY the translated text, nothing else.
"""
        
        response = llm.generate_content(prompt)
        translated = response.text.strip()
        return translated
        
    except Exception as e:
        print(f"Translation error: {e}")
        return text  # Return original on error


def enable_tts(user_id: int) -> dict:
    """Enable text-to-speech for user"""
    if not TTS_AVAILABLE:
        return {
            "success": False,
            "message": "❌ Text-to-speech not available. Install gTTS: pip install gTTS"
        }
    user_tts_enabled[user_id] = True
    return {
        "success": True,
        "message": "🔊 Text-to-speech enabled! You'll receive audio messages."
    }


def disable_tts(user_id: int) -> dict:
    """Disable text-to-speech for user"""
    user_tts_enabled[user_id] = False
    return {
        "success": True,
        "message": "🔇 Text-to-speech disabled."
    }


def is_tts_enabled(user_id: int) -> bool:
    """Check if TTS is enabled for user"""
    return user_tts_enabled.get(user_id, False)


def text_to_speech(text: str, language_code: str = "en") -> BytesIO:
    """Convert text to speech audio file"""
    if not TTS_AVAILABLE:
        raise RuntimeError("gTTS not installed")
    
    # Get TTS language code
    tts_lang = TTS_LANGUAGE_MAP.get(language_code, "en")
    
    # Generate speech
    tts = gTTS(text=text, lang=tts_lang, slow=False)
    
    # Save to BytesIO
    audio_buffer = BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)
    
    return audio_buffer


def get_language_menu() -> str:
    """Returns formatted menu of supported languages"""
    menu = "🌍 **Language & Audio Settings**\n\nSupported languages:\n\n"
    for code, name in SUPPORTED_LANGUAGES.items():
        menu += f"• {code} - {name}\n"
    menu += "\n**Commands:**\n"
    menu += "• /language <code> — Set language (e.g., /language es)\n"
    menu += "• /tts_on — Enable audio responses 🔊 (motivational quotes only)\n"
    menu += "• /tts_off — Disable audio responses 🔇"
    return menu
