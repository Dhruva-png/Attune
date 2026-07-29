# Folder Structure

Layered per Clean Architecture (see [01-overview.md](01-overview.md)) while preserving every
module name called out in the product spec.

```
attune/
├── attune/                        # Application package (importable, pip-installable)
│   ├── __init__.py
│   ├── bootstrap.py                # Composition root: wires infra -> ports -> services
│   ├── container.py                # Minimal DI container
│   │
│   ├── core/                       # DOMAIN — zero third-party framework deps
│   │   ├── entities/                # Session, FocusScore, PostureMetric, FatigueState, ...
│   │   ├── value_objects/           # Confidence, TimeRange, Landmark, BoundingBox
│   │   ├── events/                  # Event, EventType, EventBus (pub/sub), EventBus port
│   │   ├── interfaces/              # Protocols: ICamera, IPoseModel, IFaceModel, IHandModel,
│   │   │                            #   IObjectModel, IEventRepository, ISessionRepository,
│   │   │                            #   ILLMProvider, ISettingsStore
│   │   └── exceptions.py
│   │
│   ├── vision/                      # INFRASTRUCTURE — the CV pipeline
│   │   ├── camera/                  # OpenCVCamera, MockCamera, frame buffer, FPS governor
│   │   ├── preprocessing/           # resize, normalize, color convert, denoise
│   │   ├── pose/                    # MediaPipe Pose wrapper -> PoseLandmarks
│   │   ├── face/                    # MediaPipe Face Mesh -> FaceLandmarks, gaze, blink, yawn
│   │   ├── hands/                   # MediaPipe Hands -> HandLandmarks
│   │   ├── objects/                 # YOLO/ONNX object + phone detector
│   │   ├── tracking/                # Lightweight IOU/centroid tracker for object persistence
│   │   └── pipeline.py              # Orchestrates camera -> preprocessing -> models -> events
│   │
│   ├── behaviour/                   # APPLICATION — turns landmarks/detections into events
│   │   ├── focus/                   # FocusEngine: 0-100 continuous score
│   │   ├── fatigue/                 # FatigueEngine: Fresh/Normal/Tired/Very Tired
│   │   ├── posture/                 # PostureAnalyzer: neck angle, shoulder alignment, slump
│   │   ├── phone/                   # PhoneDetector: pickup/usage/put-down + glance vs. extended
│   │   ├── breaks/                  # AwayDetector: left desk / returned / break stats
│   │   └── confidence.py            # Shared confidence-gating utility (suppresses low-conf events)
│   │
│   ├── analytics/                   # APPLICATION — aggregation over events
│   │   ├── engine.py                # Rollups: daily / weekly / monthly
│   │   ├── trends.py                # Best/worst hours, focus & posture trend lines
│   │   └── timeline.py              # Chronological event timeline builder
│   │
│   ├── database/                    # INFRASTRUCTURE — persistence
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   ├── session.py               # Engine/session factory (async SQLAlchemy)
│   │   ├── repositories/            # EventRepository, SessionRepository, SettingsRepository
│   │   └── migrations/              # Alembic migrations
│   │
│   ├── llm/                         # INFRASTRUCTURE — provider abstraction + AI Coach
│   │   ├── provider.py              # LLMProvider Protocol
│   │   ├── providers/               # OpenAIProvider, GeminiProvider, ClaudeProvider,
│   │   │                            #   GroqProvider, OllamaProvider
│   │   ├── factory.py               # Reads config -> instantiates configured provider
│   │   └── coach.py                 # AI Coach use case: events -> evidence-backed insights
│   │
│   ├── reports/                     # INFRASTRUCTURE — export & PDF generation
│   │   ├── pdf_report.py            # Branded PDF report builder
│   │   ├── csv_export.py
│   │   ├── json_export.py
│   │   └── charts.py                # Plotly figure builders shared by dashboard + reports
│   │
│   ├── api/                         # PRESENTATION — FastAPI backend
│   │   ├── main.py                  # App factory, OpenAPI metadata
│   │   ├── routers/                 # sessions, live_stats, events, reports, settings, export
│   │   ├── schemas/                 # Pydantic request/response models
│   │   └── dependencies.py          # FastAPI DI (pulls from attune.container)
│   │
│   ├── dashboard/                   # PRESENTATION — PySide6 desktop UI
│   │   ├── app.py                   # QApplication entry point, qasync loop integration
│   │   ├── main_window.py
│   │   ├── views/                   # live, timeline, analytics, coach, settings
│   │   ├── widgets/                 # gauges, cards, charts, camera preview
│   │   ├── theme/                   # dark glassmorphism QSS + design tokens
│   │   └── viewmodels/              # Qt-facing state, subscribes to EventBus
│   │
│   ├── demo/                        # Synthetic session generator (LinkedIn Demo Mode)
│   │   ├── generator.py
│   │   └── scenarios/                # Preset "great focus day", "distracted day", etc.
│   │
│   ├── config/                      # Settings, env loading, logging config
│   │   ├── settings.py              # Pydantic Settings (env-var driven)
│   │   └── logging.py               # Structured logging setup
│   │
│   └── assets/                      # Icons, splash screen, fonts, brand colors
│
├── tests/
│   ├── unit/                        # Per-module, mirrors attune/ package layout
│   ├── integration/                 # Pipeline end-to-end with MockCamera
│   ├── performance/                 # FPS / latency budget tests
│   └── fixtures/                    # Recorded frame sequences, synthetic events
│
├── docs/
│   ├── architecture/                # This document set
│   ├── screenshots/
│   └── roadmap.md
│
├── scripts/                         # dev scripts: seed_demo_data.py, generate_marketing_assets.py
├── .github/                         # issue templates, PR template, workflows
├── pyproject.toml
├── requirements.txt
├── .env.example
├── README.md
└── LICENSE
```

## Naming rule

Every top-level spec module (`camera`, `pose`, `face`, `hands`, `objects`, `tracking`, `events`,
`analytics`, `database`, `api`, `reports`, `dashboard`, `llm`) exists as a real package. They are
grouped under `vision/` where the spec's vision-pipeline stages live together, since that mirrors
the actual data flow and keeps camera/pose/face/hands/objects/tracking importable as
`attune.vision.<name>` without one giant flat namespace.
