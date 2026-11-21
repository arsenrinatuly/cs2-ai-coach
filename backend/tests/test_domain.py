import pytest
from pydantic import ValidationError

from backend.domain import MatchSummary, PlayerSummary


@pytest.mark.parametrize("kills", [-1, "3", True])
def test_player_rejects_invalid_kill_counts(kills: object) -> None:
    with pytest.raises(ValidationError, match="kills"):
        PlayerSummary.model_validate(
            {"steamid": None, "name": None, "kills": kills, "deaths": None}
        )


def test_match_requires_round_count() -> None:
    with pytest.raises(ValidationError, match="round_count"):
        MatchSummary.model_validate(
            {
                "filename": "match.dem",
                "size_bytes": 100,
                "map_name": None,
                "players": [],
            }
        )
