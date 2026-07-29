from __future__ import annotations

from typing import Protocol


class ILLMProvider(Protocol):
    name: str

    async def complete(self, prompt: str, *, system: str | None = None) -> str: ...
