"""Typed configuration management for Hello Farmer."""
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    # Provider keys & defaults
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "qwen/qwen3.8-27b"
    GEMINI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_MODEL: str = "nvidia/nemotron-3.5-lightning:free"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    STT_PROVIDER: str = "mms"
    TTS_PROVIDER: str = "edge_tts"
    EMBEDDING_PROVIDER: str = "bge_m3"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    WEATHER_PROVIDER: str = "open_meteo"
    SMS_PROVIDER: str = "mock"

    # Telephony
    AUDIOSOCKET_HOST: str = "0.0.0.0"
    AUDIOSOCKET_PORT: int = 9092
    BARGE_IN_ENABLED: bool = False
    MAX_CALL_DURATION_SECONDS: int = 600
    INITIAL_SILENCE_TIMEOUT_SECONDS: int = 10
    SPEECH_SILENCE_TIMEOUT_MS: int = 800
    VAD_ENERGY_THRESHOLD: int = 700

    # DB & Redis
    DATABASE_URL: str = "postgresql+asyncpg://farmer:farmerpass@postgres:5432/hello_farmer"
    REDIS_URL: str = "redis://redis:6379/0"

    # Privacy & Limits
    SECRET_KEY: str = "hello_farmer_insecure_dev_secret_change_me_32chars!"
    PHONE_ENCRYPTION_KEY: str = "D7L2j61X01c90wPZq8c1BvK7x8k1D2M4N6P8Q0R2S4T="
    SALT_HASH_SECRET: str = "hello_farmer_caller_hash_salt_12345"
    CONCURRENCY_LIMIT: int = 2
    CALLER_RATE_LIMIT_PER_DAY: int = 10
    SIMILARITY_THRESHOLD: float = 0.65
    LOG_LEVEL: str = "INFO"

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
yaml_config = load_yaml_config()
