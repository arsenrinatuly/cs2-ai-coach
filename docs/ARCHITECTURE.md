# Architecture

The current CLI passes a local file path to the Awpy adapter. The adapter reads
the header, reconstructed rounds, and event-derived scoreboard. Pydantic
validates the summary before the CLI sorts player rows and emits JSON. The
FastAPI app currently exposes health and OpenAPI endpoints.

The upload route streams recordings to a spool, then returns a match ID.
A separate process claims queued jobs with PostgreSQL row locks. It extracts
the match header, participants, rounds, and death events, then commits those
records together. Duplicate file hashes resolve to the same match ID.

Analytics derive round-bounded counters and opening deaths. The Next.js app
polls status and presents event references. The coaching tool reads verified
opening deaths. Its output is limited to evidence IDs and review focus, and
the server revalidates references before rendering a factual observation.

The Vercel Hobby sample is a static, de-identified export of one parsed match.
Local operation runs the upload API, worker, database, and web interface.

Codex implements and verifies changes. The developer owns product decisions
and reviews evidence, architecture, and reproducible checks.
