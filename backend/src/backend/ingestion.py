"""Stage recordings and persist their evidence in a separate worker process."""

import argparse
import logging
import os
import time
from functools import lru_cache
from pathlib import Path

from awpy import Demo, InvalidDemoError
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.storage import DeathEvent, Match, Participant, Player, Round

logger = logging.getLogger(__name__)


@lru_cache
def engine() -> Engine:
    return create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)


def spool_dir() -> Path:
    directory = Path(os.environ.get("DEMO_SPOOL_DIR", ".demo-spool"))
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    return directory


def enqueue(match_id: str, filename: str, size: int, temporary: Path) -> None:
    with Session(engine()) as session, session.begin():
        statement = (
            insert(Match)
            .values(id=match_id, filename=filename, size_bytes=size, status="queued")
            .on_conflict_do_nothing(index_elements=[Match.id])
            .returning(Match.id)
        )
        if session.scalar(statement) is not None:
            temporary.replace(spool_dir() / f"{match_id}.dem")


def steam_id(value: int | None) -> str | None:
    return str(value) if value else None


def extract_evidence(
    demo: Demo, match_id: str
) -> tuple[dict[str, str | None], list[Round], list[DeathEvent]]:
    participants = {}
    for row in demo.players.iter_rows(named=True):
        identity = steam_id(row["steamid"])
        if identity is not None:
            participants.setdefault(identity, row["name"])

    rounds = [
        Round(
            match_id=match_id,
            number=row["round_num"],
            start_tick=row["start_tick"],
            end_tick=row["end_tick"],
            official_end_tick=row["official_end_tick"],
            winner_side=row["winner_side"],
            is_knife_round=row["is_knife_round"],
        )
        for row in demo.rounds.iter_rows(named=True)
    ]

    deaths = []
    for ordinal, row in enumerate(demo.kills.iter_rows(named=True), start=1):
        identities = {}
        for role in ("attacker", "victim", "assister"):
            identity = steam_id(row[f"{role}_steamid"])
            identities[f"{role}_id"] = identity
            if identity is not None:
                participants.setdefault(identity, row[f"{role}_name"])
        deaths.append(
            DeathEvent(
                match_id=match_id,
                ordinal=ordinal,
                tick=row["tick"],
                attacker_side=row["attacker_side"],
                victim_side=row["victim_side"],
                weapon=row["weapon"],
                **identities,
            )
        )
    return participants, rounds, deaths


def process_next() -> bool:
    with Session(engine()) as session, session.begin():
        match = session.scalar(
            select(Match)
            .where(Match.status == "queued", Match.next_attempt_at <= int(time.time()))
            .order_by(Match.next_attempt_at, Match.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if match is None:
            return False

        match.attempts += 1
        path = spool_dir() / f"{match.id}.dem"
        try:
            demo = Demo(path)
            participants, rounds, deaths = extract_evidence(demo, match.id)
            map_name = demo.header.get("map_name") or None
        except InvalidDemoError:
            match.status = "failed"
            match.error = "The demo is corrupt or uses an unsupported recording format."
        except OSError:
            if match.attempts < 3:
                match.next_attempt_at = int(time.time()) + 2**match.attempts
                logger.warning("Retry scheduled for match %s", match.id)
                return True
            match.status = "failed"
            match.error = "The worker could not read the staged recording."
        else:
            if participants:
                session.execute(
                    insert(Player)
                    .values(
                        [{"steamid": identity} for identity in sorted(participants)]
                    )
                    .on_conflict_do_nothing(index_elements=[Player.steamid])
                )
            session.add_all(
                Participant(match_id=match.id, steamid=identity, name=name)
                for identity, name in participants.items()
            )
            session.add_all(rounds)
            session.flush()
            session.add_all(deaths)
            match.map_name = map_name
            match.status = "ready"

    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not clean up recording for match %s", path.stem)
    return True


def clean_terminal_uploads() -> None:
    with Session(engine()) as session:
        for path in spool_dir().glob("*.dem"):
            if len(path.stem) != 64:
                continue
            match = session.get(Match, path.stem)
            if match is not None and match.status in {"ready", "failed"}:
                path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Process at most one job")
    args = parser.parse_args()
    if args.once:
        process_next()
        return
    logging.basicConfig(level=logging.INFO)
    cleanup_at = 0.0
    while True:
        try:
            if time.monotonic() >= cleanup_at:
                clean_terminal_uploads()
                cleanup_at = time.monotonic() + 300
            if not process_next():
                time.sleep(1)
        except (OperationalError, OSError) as error:
            logger.warning("Worker will reconnect after %s", type(error).__name__)
            time.sleep(2)


if __name__ == "__main__":
    main()
