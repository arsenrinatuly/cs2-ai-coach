# Local operation and deployment

## Run the full product

With PostgreSQL 17, uv, and Node.js 24 installed, create a development database
and set `DATABASE_URL` in the API and worker terminal environments. Use a
SQLAlchemy URL such as `postgresql+psycopg:///cs2_coach`.

```sh
cd backend
uv sync --locked
uv run alembic upgrade head
uv run uvicorn backend.api:app --no-access-log
```

In a second terminal with the same database and spool configuration:

```sh
cd backend
uv run python -m backend.ingestion
```

In a third terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open <http://localhost:3000>. The API and its OpenAPI page are available at
<http://127.0.0.1:8000/docs>. Use `NEXT_PUBLIC_API_URL` to point the browser at
a different API. Set `WEB_ORIGINS` to a comma-separated list of intended web origins.

### Docker Compose

Set `POSTGRES_PASSWORD` and `DATABASE_URL` in your environment or an ignored
root `.env`. Use database host `db` in the Compose URL. Then run
`docker compose up --build`. The migration service runs before the API and
worker. Both services share the private spool volume.

Restarting a worker preserves queued jobs. Workers claim rows using
`FOR UPDATE SKIP LOCKED`. One worker handles one job at a time. A transient
file read retries up to two times with a persisted delay. Database connection
errors roll back the job and reconnect. Terminal spool files are removed
after commit, with a periodic cleanup pass for terminal matches. Files left
before a transaction commits can be removed manually after stopping uploads
and reconciling the spool with the database.

To roll back code, redeploy the previous tested image or checkout. Restore
from a backup when a schema change cannot be reversed without data loss.
The compose database volume is persistent. Keep deployment rollback separate
from deleting persisted data.

## Model configuration

Set `COACH_MODEL` to a Pydantic AI model identifier and supply the matching
server-side credentials. For OpenAI, use `OPENAI_API_KEY` in the API environment.
Unset `COACH_MODEL` to run deterministic notes. Usage logs include elapsed time,
input/output token counts and an estimated USD cost when both
`COACH_INPUT_USD_PER_MILLION` and `COACH_OUTPUT_USD_PER_MILLION` are configured.
Log metadata excludes prompts, playback data, and credentials.

## Vercel Hobby sample deployment

The [public sample](https://cs2-ai-coach-demo.vercel.app) is a static export.
Vercel Functions have request-body limits below the 84 MB fixture. The export
uses real analytics with player names and Steam IDs replaced by local aliases.
It has no upload endpoint, resident parser, database, or model calls.

```sh
cd backend
uv run python scripts/export_public_demo.py \
  ../demos/valve-de_mirage-472514809.dem ../frontend/public/demo-sample.json
cd ../frontend
npm ci
NEXT_PUBLIC_DEMO_MODE=1 npm run build
```

Stage the resulting `out/` as `public/` in an isolated deployment directory.
Use a Vercel static project with no framework or build command and output
directory `public`. Deploy with the CLI. For a static rollback, redeploy the
previous verified production build in the Vercel dashboard. Active hosting uses
the Hobby account verified during deployment.

Run the full stack behind a private access boundary for a shared test.
The default local services bind through loopback in Compose.
