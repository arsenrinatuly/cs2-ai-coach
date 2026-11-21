"""Inspect one CS2 recording through Awpy."""

import argparse
import json
import stat
from pathlib import Path
from typing import TypedDict

from awpy import Demo, InvalidDemoError


class PlayerStats(TypedDict):
    steamid: str | None
    name: str | None
    kills: int | None
    deaths: int | None


class DemoInspection(TypedDict):
    filename: str
    size_bytes: int
    map_name: str | None
    round_count: int
    players: list[PlayerStats]


class DemoInspectionError(ValueError):
    """The input could not be inspected as a CS2 demo."""


def inspect_demo(path: Path) -> DemoInspection:
    """Return Awpy's recorded rounds and event-derived scoreboard."""
    if path.suffix.lower() != ".dem":
        raise DemoInspectionError("Expected an extracted .dem file.")

    try:
        file_info = path.stat()
        if not stat.S_ISREG(file_info.st_mode):
            raise DemoInspectionError("Expected a regular .dem file.")

        demo = Demo(path)
        map_name = demo.header.get("map_name") or None
        round_count = demo.rounds.height
        scoreboard = demo.player_stats(include_knife_rounds=True)
    except (OSError, InvalidDemoError) as error:
        raise DemoInspectionError(f"Cannot read {path.name}: {error}") from error

    players: list[PlayerStats] = []
    for row in scoreboard.iter_rows(named=True):
        steamid = row.get("steamid")
        players.append(
            PlayerStats(
                steamid=str(steamid) if steamid else None,
                name=row.get("name") or None,
                kills=row.get("kills"),
                deaths=row.get("deaths"),
            )
        )

    return DemoInspection(
        filename=path.name,
        size_bytes=file_info.st_size,
        map_name=map_name,
        round_count=round_count,
        players=players,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("demo", type=Path, help="Path to an extracted CS2 .dem file")
    args = parser.parse_args()
    try:
        inspection = inspect_demo(args.demo)
    except DemoInspectionError as error:
        parser.exit(1, f"{parser.prog}: {error}\n")
    print(json.dumps(inspection, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
