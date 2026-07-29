# Development Roadmap

Per the spec's explicit methodology: incremental milestones, each verified and tested before the
next begins. No milestone starts application code before the previous one's tests pass.

| # | Milestone | Deliverables | Exit criteria |
|---|---|---|---|
| M0 | **Architecture & scaffolding** *(this milestone)* | Docs in `docs/architecture/`, full folder skeleton, `pyproject.toml`, config loading, structured logging, CI skeleton | Docs reviewed by user; `pip install -e .` succeeds; empty package imports cleanly |
| M1 | **Core domain + event bus** | `core/entities`, `core/events` (Event, EventType, EventBus), `core/interfaces` ports, DI container | Unit tests: publish/subscribe, confidence gating, ordering guarantees |
| M2 | **Camera + vision pipeline skeleton** | `vision/camera` (OpenCVCamera + MockCamera), frame buffer, preprocessing, `vision/pipeline.py` wiring with no-op models | Runs against MockCamera in CI (no real webcam needed); FPS governor tested; camera-disconnect test passes |
| M3 | **Pose, Face, Hands modules** | MediaPipe wrappers publishing landmark events | Unit tests with recorded frame fixtures; latency budget test (5–10 FPS) |
| M4 | **Object/phone detection** | YOLO/ONNX wrapper, `vision/tracking`, phone pickup/down state machine | Precision/recall sanity test on labeled fixture clips |
| M5 | **Behaviour engines** | `behaviour/focus`, `fatigue`, `posture`, `phone`, `breaks` — all event-driven | Each engine unit-tested in isolation via synthetic event streams |
| M6 | **Database + persistence** | SQLAlchemy models, Alembic migrations, repositories, EventBus→DB subscriber | Integration test: full session round-trips through SQLite |
| M7 | **Analytics engine** | Daily/weekly/monthly rollups, trends, timeline builder | Rollup correctness tests against seeded event fixtures |
| M8 | **FastAPI backend** | All endpoints in [06-api-specification.md](06-api-specification.md), WebSocket live-stats | OpenAPI snapshot test; endpoint integration tests via `httpx.AsyncClient` |
| M9 | **LLM provider abstraction + AI Coach** | `llm/provider.py` Protocol + 5 providers + `coach.py` | Contract tests per provider (mocked HTTP); coach insight includes confidence + evidence ids |
| M10 | **PySide6 dashboard** | Shell, Live/Timeline/Analytics/Coach/Settings views, theme, qasync integration | Manual QA pass against wireframes; app launches, connects to API, live-updates |
| M11 | **Exports & PDF reports** | CSV/JSON/PNG exporters, branded PDF report builder, Plotly chart sharing between dashboard & reports | Generated PDF opens correctly, matches report spec sections |
| M12 | **Demo Mode + marketing assets** | Synthetic session generator, scripted scenarios, `scripts/generate_marketing_assets.py` | Demo mode populates a full week of realistic analytics without a webcam |
| M13 | **Testing & performance hardening** | Fill gaps: low-light tests, camera-disconnect edge cases, performance/perf budget tests, coverage pass | CI green across unit/integration/performance suites |
| M14 | **Docs, README, GitHub polish** | Professional README, screenshots, issue/PR templates, LICENSE, CONTRIBUTING | Repo readable end-to-end by a new contributor with no prior context |

## Sequencing rationale

- M1–M4 build the read side of the vision pipeline in isolation, testable without a real webcam
  (MockCamera + recorded fixtures) — this is what lets CV work proceed without flaking on
  hardware-dependent tests.
- M5 (behaviour) only depends on the `Event` contract from M1, so it can start once M1 lands even
  if M2–M4 are still in progress, as long as fixtures produce spec-shaped events.
- M6–M8 (persistence, analytics, API) form the backend spine and are the first point where the
  system is externally usable (e.g. via `curl`/Swagger) even before the desktop UI exists.
- M9 (LLM/Coach) depends only on M6–M7 (needs events + rollups to reason over), not on the UI.
- M10 (dashboard) is deliberately late — it consumes the already-stable API from M8, so UI
  iteration doesn't churn against a moving backend contract.
- M12 (Demo Mode) is sequenced after the dashboard so generated synthetic sessions can actually be
  *seen* and used for screenshots/marketing, which is its whole purpose.
- M13–M14 close the loop on the spec's "production-ready repository" requirement.

## Immediate next step

M0 finishes with this document set plus the physical folder/package scaffolding and project
config (see companion changes in this milestone). M1 (core domain + event bus) is the first
milestone that writes real application logic, and is the natural place to resume.
