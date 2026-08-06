from __future__ import annotations

import json
from pathlib import Path

import pytest
from attune.api.main import create_app

SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "architecture" / "openapi.snapshot.json"
)


@pytest.mark.integration
def test_openapi_schema_matches_committed_snapshot() -> None:
    """Diffs the live-generated schema against the committed snapshot, per
    docs/architecture/06-api-specification.md's "OpenAPI generation" note.
    An intentional API change means regenerating the snapshot (see the
    generation snippet in that doc) and reviewing the diff, not editing it
    by hand.
    """
    current = create_app().openapi()
    committed = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert current == committed, (
        "OpenAPI schema has drifted from docs/architecture/openapi.snapshot.json — "
        "regenerate the snapshot if this change was intentional."
    )


@pytest.mark.integration
def test_openapi_schema_documents_every_spec_endpoint() -> None:
    schema = create_app().openapi()
    paths = schema["paths"]

    for path in (
        "/api/v1/start-session",
        "/api/v1/end-session",
        "/api/v1/live-stats",
        "/api/v1/events",
        "/api/v1/reports/daily",
        "/api/v1/reports/weekly",
        "/api/v1/settings",
        "/api/v1/export",
        "/api/v1/coach/insights",
    ):
        assert path in paths, f"{path} missing from generated OpenAPI schema"
