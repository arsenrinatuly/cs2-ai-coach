"""SQLAlchemy schema for recorded matches and their source evidence."""

from sqlalchemy import BigInteger, ForeignKey, ForeignKeyConstraint, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(16))
    map_name: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)


class Player(Base):
    __tablename__ = "players"

    steamid: Mapped[str] = mapped_column(String(20), primary_key=True)


class Participant(Base):
    __tablename__ = "participants"

    match_id: Mapped[str] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), primary_key=True
    )
    steamid: Mapped[str] = mapped_column(
        ForeignKey("players.steamid"), primary_key=True
    )
    name: Mapped[str | None] = mapped_column(Text)


class Round(Base):
    __tablename__ = "rounds"

    match_id: Mapped[str] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), primary_key=True
    )
    number: Mapped[int] = mapped_column(primary_key=True)
    start_tick: Mapped[int]
    end_tick: Mapped[int | None]
    official_end_tick: Mapped[int | None]
    winner_side: Mapped[str | None] = mapped_column(Text)
    is_knife_round: Mapped[bool]


class DeathEvent(Base):
    __tablename__ = "death_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ("match_id", "attacker_id"),
            ("participants.match_id", "participants.steamid"),
        ),
        ForeignKeyConstraint(
            ("match_id", "victim_id"), ("participants.match_id", "participants.steamid")
        ),
        ForeignKeyConstraint(
            ("match_id", "assister_id"),
            ("participants.match_id", "participants.steamid"),
        ),
    )

    match_id: Mapped[str] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(primary_key=True)
    tick: Mapped[int]
    attacker_id: Mapped[str | None] = mapped_column(String(20))
    victim_id: Mapped[str | None] = mapped_column(String(20))
    assister_id: Mapped[str | None] = mapped_column(String(20))
    attacker_side: Mapped[str | None] = mapped_column(Text)
    victim_side: Mapped[str | None] = mapped_column(Text)
    weapon: Mapped[str | None] = mapped_column(Text)
