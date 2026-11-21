# CS2 AI Coach

Inspect a CS2 Source 2 demo, select a player, and review opening deaths backed
by recorded round and event references.

[Open the public sample match](https://cs2-ai-coach-demo.vercel.app).
It is an anonymized Valve recording. The full upload and worker workflow runs
locally. A configured model can prioritize evidence. The default review notes
use deterministic rules.

## Run locally

Use Docker Compose, or run PostgreSQL 17, Python 3.12 with uv, and Node.js 24
locally. See [operations](docs/OPERATIONS.md) for both paths and rollback.

```sh
cd backend
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

```sh
cd frontend
npm ci
npm run typecheck
npm run build
```

## How it works

1. FastAPI validates and streams the file into a local spool.
2. A separate Awpy worker claims the queued match and stores round and death
   events in PostgreSQL.
3. Deterministic analytics attribute kills, deaths, assists and first deaths
   to recorded players. Next.js displays the result and event references.
4. The optional Pydantic AI coach selects only verified evidence. The server
   renders factual text and separates it from suggested review actions.

The [backend guide](backend/README.md) documents parser semantics and the
public fixture. See the [PRD](docs/PRD.md), [architecture](docs/ARCHITECTURE.md),
[technical case study](docs/CASE-STUDY.md), and [evaluation report](docs/COACH-EVAL.md).
