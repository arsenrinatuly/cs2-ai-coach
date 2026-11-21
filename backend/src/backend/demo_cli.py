"""Print a JSON summary of one CS2 recording."""

import argparse
import json
from pathlib import Path

from backend.demo_inspection import DemoInspectionError, inspect_demo
from backend.domain import MatchSummary, PlayerSummary


def player_sort_key(player: PlayerSummary) -> tuple[str, str, int, int]:
    kills = player.kills
    deaths = player.deaths
    return (
        player.steamid or "",
        player.name or "",
        kills if kills is not None else -1,
        deaths if deaths is not None else -1,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("demo", type=Path, help="Path to an extracted CS2 .dem file")
    args = parser.parse_args(argv)
    try:
        inspection = inspect_demo(args.demo)
    except DemoInspectionError as error:
        parser.exit(1, f"{parser.prog}: {error}\n")

    summary = MatchSummary.model_validate(inspection)
    summary.players.sort(key=player_sort_key)
    print(json.dumps(summary.model_dump(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
