from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


class Container:
    """Minimal service locator resolved once at startup by bootstrap.py.

    Registrations are keyed by the domain Protocol (port), never by the concrete
    infrastructure class, so callers depend only on attune.core.interfaces.
    """

    def __init__(self) -> None:
        self._singletons: dict[type, object] = {}

    def register(self, interface: type[T], instance: T) -> None:
        self._singletons[interface] = instance

    def resolve(self, interface: type[T]) -> T:
        try:
            return self._singletons[interface]  # type: ignore[return-value]
        except KeyError as exc:
            raise LookupError(f"No implementation registered for {interface!r}") from exc
