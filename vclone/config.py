import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
DB_PATH = os.path.join(BASE_DIR, "data", "viclone.db")

ALLOWED_REFERENCE_EXTENSIONS = {
    "mp3", "wav", "m4a", "aac", "flac", "ogg",
    "mp4", "mov", "mkv", "webm", "avi",
}

TTS_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
DEFAULT_LANGUAGE = "es"
SAMPLE_RATE = 24000
