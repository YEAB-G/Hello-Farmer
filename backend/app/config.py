"""Typed configuration management for Hello Farmer."""
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    # Provider keys & defaults (Gemini-first)
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-3.5-flash"
    GEMINI_API_KEY: str | None = None
    GEMINI_STT_MODEL: str = "gemini-3.5-transcribe"
    GEMINI_LLM_MODEL: str = "gemini-3.5-flash"
    GEMINI_TTS_MODEL: str = "gemini-3.8-flash-tts"
    GEMINI_TTS_VOICE: str = "Kore"
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_MODEL: str = "nvidia/nemotron-3.5-lightning:free"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    LLM_PROVIDER: str = "groq"
    LLM_FALLBACK_PROVIDER: str = "gemini"
    HF_TOKEN: str | None = None
    HF_ASR_MODEL: str = "snapwre/hohe-asr-amharic"
    GROQ_STT_MODEL: str = "whisper-large-v3"
    STT_PROVIDER: str = "gemini"
    STT_FALLBACK_PROVIDER: str = "none"
    TTS_PROVIDER: str = "edge_tts"
    TTS_FALLBACK_PROVIDER: str = "google"

    VOICE_LANGUAGE_DEFAULT: str = "am"
    VOICE_AMHARIC_ID: str = "Kore"
    VOICE_AFAAN_OROMO_ID: str = "Kore"
    VOICE_TTS_SPEED: float = 1.0
    VOICE_RATE: float = 1.0
    VOICE_MAX_RESPONSE_SENTENCES: int = 6
    GEMINI_RATE_LIMIT_RPM: int = 3
    GEMINI_TIMEOUT_SECONDS: float = 12.0
    GEMINI_STT_TIMEOUT_SECONDS: float = 8.0

    EMBEDDING_PROVIDER: str = "bge_m3"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    WEATHER_PROVIDER: str = "open_meteo"
    SMS_PROVIDER: str = "mock"

    # Telephony & VAD
    AUDIOSOCKET_HOST: str = "0.0.0.0"
    AUDIOSOCKET_PORT: int = 9092
    BARGE_IN_ENABLED: bool = False
    BARGE_IN_ENERGY_THRESHOLD: int = 550
    MAX_CALL_DURATION_SECONDS: int = 600
    INITIAL_SILENCE_TIMEOUT_SECONDS: int = 14
    SPEECH_SILENCE_TIMEOUT_MS: int = 2500
    VAD_ENERGY_THRESHOLD: int = 110
    SILENCE_REMINDER_TIMEOUT_SEC: float = 6.0
    MAX_SILENCE_REMINDERS: int = 2

    # DB & Redis
    DATABASE_URL: str = "postgresql+asyncpg://farmer:farmerpass@postgres:5432/hello_farmer"
    REDIS_URL: str = "redis://redis:6379/0"

    ENVIRONMENT: str = "development"
    ADMIN_API_KEY: str = "dev_admin_key_hello_farmer_2026"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Privacy & Recording Policy
    # Options: "transient_only" (default, zero audio files persisted, ephemeral VAD/STT buffer discarded)
    #          "notice_based_persistent" (lawful recording notice announced in greeting; files stored in cache/recordings with retention cleanup)
    #          "explicit_consent_persistent" (requires spoken opt-in before storing audio)
    RECORDING_POLICY: str = "transient_only"
    RECORDING_RETENTION_DAYS: int = 7
    SECRET_KEY: str = "hello_farmer_insecure_dev_secret_change_me_32chars!"
    PHONE_ENCRYPTION_KEY: str = "D7L2j61X01c90wPZq8c1BvK7x8k1D2M4N6P8Q0R2S4T="
    SALT_HASH_SECRET: str = "hello_farmer_caller_hash_salt_12345"
    CONCURRENCY_LIMIT: int = 2
    CALLER_RATE_LIMIT_PER_DAY: int = 10
    SIMILARITY_THRESHOLD: float = 0.65
    LOG_LEVEL: str = "INFO"

    def validate_production_secrets(self) -> None:
        """Fail fast if insecure development defaults are used in production."""
        if self.ENVIRONMENT.lower() == "production":
            insecure_defaults = [
                "hello_farmer_insecure_dev_secret_change_me_32chars!",
                "D7L2j61X01c90wPZq8c1BvK7x8k1D2M4N6P8Q0R2S4T=",
                "dev_admin_key_hello_farmer_2026",
            ]
            if self.SECRET_KEY in insecure_defaults or len(self.SECRET_KEY) < 32:
                raise ValueError("CRITICAL SECURITY ERROR: Insecure or short SECRET_KEY detected in production!")
            if self.PHONE_ENCRYPTION_KEY in insecure_defaults:
                raise ValueError("CRITICAL SECURITY ERROR: Default PHONE_ENCRYPTION_KEY detected in production!")
            if self.ADMIN_API_KEY in insecure_defaults or not self.ADMIN_API_KEY.strip():
                raise ValueError("CRITICAL SECURITY ERROR: Default ADMIN_API_KEY detected in production!")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


def load_yaml_config(path: str = "config.yaml") -> dict[str, Any]:
    """Load configuration from config.yaml if present."""
    config_file = Path(path)
    if not config_file.exists():
        # Fallback to root or parent directory
        config_file = Path(__file__).resolve().parent.parent.parent / "config.yaml"

    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


settings = AppSettings()
if os.getenv("ALLOWED_ORIGINS"):
    settings.ALLOWED_ORIGINS = [orig.strip() for orig in os.getenv("ALLOWED_ORIGINS").split(",") if orig.strip()]
settings.validate_production_secrets()
# Configure STT provider and silence timeout
settings.STT_PROVIDER = os.getenv("STT_PROVIDER", "gemini")
settings.HF_ASR_MODEL = "snapwre/hohe-asr-amharic"
settings.GEMINI_STT_MODEL = "gemini-3.5-flash-lite"
settings.GEMINI_STT_TIMEOUT_SECONDS = float(os.getenv("GEMINI_STT_TIMEOUT_SECONDS", "8.0"))
if not settings.HF_TOKEN or not settings.HF_TOKEN.strip():
    settings.HF_TOKEN = os.getenv("HF_TOKEN")
settings.VAD_ENERGY_THRESHOLD = 150
settings.SPEECH_SILENCE_TIMEOUT_MS = 2000

yaml_config = load_yaml_config()
