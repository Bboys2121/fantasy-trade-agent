from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    espn_team_id: Mapped[int] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(100))
    owner: Mapped[str] = mapped_column(String(100), default="")
    wins: Mapped[int] = mapped_column(default=0)
    losses: Mapped[int] = mapped_column(default=0)
    roster: Mapped[list["RosterSlot"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )


class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(primary_key=True)
    espn_player_id: Mapped[int] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(100))
    position: Mapped[str] = mapped_column(String(10))
    pro_team: Mapped[str] = mapped_column(String(10), default="")
    injury_status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    total_points: Mapped[float] = mapped_column(default=0.0)
    projected_points: Mapped[float] = mapped_column(default=0.0)


class RosterSlot(Base):
    """Which player sits on which team, and in which lineup slot (QB, RB, BE, IR...)."""
    __tablename__ = "roster_slots"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    lineup_slot: Mapped[str] = mapped_column(String(10))
    team: Mapped[Team] = relationship(back_populates="roster")
    player: Mapped[Player] = relationship()
