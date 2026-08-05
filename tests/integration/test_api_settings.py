from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_settings_returns_defaults_when_nothing_stored(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["theme"] == "dark"
    assert body["camera"]["fps"] == 30
    assert body["llm"]["provider"] == "ollama"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_put_settings_updates_only_specified_fields(api_client: AsyncClient) -> None:
    response = await api_client.put(
        "/api/v1/settings", json={"camera": {"fps": 15}, "theme": "light"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["theme"] == "light"
    assert body["camera"]["fps"] == 15
    assert body["camera"]["device_index"] == 0  # untouched field keeps its default


@pytest.mark.integration
@pytest.mark.asyncio
async def test_successive_partial_updates_do_not_clobber_each_other(
    api_client: AsyncClient,
) -> None:
    await api_client.put("/api/v1/settings", json={"camera": {"fps": 15}})
    second = await api_client.put("/api/v1/settings", json={"camera": {"device_index": 1}})

    body = second.json()
    assert body["camera"]["fps"] == 15  # preserved from the first update
    assert body["camera"]["device_index"] == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_put_settings_updates_nested_llm_provider(api_client: AsyncClient) -> None:
    response = await api_client.put(
        "/api/v1/settings", json={"llm": {"provider": "openai", "model": "gpt-4o"}}
    )

    body = response.json()
    assert body["llm"]["provider"] == "openai"
    assert body["llm"]["model"] == "gpt-4o"
