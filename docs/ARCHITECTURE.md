# Architecture

The current CLI passes a local file path to the Awpy adapter. The adapter reads
the header, reconstructed rounds, and event-derived scoreboard. Pydantic
validates the summary before the CLI sorts player rows and emits JSON. The
FastAPI app currently exposes health and OpenAPI endpoints.

The planned upload route will validate and stage the recording, then return a
match ID and processing status. A background worker will claim the job, parse
it outside the API process, and persist the match, participants, rounds and
events in PostgreSQL. Durable job status will support bounded retries and
idempotent processing. A privacy-conscious retention policy will cover raw
uploads and temporary files.

Analytics will derive metrics from persisted events. The web app will use
stable API contracts to display processing status, metrics and event evidence.
Coaching will consume server-side analytics and validate report references
against the match before presenting any observation.

Codex implements and verifies changes. The developer owns product decisions
and reviews evidence, architecture, and reproducible checks.
