import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.storage import DeathEvent, Match, Participant, Player, Round


def test_round_trip_match_evidence() -> None:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated PostgreSQL test database.")
    engine = create_engine(url)
    match_id = "a" * 64
    with engine.begin() as connection:
        with Session(bind=connection) as session:
            session.add(
                Match(id=match_id, filename="sample.dem", size_bytes=10, status="ready")
            )
            session.add(Player(steamid="123"))
            session.flush()
            session.add(Participant(match_id=match_id, steamid="123", name="Player"))
            session.add(
                Round(match_id=match_id, number=1, start_tick=5, is_knife_round=False)
            )
            session.flush()
            session.add(
                DeathEvent(match_id=match_id, ordinal=1, tick=10, victim_id="123")
            )
            session.flush()
            session.expunge_all()

            assert session.get(Match, match_id).status == "ready"
            assert session.get(Participant, (match_id, "123")).name == "Player"
            assert session.get(Round, (match_id, 1)).start_tick == 5
            assert session.get(DeathEvent, (match_id, 1)).victim_id == "123"
            session.rollback()
    engine.dispose()
