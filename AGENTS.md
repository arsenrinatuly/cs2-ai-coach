# CS2 AI Coach — Codex Working Agreement

## Mission
Build an evidence-grounded Counter-Strike 2 demo-analysis application. Parse real `.dem` files, calculate verifiable match statistics, and later generate evidence-grounded coaching reports. Avoid hallucinated gameplay facts.

## Developer and environment
- The human developer owns product decisions, reviews the architecture and implementation, and accepts completed work.
- Development machine: **macOS**, typically using **zsh** and Terminal.
- Preferred backend: Python 3.12, `uv`, FastAPI, Awpy, pytest, Ruff.
- Planned later: PostgreSQL, SQLAlchemy/Alembic, Next.js/TypeScript, Pydantic AI, Docker, CI.
- Existing GitHub repository: `https://github.com/arsenrinatuly/cs2-ai-coach`.
- Linear team: `ARS`; include issue IDs (e.g. `ARS-5`) in branch/PR names when possible.

## Codex-first development
1. Identify the active issue in Linear and inspect the repository before making changes.
2. Codex is the primary implementation agent and can write code, tests, documentation, and focused refactors within the agreed scope.
3. Share a short implementation plan, then carry it through testing and self-review. Explain significant decisions, trade-offs, and how to verify the result on macOS.
4. Work on feature branches and reference the issue ID in branch names and commits. Keep changes small and reviewable.
5. Preserve existing work and shared history. Do not force-push or merge to main without the developer's approval.

## Engineering rules
- Modular monolith. Separate parser adapter, domain models, analytics, HTTP handlers and LLM integration.
- Match statistics must come from parsed game events, never inferred by an LLM.
- Every factual coaching observation must reference supporting match evidence; label advice or uncertainty clearly.
- Use descriptive Python names and type hints. Keep modules and functions focused.
- Add tests for behavior and edge cases. Run `uv run pytest` and `uv run ruff check .` when configured; report what actually ran.
- Avoid new dependencies without explaining their purpose and getting approval.
- Do not mark issues as Done until acceptance criteria are verified.

## macOS and safety
- Give macOS-compatible commands; do not use `apt` or Linux-only paths.
- Before setup, verify `pwd`, `git status`, existing files, and installed tools. Never run `git init` in an already-cloned repository just because a checklist mentions initialization.
- Ask before destructive commands, force pushes, deleting files, migrations that discard data, or creating cloud resources.
- Never commit `.env`, credentials, private `.dem` files, `.venv/`, generated datasets, or unnecessary personal information.
- Do not claim tests pass, files exist, or a GitHub PR was created unless verified.

## Response style
- Explanations and feedback: **Russian**.
- Code, variable names, issues, README and developer documentation: **English**.
- Be concise and technically precise. End learning responses with one concrete next action.
