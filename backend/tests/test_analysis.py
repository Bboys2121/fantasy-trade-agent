import json
from pathlib import Path

from app.analysis.roster_scoring import (
    RosterPlayer as P,
)
from app.analysis.roster_scoring import (
    best_lineup,
    lineup_points,
    needs,
    rate_team,
    replacement_levels,
    surpluses,
)
from app.analysis.trade_finder import find_trades

FIXTURE = Path(__file__).parent / "fixtures" / "league_snapshot.json"


def basic_roster(**overrides):
    """A legal roster; pass e.g. WR2=50 to change one player's points."""
    pts = {"QB": 300, "RB1": 200, "RB2": 190, "WR1": 200, "WR2": 190, "TE": 100}
    pts.update(overrides)
    return [P("qb", "QB", pts["QB"]), P("rb1", "RB", pts["RB1"]), P("rb2", "RB", pts["RB2"]),
            P("wr1", "WR", pts["WR1"]), P("wr2", "WR", pts["WR2"]), P("te", "TE", pts["TE"])]


# A is deep at RB and thin at WR; B is the reverse. A natural trade partner pair.
TEAM_A = basic_roster(WR1=100, WR2=90) + [P("a_rb3", "RB", 230), P("a_rb4", "RB", 220)]
TEAM_B = basic_roster(RB1=100, RB2=90) + [P("b_wr3", "WR", 180)]


def test_best_lineup_fills_flex_with_best_leftover():
    lineup = best_lineup(TEAM_A)
    assert len(lineup) == 7  # 1 QB + 2 RB + 2 WR + 1 TE + 1 FLEX
    assert "a_rb3" in {p.name for p in lineup}  # 230 RB beats every WR leftover


def test_out_player_scores_zero():
    healthy = basic_roster()
    hurt = [P("qb", "QB", 300, "OUT")] + healthy[1:]
    assert lineup_points(hurt) == lineup_points(healthy) - 300


# A weak third team so the league has a realistic replacement level at every position.
TEAM_C = [P("c_qb1", "QB", 200), P("c_qb2", "QB", 190), P("c_te1", "TE", 40), P("c_te2", "TE", 30)] + [
    P(f"c_{pos}{i}", pos, 60 - 10 * (i // 2)) for pos in ("RB", "WR") for i in range(4)]


def test_needs_and_surpluses():
    rosters = {"A": TEAM_A, "B": TEAM_B, "C": TEAM_C}
    ratings = rate_team(TEAM_A, replacement_levels(rosters))
    assert needs(ratings)[0] == "WR"          # A's weakest position
    assert "RB" in surpluses(ratings)         # A has an unused RB on the bench


def test_find_trades_both_sides_improve():
    trades = find_trades({"A": TEAM_A, "B": TEAM_B}, "A")
    assert trades
    for t in trades:
        assert t.my_gain >= 1 and t.their_gain >= 1
        assert t.my_team == "A" and t.their_team == "B"
    assert trades[0].give.position == "RB" and trades[0].get.position == "WR"
    scores = [t.score for t in trades]
    assert scores == sorted(scores, reverse=True)


def test_no_trade_between_identical_teams():
    assert find_trades({"A": basic_roster(), "B": basic_roster()}, "A") == []


def test_fixture_league_runs_end_to_end():
    snap = json.loads(FIXTURE.read_text())
    rosters = {t["name"]: [P(p["name"], p["position"], p["projected_points"], p["injury_status"])
                           for p in t["roster"]] for t in snap["teams"]}
    for t in find_trades(rosters, "Team 1"):
        assert t.score >= 1
