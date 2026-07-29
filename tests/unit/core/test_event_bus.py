from __future__ import annotations

from uuid import uuid4

import pytest
from attune.core.events.bus import EventBus
from attune.core.events.schema import Event, EventType


def make_event(event_type: EventType = EventType.SESSION_STARTED, confidence: float = 0.9) -> Event:
    return Event(
        session_id=uuid4(),
        type=event_type,
        confidence=confidence,
        source_module="test",
    )


@pytest.mark.asyncio
async def test_subscribe_and_publish_delivers_to_matching_handler() -> None:
    bus = EventBus()
    received: list[Event] = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe(EventType.PHONE_PICKUP, handler)
    event = make_event(EventType.PHONE_PICKUP)
    await bus.publish(event)

    assert received == [event]


@pytest.mark.asyncio
async def test_publish_does_not_deliver_to_non_matching_subscriber() -> None:
    bus = EventBus()
    received: list[Event] = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe(EventType.PHONE_PICKUP, handler)
    await bus.publish(make_event(EventType.LEFT_DESK))

    assert received == []


@pytest.mark.asyncio
async def test_subscribe_all_receives_every_event_type() -> None:
    bus = EventBus()
    received: list[EventType] = []

    async def wildcard(event: Event) -> None:
        received.append(event.type)

    bus.subscribe_all(wildcard)
    await bus.publish(make_event(EventType.YAWN))
    await bus.publish(make_event(EventType.GOOD_POSTURE))

    assert received == [EventType.YAWN, EventType.GOOD_POSTURE]


@pytest.mark.asyncio
async def test_multiple_handlers_for_same_event_all_run() -> None:
    bus = EventBus()
    calls: list[str] = []

    async def handler_a(event: Event) -> None:
        calls.append("a")

    async def handler_b(event: Event) -> None:
        calls.append("b")

    bus.subscribe(EventType.COFFEE_DRINK, handler_a)
    bus.subscribe(EventType.COFFEE_DRINK, handler_b)
    await bus.publish(make_event(EventType.COFFEE_DRINK))

    assert set(calls) == {"a", "b"}


@pytest.mark.asyncio
async def test_one_failing_handler_does_not_block_others() -> None:
    bus = EventBus()
    received: list[str] = []

    async def failing_handler(event: Event) -> None:
        raise RuntimeError("boom")

    async def ok_handler(event: Event) -> None:
        received.append("ok")

    bus.subscribe(EventType.FACE_TOUCH, failing_handler)
    bus.subscribe(EventType.FACE_TOUCH, ok_handler)

    await bus.publish(make_event(EventType.FACE_TOUCH))  # must not raise

    assert received == ["ok"]


@pytest.mark.asyncio
async def test_unsubscribe_stops_future_delivery() -> None:
    bus = EventBus()
    received: list[Event] = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe(EventType.LOOKED_AWAY, handler)
    bus.unsubscribe(EventType.LOOKED_AWAY, handler)
    await bus.publish(make_event(EventType.LOOKED_AWAY))

    assert received == []


@pytest.mark.asyncio
async def test_publish_preserves_ordering_for_sequential_awaits() -> None:
    bus = EventBus()
    received: list[EventType] = []

    async def handler(event: Event) -> None:
        received.append(event.type)

    ordered_types = (
        EventType.SESSION_STARTED,
        EventType.LOOKING_AT_SCREEN,
        EventType.SESSION_ENDED,
    )
    bus.subscribe_all(handler)
    for event_type in ordered_types:
        await bus.publish(make_event(event_type))

    assert received == list(ordered_types)
