"""Rate each team's roster by position.

Everything here works on plain RosterPlayer objects (no database), so it is easy to test.
Team strength = projected points of the best legal starting lineup.
"""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Team

# League lineup rules. Change these to match your league's settings.
STARTER_SLOTS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1}
FLEX_SLOTS = 1
FLEX_POSITIONS = ("RB", "WR", "TE")
# Players who can't play count as zero points.
OUT_STATUSES = {"OUT", "INJURY_RESERVE"}


@dataclass(frozen=True)
class RosterPlayer:
    name: str
    position: str
    projected_points: float
    injury_status: str = "ACTIVE"

    @property
    def points(self) -> float:
        return 0.0 if self.injury_status in OUT_STATUSES else self.projected_points


@dataclass(frozen=True)
class PositionRating:
    position: str
    starter_vor: float  # total value over replacement of players starting at this position
    n_starters: int     # how many of them start (incl. FLEX)
    bench_vor: float    # total positive VOR sitting on the bench (tradeable surplus)


def load_rosters(session: Session) -> dict[str, list[RosterPlayer]]:
    """Read the DB into {team name: [RosterPlayer]}."""
    rosters = {}
    for team in session.scalars(select(Team).order_by(Team.espn_team_id)):
        rosters[team.name] = [
            RosterPlayer(s.player.name, s.player.position, s.player.projected_points,
                         s.player.injury_status)
            for s in team.roster
        ]
    return rosters


def best_lineup(players: list[RosterPlayer]) -> list[RosterPlayer]:
    """Pick the highest-scoring legal lineup: fixed slots first, then the best FLEX."""
    by_pos: dict[str, list[RosterPlayer]] = {}
    for p in sorted(players, key=lambda p: p.points, reverse=True):
        by_pos.setdefault(p.position, []).append(p)

    lineup, leftovers = [], []
    for pos, players_at_pos in by_pos.items():
        n = STARTER_SLOTS.get(pos, 0)
        lineup += players_at_pos[:n]
        if pos in FLEX_POSITIONS:
            leftovers += players_at_pos[n:]
    leftovers.sort(key=lambda p: p.points, reverse=True)
    return lineup + leftovers[:FLEX_SLOTS]


def lineup_points(players: list[RosterPlayer]) -> float:
    return sum(p.points for p in best_lineup(players))


def replacement_levels(rosters: dict[str, list[RosterPlayer]]) -> dict[str, float]:
    """Replacement level per position = the best player who would NOT start league-wide.

    Example: 10 teams x 2 RB slots = 20 starting RBs, so replacement is the 21st best RB.
    """
    n_teams = len(rosters)
    levels = {}
    for pos, slots in STARTER_SLOTS.items():
        pts = sorted((p.points for r in rosters.values() for p in r if p.position == pos),
                     reverse=True)
        idx = n_teams * slots  # first non-starter
        levels[pos] = pts[idx] if idx < len(pts) else (pts[-1] if pts else 0.0)
    return levels


def rate_team(players: list[RosterPlayer], replacement: dict[str, float]) -> dict[str, PositionRating]:
    """Per-position strength: value over replacement for starters vs. bench."""
    starters = set(best_lineup(players))
    ratings = {}
    for pos in STARTER_SLOTS:
        at_pos = [p for p in players if p.position == pos]
        base = replacement.get(pos, 0.0)
        ratings[pos] = PositionRating(
            position=pos,
            starter_vor=sum(p.points - base for p in at_pos if p in starters),
            n_starters=sum(1 for p in at_pos if p in starters),
            bench_vor=sum(max(p.points - base, 0.0) for p in at_pos if p not in starters),
        )
    return ratings


def needs(ratings: dict[str, PositionRating]) -> list[str]:
    """Positions ordered weakest first (lowest average VOR per starter, so a position
    with two starting slots isn't judged against one with a single slot)."""
    return sorted(ratings, key=lambda pos: ratings[pos].starter_vor / max(ratings[pos].n_starters, 1))


def surpluses(ratings: dict[str, PositionRating]) -> list[str]:
    """Positions with tradeable bench value, biggest first."""
    return [pos for pos in sorted(ratings, key=lambda p: ratings[p].bench_vor, reverse=True)
            if ratings[pos].bench_vor > 0]
