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
