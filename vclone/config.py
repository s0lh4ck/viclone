import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
DB_PATH = os.path.join(BASE_DIR, "data", "viclone.db")
RVC_BRIDGE_DIR = os.path.join(BASE_DIR, "rvc_bridge")

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
