"""Find 1-for-1 trades where BOTH teams improve their best lineup.

Usage (from backend/):  python -m app.analysis.trade_finder --team "Team 1"
"""
import argparse
from dataclasses import dataclass

from app.analysis.roster_scoring import RosterPlayer, lineup_points, load_rosters


@dataclass(frozen=True)
class TradeCandidate:
    my_team: str
    their_team: str
    give: RosterPlayer  # player I send
    get: RosterPlayer   # player I receive
    my_gain: float      # change in my lineup points
    their_gain: float   # change in their lineup points

    @property
    def score(self) -> float:
        # Ranking by the smaller gain favors deals the other manager would actually accept,
        # instead of lopsided ones that look great for me only.
        return min(self.my_gain, self.their_gain)


def _swap(roster: list[RosterPlayer], out: RosterPlayer, incoming: RosterPlayer) -> list[RosterPlayer]:
    return [incoming if p is out else p for p in roster]


def find_trades(rosters: dict[str, list[RosterPlayer]], my_team: str,
                min_gain: float = 1.0, limit: int = 10) -> list[TradeCandidate]:
    """Try every 1-for-1 swap with every other team; keep those where both gain >= min_gain."""
    mine = rosters[my_team]
    my_base = lineup_points(mine)
    found = []
    for their_team, theirs in rosters.items():
        if their_team == my_team:
            continue
        their_base = lineup_points(theirs)
        for give in mine:
            for get in theirs:
                my_gain = lineup_points(_swap(mine, give, get)) - my_base
                their_gain = lineup_points(_swap(theirs, get, give)) - their_base
                if my_gain >= min_gain and their_gain >= min_gain:
                    found.append(TradeCandidate(my_team, their_team, give, get, my_gain, their_gain))
    found.sort(key=lambda t: t.score, reverse=True)
    return found[:limit]


def main() -> None:
    from app.db.session import get_session, make_engine

    parser = argparse.ArgumentParser()
    parser.add_argument("--team", required=True, help="your team name")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    with get_session(make_engine()) as session:
        rosters = load_rosters(session)
    if args.team not in rosters:
        raise SystemExit(f"Unknown team. Choose from: {', '.join(rosters)}")

    trades = find_trades(rosters, args.team, limit=args.limit)
    if not trades:
        print("No trades found where both teams improve.")
    for t in trades:
        print(f"With {t.their_team}: give {t.give.name} ({t.give.position}, {t.give.points:.0f}) "
              f"for {t.get.name} ({t.get.position}, {t.get.points:.0f})  "
              f"-> you +{t.my_gain:.1f}, them +{t.their_gain:.1f}")


if __name__ == "__main__":
    main()
