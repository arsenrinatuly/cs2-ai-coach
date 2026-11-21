# CS2 AI Coach technical case study

## Goal

Help players turn a recorded match into a short list of rounds to review.
The system must be able to show the match evidence behind each factual claim.

## Implementation

A Next.js web app uploads recordings to a FastAPI backend. A separate
PostgreSQL-backed worker uses Awpy to turn a recording into player identities,
round boundaries, and death events. Deterministic analytics classify events
and select opening deaths. A typed coaching contract allows a model to
prioritize verified events. The backend renders the factual claim and the
review action from validated fields.

## What I verified

- An 84 MB Valve demo passed through upload, storage and event-based analytics.
  Awpy decoded Mirage, 13 rounds and 78 death events.
- The first-death rule uses round boundaries, then event tick and ordinal.
  A world death after the final recorded round explains one difference
  between Awpy's scoreboard and the review dashboard.
- The evidence evaluation suite checks 30 factual and adversarial cases.
  A model double verifies tool calling and typed output independently.
- The public sample loads a sanitized export of real match evidence on
  Vercel Hobby. It supports player selection, opening deaths and review notes.

## Limits and next validation

Match sources differ in coverage. Recorded interactions cannot establish
full attendance or explain why a player lost a fight. Model-backed production
quality and human usefulness need separate evaluation. The public sample
serves a replayable example, while the upload workflow runs in the local stack.

- [Interactive sample](https://cs2-ai-coach-demo.vercel.app)
- [Evaluation baseline](COACH-EVAL.md)
- [Run the full stack](OPERATIONS.md)

## Portfolio entry

**CS2 AI Coach** — Built a CS2 replay analysis application with a Next.js
interface, FastAPI, PostgreSQL, and an Awpy worker. Implemented verified
round metrics and evidence-validated coaching, and built a 30-case suite for
unsupported gameplay claims.
