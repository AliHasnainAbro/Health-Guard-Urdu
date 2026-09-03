"""TTS fallback using gTTS (Google Text-to-Speech) — Urdu supported via lang='ur'."""

import os
import uuid

from gtts import gTTS

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "audio_output")
os.makedirs(AUDIO_DIR, exist_ok=True)


def text_to_speech_urdu(text: str) -> str:
    """Convert Urdu text to speech, return path to the saved MP3 file."""
    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)
    tts = gTTS(text=text, lang="ur")
    tts.save(filepath)
    return filepath
