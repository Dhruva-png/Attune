from __future__ import annotations


class AttuneError(Exception):
    """Base class for all Attune domain errors."""


class InvalidSessionStateError(AttuneError):
    """Raised when a Session transition is attempted from an invalid state."""
