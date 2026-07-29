from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderName(StrEnum):
    OPENAI = "openai"
    GEMINI = "gemini"
    CLAUDE = "claude"
    GROQ = "groq"
    OLLAMA = "ollama"


class CameraSettings(BaseModel):
    device_index: int = 0
    fps: int = 30
    inference_fps: int = 8
    width: int = 1280
    height: int = 720


class LLMSettings(BaseModel):
    provider: LLMProviderName = LLMProviderName.OLLAMA
    model: str = "llama3.1"
    # API keys are read directly from provider-specific env vars at call time
    # (OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY) — never stored here.


class PrivacySettings(BaseModel):
    cloud_ai_enabled: bool = False
    debug_save_frames: bool = False
    data_retention_days: int = 90


class NotificationSettings(BaseModel):
    enabled: bool = True
    posture_alerts: bool = True
    break_reminders: bool = True
    idle_reminder_minutes: int = 45


class PerformanceSettings(BaseModel):
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    max_dropped_frame_ratio: float = Field(default=0.2, ge=0.0, le=1.0)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ATTUNE_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Attune"
    debug: bool = False
    theme: str = "dark"

    api_host: str = "127.0.0.1"
    api_port: int = 8420

    database_url: str = "sqlite+aiosqlite:///./attune.db"
    data_dir: Path = Path("./data")

    log_level: str = "INFO"
    log_json: bool = False

    camera: CameraSettings = CameraSettings()
    llm: LLMSettings = LLMSettings()
    privacy: PrivacySettings = PrivacySettings()
    notifications: NotificationSettings = NotificationSettings()
    performance: PerformanceSettings = PerformanceSettings()


@lru_cache
def get_settings() -> Settings:
    return Settings()
