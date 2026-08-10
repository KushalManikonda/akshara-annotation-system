import os
from pathlib import Path

# Database
DATABASE_URL = "sqlite:///akshara.db"

# Storage
BASE_AUDIO_PATH = Path("assets/audio")

# Audio formats
SUPPORTED_AUDIO_FORMATS = [".wav", ".mp3", ".flac"]
