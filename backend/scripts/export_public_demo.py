"""Export a de-identified review of an approved public CS2 recording."""

import argparse
import json
from pathlib import Path

from awpy import Demo

from backend.analytics import compute_analytics
from backend.coach import CoachSelection, ReviewChoice, ReviewContext, render_report
from backend.ingestion import extract_evidence
from backend.storage import Match, Participant


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("demo", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    demo = Demo(args.demo)
    identities, rounds, deaths = extract_evidence(demo, "public-mirage")
    analytics = compute_analytics(
        Match(id="public-mirage", map_name=demo.header.get("map_name")),
        [
            Participant(steamid=identity, name=name)
            for identity, name in identities.items()
        ],
        rounds,
        deaths,
    )
    reports = {}
    for index, player in enumerate(analytics.players, start=1):
        player.steamid = str(index)
        player.name = f"Player {index}"
        choices = [
            ReviewChoice(event_ordinal=event.event_ordinal, focus="timing")
            for event in player.opening_deaths[:3]
        ]
        reports[player.steamid] = render_report(
            ReviewContext(analytics.match_id, player),
            CoachSelection(choices=choices) if choices else None,
            "deterministic",
        ).model_dump()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"analytics": analytics.model_dump(), "reports": reports}) + "\n"
    )


if __name__ == "__main__":
    main()
