# CS2 AI Coach

CS2 AI Coach is a demo-analysis project for Counter-Strike 2. It currently
inspects local Source 2 recordings and exposes an API health endpoint.

## Run locally

Install uv, then run the following from the repository root.

```sh
cd backend
uv sync --locked
uv run uvicorn backend.api:app --reload
```

Open <http://127.0.0.1:8000/docs> for the API reference. In a separate terminal,
run these commands from the repository root.

```sh
cd backend
uv run pytest
uv run ruff check .
```

See the [backend guide](backend/README.md) for inspecting a real demo.
The [PRD](docs/PRD.md), [architecture](docs/ARCHITECTURE.md), and
[ADR-001](docs/ADR-001.md) describe the MVP and its design.
