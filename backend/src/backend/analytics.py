"""Compute review metrics from stored rounds and recorded death events."""

from bisect import bisect_right

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.storage import DeathEvent, Match, Participant, Round


class EventReference(BaseModel):
    round_number: int
    event_ordinal: int
    tick: int


class PlayerMetrics(BaseModel):
    steamid: str
    name: str | None
    kills: int
    deaths: int
    assists: int
    rounds_with_death_event_participation: list[int]
    opening_deaths: list[EventReference]


class MatchAnalytics(BaseModel):
    match_id: str
    map_name: str | None
    round_count: int
    players: list[PlayerMetrics]


def compute_analytics(
    match: Match,
    participants: list[Participant],
    rounds: list[Round],
    events: list[DeathEvent],
) -> MatchAnalytics:
    players = {
        row.steamid: PlayerMetrics(
            steamid=row.steamid,
            name=row.name,
            kills=0,
            deaths=0,
            assists=0,
            rounds_with_death_event_participation=[],
            opening_deaths=[],
        )
        for row in sorted(participants, key=lambda row: row.steamid)
    }
    participation: dict[str, set[int]] = {identity: set() for identity in players}
    ordered_rounds = sorted(rounds, key=lambda row: (row.start_tick, row.number))
    starts = [row.start_tick for row in ordered_rounds]
    seen_rounds: set[int] = set()

    for event in sorted(events, key=lambda row: (row.tick, row.ordinal)):
        position = bisect_right(starts, event.tick) - 1
        if position < 0:
            continue
        round_ = ordered_rounds[position]
        boundary = round_.official_end_tick
        if boundary is None:
            boundary = round_.end_tick
        if boundary is None or event.tick > boundary or round_.is_knife_round:
            continue

        attacker = players.get(event.attacker_id)
        victim = players.get(event.victim_id)
        assister = players.get(event.assister_id)
        for player in (attacker, victim, assister):
            if player is not None:
                participation[player.steamid].add(round_.number)
        if attacker is not None and is_enemy_kill(event):
            attacker.kills += 1
        if victim is not None:
            victim.deaths += 1
        if assister is not None and event.assister_id not in (
            event.attacker_id,
            event.victim_id,
        ):
            assister.assists += 1

        if round_.number not in seen_rounds:
            seen_rounds.add(round_.number)
            if victim is not None:
                victim.opening_deaths.append(
                    EventReference(
                        round_number=round_.number,
                        event_ordinal=event.ordinal,
                        tick=event.tick,
                    )
                )

    for identity, player in players.items():
        player.rounds_with_death_event_participation = sorted(participation[identity])

    return MatchAnalytics(
        match_id=match.id,
        map_name=match.map_name,
        round_count=len(rounds),
        players=list(players.values()),
    )


def is_enemy_kill(event: DeathEvent) -> bool:
    return (
        event.attacker_id != event.victim_id
        and event.attacker_side in ("terrorist", "counter-terrorist")
        and event.victim_side in ("terrorist", "counter-terrorist")
        and event.attacker_side != event.victim_side
    )


def load_analytics(session: Session, match: Match) -> MatchAnalytics:
    return compute_analytics(
        match,
        list(
            session.scalars(select(Participant).where(Participant.match_id == match.id))
        ),
        list(session.scalars(select(Round).where(Round.match_id == match.id))),
        list(
            session.scalars(select(DeathEvent).where(DeathEvent.match_id == match.id))
        ),
    )
