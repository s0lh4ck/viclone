import os
import sys

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
DB_PATH = os.path.join(BASE_DIR, "data", "viclone.db")
LOG_DIR = os.path.join(BASE_DIR, "logs")
RVC_BRIDGE_DIR = os.path.join(BASE_DIR, "rvc_bridge")

# Authentication and session security. If VICLONE_PASSWORD is unset, the app
# runs without a login gate -- fine for a quick local trial, not for handling
# real client data. Always set both before pointing this at a real audit.
SECRET_KEY = os.environ.get("VICLONE_SECRET_KEY")
ADMIN_PASSWORD = os.environ.get("VICLONE_PASSWORD")

MAX_UPLOAD_MB = int(os.environ.get("VICLONE_MAX_UPLOAD_MB", "500"))

# Flip this only once you have wired rvc_bridge/realtime.py to a real,
# verified voice-conversion engine. Until then the live-call feature is a
# passthrough (no conversion), and the UI says so.
LIVE_ENGINE_IMPLEMENTED = (
    os.environ.get("VICLONE_LIVE_ENGINE_IMPLEMENTED", "false").lower() == "true"
)

ALLOWED_REFERENCE_EXTENSIONS = {
    "mp3", "wav", "m4a", "aac", "flac", "ogg",
    "mp4", "mov", "mkv", "webm", "avi",
}

TTS_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
DEFAULT_LANGUAGE = "es"
SAMPLE_RATE = 24000

# Real-time voice conversion (for live calls through a softphone such as
# MicroSIP). ViClone only orchestrates this: training and live inference are
# delegated to whatever RVC-style toolkit is installed locally, via the thin
# adapters in rvc_bridge/. See README for setup.
RVC_PYTHON_BIN = os.environ.get("RVC_PYTHON_BIN", sys.executable)
RVC_TRAIN_EPOCHS = int(os.environ.get("RVC_TRAIN_EPOCHS", "200"))
LIVE_SAMPLE_RATE = 16000
