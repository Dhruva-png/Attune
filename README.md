# Attune

**Learn your habits. Improve your focus.**

Attune is a privacy-first desktop productivity coach that understands how you work using
*only* your laptop's built-in webcam — no screen recording, no keyboard logging, no browser
extensions, no wearables. Everything is inferred through on-device computer vision and
behavioural analysis; cloud AI is entirely opt-in.

> **Status: early development (Milestone 0 — architecture & scaffolding).** The application is
> not yet runnable. This README will be replaced with the full product README (screenshots,
> install instructions, usage guide) once the desktop app and API are functional — see the
> roadmap below.

## Architecture

Full design docs live in [`docs/architecture/`](docs/architecture/):

1. [Overview & architectural style](docs/architecture/01-overview.md)
2. [Folder structure](docs/architecture/02-folder-structure.md)
3. [Module dependency diagram](docs/architecture/03-module-dependencies.md)
4. [Database schema](docs/architecture/04-database-schema.md)
5. [Event schema](docs/architecture/05-event-schema.md)
6. [API specification](docs/architecture/06-api-specification.md)
7. [UI wireframes](docs/architecture/07-ui-wireframes.md)
8. [Development roadmap](docs/architecture/08-roadmap.md)

## Tech stack

Python 3.12 · FastAPI · Pydantic · SQLAlchemy/SQLite · OpenCV · MediaPipe · Ultralytics YOLO ·
ONNX Runtime · PySide6 · Plotly · pluggable LLM providers (OpenAI, Gemini, Claude, Groq, Ollama).

## Development

```bash
pip install -e ".[dev]"
cp .env.example .env
pytest
```

> **Windows:** `pip install -e ".[dev]"` can fail with `WinError 206: filename too long` while
> installing PyTorch (an `ultralytics` dependency) unless
> [long path support is enabled](https://learn.microsoft.com/windows/win32/fileio/maximum-file-path-limitation#enable-long-paths-in-windows-10-version-1607-and-later).
> Workaround without changing system settings: install a CPU-only build first —
> `pip install torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cpu`
> — then run the command above.

The fast default `pytest` run covers unit tests only. Vision-model tests that need real model
weights (downloaded on first use into gitignored `data/models/`) are marked `integration` /
`performance` and run separately:

```bash
pytest -m "performance or integration"
```

See [the roadmap](docs/architecture/08-roadmap.md) for the milestone currently in progress.

## License

[MIT](LICENSE)
