from __future__ import annotations

from pydantic import BaseModel

from attune.config.settings import (
    CameraSettings,
    LLMProviderName,
    LLMSettings,
    NotificationSettings,
    PerformanceSettings,
    PrivacySettings,
)


class SettingsResponse(BaseModel):
    camera: CameraSettings
    llm: LLMSettings
    privacy: PrivacySettings
    notifications: NotificationSettings
    performance: PerformanceSettings
    theme: str


class CameraSettingsUpdate(BaseModel):
    device_index: int | None = None
    fps: int | None = None
    inference_fps: int | None = None
    width: int | None = None
    height: int | None = None


class LLMSettingsUpdate(BaseModel):
    provider: LLMProviderName | None = None
    model: str | None = None


class PrivacySettingsUpdate(BaseModel):
    cloud_ai_enabled: bool | None = None
    debug_save_frames: bool | None = None
    data_retention_days: int | None = None


class NotificationSettingsUpdate(BaseModel):
    enabled: bool | None = None
    posture_alerts: bool | None = None
    break_reminders: bool | None = None
    idle_reminder_minutes: int | None = None


class PerformanceSettingsUpdate(BaseModel):
    confidence_threshold: float | None = None
    max_dropped_frame_ratio: float | None = None


class SettingsUpdateRequest(BaseModel):
    """Partial update — JSON merge-patch semantics, applied per-section by
    the settings router (undefined fields on a section leave the stored
    value untouched; omitted sections are left entirely alone).
    """

    camera: CameraSettingsUpdate | None = None
    llm: LLMSettingsUpdate | None = None
    privacy: PrivacySettingsUpdate | None = None
    notifications: NotificationSettingsUpdate | None = None
    performance: PerformanceSettingsUpdate | None = None
    theme: str | None = None
