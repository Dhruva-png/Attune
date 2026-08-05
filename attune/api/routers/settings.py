from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Depends

from attune.api.dependencies import get_settings_store
from attune.api.schemas.settings import SettingsResponse, SettingsUpdateRequest
from attune.config.settings import (
    CameraSettings,
    LLMSettings,
    NotificationSettings,
    PerformanceSettings,
    PrivacySettings,
)
from attune.core.interfaces.repository import ISettingsStore

router = APIRouter(tags=["settings"])

_SECTION_MODELS = {
    "camera": CameraSettings,
    "llm": LLMSettings,
    "privacy": PrivacySettings,
    "notifications": NotificationSettings,
    "performance": PerformanceSettings,
}


def _section(stored: dict[str, object], key: str) -> dict[str, Any]:
    """`ISettingsStore.load()` returns `dict[str, object]` since it's a
    generic key-value contract; every section value is actually a JSON
    object in practice (SettingsModel's JSON columns), so this narrows it
    back to something `**`-unpackable into the section's Pydantic model.
    """
    return cast(dict[str, Any], stored.get(key, {}))


async def _load_settings_response(store: ISettingsStore) -> SettingsResponse:
    stored = await store.load()
    return SettingsResponse(
        camera=CameraSettings(**_section(stored, "camera")),
        llm=LLMSettings(**_section(stored, "llm")),
        privacy=PrivacySettings(**_section(stored, "privacy")),
        notifications=NotificationSettings(**_section(stored, "notifications")),
        performance=PerformanceSettings(**_section(stored, "performance")),
        theme=cast(str, stored.get("theme", "dark")),
    )


@router.get("/settings")
async def get_settings(
    store: ISettingsStore = Depends(get_settings_store),
) -> SettingsResponse:
    return await _load_settings_response(store)


@router.put("/settings")
async def update_settings(
    request: SettingsUpdateRequest,
    store: ISettingsStore = Depends(get_settings_store),
) -> SettingsResponse:
    stored = await store.load()
    updates: dict[str, object] = {}

    for section_name, model in _SECTION_MODELS.items():
        section_update = getattr(request, section_name)
        if section_update is None:
            continue
        current = model(**_section(stored, section_name)).model_dump()
        current.update(section_update.model_dump(exclude_none=True))
        updates[section_name] = current

    if request.theme is not None:
        updates["theme"] = request.theme

    await store.save(updates)
    return await _load_settings_response(store)
