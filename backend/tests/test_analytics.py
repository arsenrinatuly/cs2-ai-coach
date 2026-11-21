from backend.analytics import compute_analytics
from backend.storage import DeathEvent, Match, Participant, Round


def test_opening_death_order_uses_event_ordinal_to_break_tick_ties() -> None:
    players = [
        Participant(steamid="2", name="Same"),
        Participant(steamid="1", name="Same"),
    ]
    rounds = [
        Round(number=1, start_tick=5, end_tick=20, is_knife_round=False),
        Round(number=2, start_tick=21, end_tick=30, is_knife_round=False),
    ]
    events = [
        DeathEvent(ordinal=2, tick=10, victim_id="2"),
        DeathEvent(
            ordinal=1,
            tick=10,
            attacker_id="2",
            victim_id="1",
            attacker_side="terrorist",
            victim_side="counter-terrorist",
        ),
        DeathEvent(ordinal=3, tick=40, victim_id="1"),
    ]
    result = compute_analytics(Match(id="sample"), players, rounds, events)

    first, second = result.players
    assert first.steamid == "1"
    assert first.opening_deaths[0].event_ordinal == 1
    assert first.deaths == 1
    assert first.rounds_with_death_event_participation == [1]
    assert second.kills == 1
    assert second.deaths == 1
    assert second.opening_deaths == []
    assert result.round_count == 2


def test_unknown_first_victim_is_not_replaced_with_the_next_death() -> None:
    result = compute_analytics(
        Match(id="sample"),
        [Participant(steamid="1")],
        [Round(number=1, start_tick=5, end_tick=20, is_knife_round=False)],
        [
            DeathEvent(ordinal=1, tick=10),
            DeathEvent(ordinal=2, tick=11, victim_id="1"),
        ],
    )
    assert result.players[0].deaths == 1
    assert result.players[0].opening_deaths == []
