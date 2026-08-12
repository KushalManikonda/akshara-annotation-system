"""
backend/core/config.py
----------------------
Application configuration using pydantic-settings.
All values come from environment variables or .env file.
"""

from functools import lru_cache
from typing import List, Union, Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


from pathlib import Path

# Absolute path to the .env file at the project root
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"

class Settings(BaseSettings):
    # ── Application ───────────────────────────────────────────────
    APP_NAME: str = "Akshara Annotation Platform"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ── Database ──────────────────────────────────────────────────
    # Supabase PostgreSQL connection string
    # Example: postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
    DATABASE_URL: str = ""

    # ── JWT ───────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "changeme-use-a-strong-random-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Accepts a JSON array OR comma-separated string in .env:
    #   CORS_ORIGINS="http://localhost:5173,http://localhost:3000"
    #   CORS_ORIGINS='["http://localhost:5173"]'
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Alternative dev port
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── Supabase ──────────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # ── Storage ───────────────────────────────────────────────────
    STORAGE_BUCKET: str = "audio-files"
    # Local fallback path for audio uploads
    BASE_AUDIO_PATH: str = "assets/audio"
    # Signed URL expiry for audio playback (seconds)
    AUDIO_URL_EXPIRY_SECONDS: int = 3600

    # ── Audio ─────────────────────────────────────────────────────────────────
    SUPPORTED_AUDIO_FORMATS: Union[List[str], str] = [".wav", ".mp3", ".flac"]

    @field_validator("SUPPORTED_AUDIO_FORMATS", mode="before")
    @classmethod
    def parse_audio_formats(cls, v: Any) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [fmt.strip() for fmt in v.split(",") if fmt.strip()]
        return v

    # ── Local Audio Root ──────────────────────────────────────────────────────────
    # Optional: server-side path to the root directory containing audio datasets.
    # Used ONLY for server-side ZIP export to include the original WAV.
    # NOT used for browser-based audio playback (users pick files locally).
    # Example (Linux):   AUDIO_ROOT_DIR=/data/akshara-audio
    # Example (Windows): AUDIO_ROOT_DIR=C:\AksharaAudio
    # If empty, exports will include a WAV_NOT_AVAILABLE.txt note instead of the WAV.
    AUDIO_ROOT_DIR: str = ""

    # ── Task Locking ──────────────────────────────────────────────
    TASK_LOCK_TIMEOUT_MINUTES: int = 30
    TASK_LOCK_HEARTBEAT_INTERVAL_SECONDS: int = 60

    # ── Pipeline Configuration ─────────────────────────────────────────────────
    # Hugging Face token — required for Pyannote (Hindi pipeline)
    HF_TOKEN: str = ""
    # Whisper model path or HF model ID (English pipeline)
    WHISPER_MODEL_PATH: str = "openai/whisper-base"
    # AI4Bharat IndicConformer model ID (Hindi + Telugu pipelines)
    INDIC_CONFORMER_MODEL: str = "ai4bharat/indic-conformer-600m-multilingual"
    # Temporary directory for pipeline intermediate files (separated vocals, etc.)
    PIPELINE_TEMP_DIR: str = "/tmp/akshara_pipeline"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    Use this as a FastAPI dependency: Depends(get_settings).
    """
    return Settings()


# Module-level singleton for non-DI usage
settings = get_settings()
