"""Configuration for David's Voice backend."""

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "voice_studio.db"
RECORDINGS_DIR = DATA_DIR / "recordings"

# Existing dataset path (relative to the TTS project root)
TTS_ROOT = PROJECT_ROOT.parent
EXISTING_DATASET_DIR = TTS_ROOT / "dataset_40_items"
EXISTING_METADATA_JSON = EXISTING_DATASET_DIR / "metadata.json"
EXISTING_SENTENCES_JSON = TTS_ROOT / "recording_sentences.json"

# Audio specifications (must match existing dataset)
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 1
AUDIO_BIT_DEPTH = 16

# Recording constraints
MIN_DURATION_SECONDS = 3.0
MAX_DURATION_SECONDS = 30.0
TARGET_RECORDINGS = 200

# Quality thresholds
SNR_THRESHOLD_A = 30.0  # dB - excellent
SNR_THRESHOLD_B = 20.0  # dB - good
SNR_THRESHOLD_C = 15.0  # dB - acceptable
CLIPPING_THRESHOLD = 0.99  # fraction of max amplitude
MAX_SILENCE_RATIO = 0.4  # 40% silence is too much

# Anthropic API
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"

# Server
HOST = "0.0.0.0"
PORT = 8001
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
