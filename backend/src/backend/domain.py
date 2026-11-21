"""Validated contracts for match data extracted from CS2 recordings."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonnegativeInt = Annotated[int, Field(ge=0)]
SteamID = Annotated[str, StringConstraints(pattern=r"^[1-9][0-9]{0,19}$")]


class PlayerSummary(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    steamid: SteamID | None
    name: str | None
    kills: NonnegativeInt | None
    deaths: NonnegativeInt | None


class MatchSummary(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    filename: Annotated[str, StringConstraints(min_length=1)]
    size_bytes: NonnegativeInt
    map_name: str | None
    round_count: NonnegativeInt
    players: list[PlayerSummary]
