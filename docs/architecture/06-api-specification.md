# API Specification

FastAPI backend, mounted at `attune.api.main:create_app()`. Auto-generated OpenAPI docs at
`/docs` (Swagger) and `/redoc`. All responses are JSON; all timestamps are ISO-8601 UTC.

## Conventions

- Base path: `/api/v1`
- Auth: none for v1 (local-only desktop app, API bound to `127.0.0.1`); a bearer-token local
  secret is generated at first run and required for non-localhost binds (future remote-access
  roadmap item).
- Errors: RFC-7807-style `{ "detail": str, "code": str }` with standard HTTP status codes.
- Pagination: cursor-based (`?cursor=...&limit=...`) on list endpoints.

## Endpoints

### `POST /api/v1/start-session`
Starts a new observation session (spins up camera + vision pipeline).

Request:
```json
{ "camera_index": 0, "confidence_threshold": 0.6 }
```
Response `201`:
```json
{ "session_id": "uuid", "started_at": "2026-07-29T09:00:00Z", "status": "active" }
```

### `POST /api/v1/end-session`
Stops the active session, triggers analytics rollup.

Request: `{ "session_id": "uuid" }`
Response `200`:
```json
{ "session_id": "uuid", "ended_at": "...", "status": "completed",
  "focus_score_avg": 78.4, "posture_score_avg": 81.2, "fatigue_level_end": "normal" }
```

### `GET /api/v1/live-stats`
Current in-progress session snapshot (polling fallback).
Response `200`:
```json
{
  "session_id": "uuid", "elapsed_seconds": 5423,
  "focus_score": 82, "status": "focused",
  "fatigue_level": "normal", "posture": "good",
  "phone_activity": { "last_pickup": "...", "interactions_today": 4 },
  "breaks": { "count": 2, "total_seconds": 540, "longest_seconds": 360 }
}
```

### `WS /api/v1/live-stats/stream`
WebSocket push of every `Event` as it's published (see [05-event-schema.md](05-event-schema.md))
plus a `focus_score_updated` heartbeat every 2s. Used by the dashboard for real-time UI instead of
polling.

### `GET /api/v1/events`
Query params: `session_id`, `type`, `from`, `to`, `cursor`, `limit` (default 50, max 500).
Response `200`:
```json
{ "items": [ { "...Event fields..." } ], "next_cursor": "opaque-string-or-null" }
```

### `GET /api/v1/reports/daily?date=2026-07-29`
Response `200`:
```json
{
  "date": "2026-07-29", "avg_focus_score": 76.5, "avg_posture_score": 80.1,
  "distraction_count": 11, "break_count": 4, "longest_break_seconds": 620,
  "best_hours": ["09:30-11:15"], "worst_hours": ["14:00-14:45"],
  "timeline": [ { "time": "09:00", "label": "Started", "event_type": "session_started" } ]
}
```

### `GET /api/v1/reports/weekly?week_start=2026-07-27`
Same shape as daily, aggregated over 7 days, plus `daily_breakdown: [...]` array.

### `GET /api/v1/settings`
Returns the singleton settings row (see [04-database-schema.md](04-database-schema.md)),
API-key fields redacted to `"***configured***"` / `null`.

### `PUT /api/v1/settings`
Partial update (JSON merge patch semantics). Request body mirrors the `Settings` Pydantic model
(`camera`, `llm`, `privacy`, `notifications`, `performance`, `theme`). Response `200`: updated
settings (redacted).

### `POST /api/v1/export`
Request:
```json
{ "scope": "session" | "daily" | "weekly" | "monthly", "target_id": "uuid-or-date",
  "format": "pdf" | "csv" | "json" | "png" }
```
Response `202` (generation is async for PDF/large exports):
```json
{ "report_id": "uuid", "status": "processing" }
```
Poll `GET /api/v1/reports/{report_id}` → `{ "status": "ready", "download_url": "/api/v1/reports/{id}/download" }`.

### `GET /api/v1/coach/insights?session_id=uuid`
Returns AI Coach output for a session (or `?period=weekly` for a rollup):
```json
{
  "insights": [
    { "text": "You consistently lose focus within five minutes of checking your phone.",
      "confidence": 0.87,
      "evidence_event_ids": ["uuid1", "uuid2", "..."] }
  ],
  "generated_by": "provider:model", "generated_at": "..."
}
```
Every insight carries `confidence` and the underlying `evidence_event_ids` it references, per the
spec's "recommendations must reference actual collected data" and "every prediction must include
confidence" rules.

## OpenAPI generation

FastAPI auto-generates the schema from the Pydantic models in `api/schemas/`; no hand-maintained
OpenAPI YAML. CI runs a contract test that diffs the generated schema against a committed snapshot
(`docs/architecture/openapi.snapshot.json`) so breaking API changes are caught in review.
