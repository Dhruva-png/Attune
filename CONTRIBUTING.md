# Contributing to Attune

Thanks for considering a contribution. This document covers everything you need to get from a
fresh clone to an opened PR.

## Getting set up

```bash
git clone https://github.com/Dhruva-png/Attune.git
cd Attune
pip install -e ".[dev]"
cp .env.example .env
pytest
```

See the [README](README.md#quick-start) for platform-specific install notes (in particular a
Windows long-path workaround for the PyTorch dependency) and for how to run the app itself,
including [demo mode](README.md#try-it-without-a-webcam-demo-mode) if you don't want to test
against a real webcam.

## Project structure and architecture rules

Attune follows Clean Architecture with a strict dependency direction — read
[docs/architecture/01-overview.md](docs/architecture/01-overview.md) before making any change
that touches more than one layer. In short:

- `attune/core/` (domain) has **zero** third-party dependencies — no FastAPI, PySide6, OpenCV,
  MediaPipe, SQLAlchemy, or LLM SDKs. Only entities, value objects, and `typing.Protocol` ports.
- `attune/vision/`, `attune/behaviour/`, `attune/analytics/` communicate with everything
  downstream **only** through the event bus (`attune/core/events/bus.py`) — never direct
  imports of each other.
- `attune/dashboard/` never imports `attune/vision/`, `attune/database/`, or `attune/llm/`
  directly — it only talks to `attune/api/` over HTTP, via `attune/dashboard/api_client.py`.
- `attune/bootstrap.py` is the **only** file allowed to import across every layer — it's the
  composition root that wires concrete infrastructure into the domain ports at startup.

These rules are enforced in CI by [import-linter](https://import-linter.readthedocs.io/)
(contracts in `pyproject.toml` under `[tool.importlinter]`), not just left as convention — a PR
that violates layering will fail `lint-imports` locally and in CI before you even get to review.

See [docs/architecture/02-folder-structure.md](docs/architecture/02-folder-structure.md) for
where each concern lives, and [docs/architecture/08-roadmap.md](docs/architecture/08-roadmap.md)
for the milestone-by-milestone history of how the codebase got here — useful context for why
things are organized the way they are.

## Before opening a PR

Run the exact checks CI runs, in this order, and get all five green:

```bash
ruff check attune tests
mypy attune
lint-imports
pytest
pytest -m "performance or integration" --no-cov
```

- `ruff` — linting and import sorting (`attune/` and `tests/`)
- `mypy attune` — strict type checking (application code only; tests aren't type-checked)
- `lint-imports` — the architectural layering contracts described above
- `pytest` — the unit test suite with coverage (excludes `integration`/`performance`-marked
  tests, which need real model weights or take longer to run)
- `pytest -m "performance or integration"` — API/database integration tests and
  performance-budget tests (vision-model inference latency, analytics rollup throughput)

CI runs the identical commands (see `.github/workflows/ci.yml`) — if these five pass locally,
CI will pass.

## Updating the README screenshots

If a UI change affects what's shown in `docs/screenshots/`, regenerate them rather than editing
by hand:

```bash
python scripts/generate_marketing_assets.py
```

This seeds a throwaway demo database (your real one is untouched), launches the dashboard
against it, and re-captures all five views.

## Writing tests

- Unit tests mirror the `attune/` package layout under `tests/unit/`.
- Use `attune.vision.camera.mock_camera.MockCamera` (never a real webcam) for anything that
  needs a camera — CI has none.
- Prefer testing behaviour through the public API of a module rather than reaching into private
  attributes.
- New endpoints need an integration test in `tests/integration/` using the `api_client` /
  `api_container` fixtures from `tests/integration/conftest.py` — see any existing
  `test_api_*.py` file for the pattern.
- If you add or change an API endpoint, regenerate the OpenAPI snapshot test fixture:
  ```bash
  python -c "import json; from attune.api.main import create_app; print(json.dumps(create_app().openapi(), indent=2, sort_keys=True))" > docs/architecture/openapi.snapshot.json
  ```
  and review the diff — an unintentional schema change here is exactly what that test is meant
  to catch.

## Commit and PR conventions

- Keep commits focused; write commit messages that explain *why*, not just *what* (the diff
  already shows what changed).
- Reference the relevant architecture doc or roadmap milestone in your PR description if the
  change touches a specific subsystem.
- Update `docs/architecture/openapi.snapshot.json` (see above) and any relevant doc in
  `docs/architecture/` in the same PR as the code change it documents — not as a follow-up.

## Reporting bugs / requesting features

Use the issue templates — they'll prompt for the information needed to act on a report quickly
(repro steps, environment, expected vs. actual behaviour for bugs; motivation and proposed
approach for features).
