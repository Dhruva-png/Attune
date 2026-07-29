from __future__ import annotations

import pytest
from attune.core.entities.session import Session, SessionStatus
from attune.core.exceptions import InvalidSessionStateError


def test_new_session_defaults_to_active() -> None:
    session = Session()
    assert session.status == SessionStatus.ACTIVE
    assert session.ended_at is None


def test_end_transitions_active_session_to_completed() -> None:
    session = Session()
    session.end()
    assert session.status == SessionStatus.COMPLETED
    assert session.ended_at is not None


def test_end_on_already_completed_session_raises() -> None:
    session = Session()
    session.end()
    with pytest.raises(InvalidSessionStateError):
        session.end()


def test_abort_transitions_active_session_to_aborted() -> None:
    session = Session()
    session.abort()
    assert session.status == SessionStatus.ABORTED
    assert session.ended_at is not None


def test_abort_on_completed_session_raises() -> None:
    session = Session()
    session.end()
    with pytest.raises(InvalidSessionStateError):
        session.abort()
