# Backend

## Inspect one CS2 demo on macOS

From the repository root, put an extracted CS2 Source 2 recording in `demos/`.
Keep downloaded archives in the same directory. Git ignores that directory, raw
`.dem` files, and common `.dem.*` archive formats.

```sh
cd backend
uv sync --locked
uv run inspect-demo ../demos/valve-de_mirage-472514809.dem
uv run pytest
uv run ruff check .
```

The inspector also exposes `backend.demo_inspection.inspect_demo(Path(...))`
for Python callers. The CLI sorts player rows by Steam ID, name, kills, and deaths for stable output.
The CLI prints JSON to stdout and reports invalid, unreadable,
or unsupported inputs to stderr with a nonzero exit code.

## ARS-6 verification

The [Awpy fixtures manifest](https://github.com/pnxenopoulos/awpy-fixtures/blob/main/manifest.json)
lists a public Valve matchmaking recording for
[match 472514809](https://csstats.gg/match/472514809).
[Download the fixture](https://github.com/pnxenopoulos/awpy-fixtures/releases/download/valve-de_mirage-472514809/valve-de_mirage-472514809.dem)
as `demos/valve-de_mirage-472514809.dem`.
Verify it with `shasum -a 256 demos/valve-de_mirage-472514809.dem` from the repository root.
The expected SHA-256 is
`2e0a4f9aa257af9d8e2c934dcbd6cb6a8c48483c264904ecc27218dd7d360506`.

On Apple Silicon macOS with Python 3.12.16 and Awpy 3.3.0, the inspector
read 84,203,211 bytes and returned `de_mirage`, 13 rounds, and 10 scoreboard
rows with Steam IDs. Both player K/D pairs in the manifest matched (27/1 and
4/13).

- The map comes from the demo header. The round count is the number of rows
  Awpy reconstructs. The inspector includes knife rounds in both the round count
  and the scoreboard if they occur.
- Awpy derives K/D from recorded events. Enemy kills exclude suicides and team
  kills. Deaths can include world or self-inflicted deaths, so the totals can
  differ and external scoreboards may use different rules.
- Player rows come from Awpy's scoreboard. Display names can repeat. Steam IDs
  are serialized as strings to preserve 64-bit precision in JavaScript.
  Missing player fields and map names are represented as JSON `null`.
- This verification covers one Valve recording. Other demo providers and
  recordings with unusual round boundaries require separate verification.

See [Awpy's datasets](https://awpy.readthedocs.io/en/latest/datasets.html)
and [metric definitions](https://awpy.readthedocs.io/en/latest/reference.html).

## Local upload and worker

Create a local PostgreSQL database and set `DATABASE_URL` to its SQLAlchemy
connection URL (for example, `postgresql+psycopg:///cs2_coach`). From this
directory run `uv run alembic upgrade head`. Start the API with
`uv run uvicorn backend.api:app` and the worker in a second terminal with
`uv run python -m backend.ingestion`.

```sh
curl -X POST --data-binary @../demos/valve-de_mirage-472514809.dem \
  'http://127.0.0.1:8000/matches?filename=valve-de_mirage-472514809.dem'
```

Poll the returned `status_url` for `queued`, `ready`, or `failed`. Uploads
are limited to 512 MiB and deduplicated by file SHA-256. The API and worker
must share the private `DEMO_SPOOL_DIR` (default `.demo-spool`). The
worker removes staged bytes after the result commits. Interrupted processes
can leave orphan files. Automatic cleanup and retry policies are tracked
under ARS-22. Run the storage tests against a migrated, disposable PostgreSQL
database by setting `TEST_DATABASE_URL`.

For a ready match, `GET /matches/{id}/analytics` returns review metrics.
Events belong to the latest round whose start is at or before the event tick,
provided the event is within that round's recorded official end (or end
when no official end is available). Review metrics exclude knife rounds.
Kills count deaths credited to an opposing-side attacker. Deaths include
resolved victims of suicides or world damage. Assists count the recorded
assister, excluding the attacker and victim, without inferring additional flash
assists. The first death uses tick order and then source event ordinal.
Unresolved first victims produce no player attribution for that round.

Round participation here is the set of rounds in which a player is observed
as an attacker, victim, or assister. Quiet rounds, disconnects, and missing
events mean this cannot establish full round attendance. ADR and KAST are
outside this endpoint's contract.

In the public Mirage recording, the last round ends at tick 40132. A world
death occurs at tick 40220. Awpy's CLI scoreboard includes that death (27/1),
while the round-bounded review endpoint reports 27/0 for the same player.
Both workflows match 4/13 for the other manifest player. Set
`TEST_DEMO_PATH=../demos/valve-de_mirage-472514809.dem` alongside
`TEST_DATABASE_URL` to reproduce the ingestion and analytics checks.
